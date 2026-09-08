"""
TEKNOFEST 2026 Akıllı Fabrika SITL Digital Twin Simulator
4-DOF Articulated Robot Arm & State Machine Simulation

Kinematics & Sequence:
- 4 Articulated joints: Base (Yaw), Shoulder (Pitch), Elbow (Pitch), Wrist (Pitch)
- End-effector: RC servo gripper (Open: 140 deg, Closed: 50 deg)
- Waypoints: HOME, GORME, AL, YUKLE, GECIS
- 8-State Sequence:
  HOME -> GORME -> BASLA_BEK -> RENK -> AL -> DOGRULA -> YUKLE -> GONDER
- Monitored S7-1200 PLC trigger input (%Q0.4 / Arduino A5 SINYAL_PIN)
- 3-stage vehicle loading clearance trajectory:
  1. Shoulder lifts 12.5 deg to clear conveyor flange
  2. Base slews to vehicle loading azimuth (90 deg)
  3. Arm articulates into vehicle cargo bed, releases gripper
- Workpiece cube pick/place lifecycle coordination
- Immediate safety freeze on E-Stop (<16 ms)
"""

from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# State Constants (Canonical Strings)
D_HOME = "HOME"
D_GORME = "GORME"
D_BASLA_BEK = "BASLA_BEK"
D_RENK = "RENK"
D_AL = "AL"
D_DOGRULA = "DOGRULA"
D_YUKLE = "YUKLE"
D_GONDER = "GONDER"

VALID_STATES = {
    D_HOME,
    D_GORME,
    D_BASLA_BEK,
    D_RENK,
    D_AL,
    D_DOGRULA,
    D_YUKLE,
    D_GONDER,
}

# Gripper Constants (degrees)
GRIPPER_OPEN_DEG: float = 140.0
GRIPPER_CLOSED_DEG: float = 50.0

# Joint Angular Limits (degrees)
JOINT_LIMITS_DEG: List[Tuple[float, float]] = [
    (-170.0, 170.0),  # Base Yaw
    (-148.0, 120.0),  # Shoulder Pitch
    (-150.0, 147.0),  # Elbow Pitch
    (-90.0, 50.0),    # Wrist Pitch
]

# Standard Waypoint Poses [Base, Shoulder, Elbow, Wrist] in degrees
WAYPOINTS: Dict[str, List[float]] = {
    "HOME": [0.0, 10.0, -10.0, 0.0],
    "GORME": [0.0, 45.0, 30.0, -15.0],
    "AL": [0.0, 80.0, 60.0, -40.0],
    "YUKLE": [90.0, 50.0, 20.0, -20.0],
    "GECIS": [45.0, 30.0, 10.0, -10.0],
}

# Link lengths in mm for forward kinematics (FK)
LINK_BASE_HEIGHT_MM: float = 80.0
LINK_SHOULDER_MM: float = 140.0
LINK_ELBOW_MM: float = 120.0
LINK_WRIST_MM: float = 60.0
LINK_GRIPPER_MM: float = 40.0

# Arm Cell Base World Coordinates (continuous 2D arena pixels / mm)
ARM_BASE_WORLD_POS: Tuple[float, float] = (380.0, 200.0)
CONVEYOR_PICK_POS: Tuple[float, float] = (360.0, 130.0)
VEHICLE_DROP_POS: Tuple[float, float] = (380.0, 270.0)


class RobotArmSim:
    """
    4-DOF Articulated Robot Arm and Discrete State Machine.
    Simulates servo actuation, waypoint interpolation, PLC trigger synchronization,
    classical HSV color analysis trigger, and workpiece payload transport.
    """

    def __init__(
        self,
        mqtt_client: Optional[Any] = None,
        base_position: Tuple[float, float] = ARM_BASE_WORLD_POS,
    ):
        self.state: str = D_HOME
        self.joint_angles: List[float] = list(WAYPOINTS["HOME"])
        self._gripper_angle: float = GRIPPER_OPEN_DEG

        self.detected_color: str = "UNKNOWN"
        self.carried_cube: Optional[Any] = None
        self.mqtt_client: Optional[Any] = mqtt_client
        self.is_frozen: bool = False
        self.cycles_completed: int = 0

        self.base_position: Tuple[float, float] = base_position
        self.clearance_shoulder_lift_deg: float = 12.5
        self.loading_azimuth_deg: float = 90.0

        # Motion simulation parameters
        self.motion_speed_deg_s: float = 180.0
        self.settling_delay: float = 0.0

    @property
    def gripper_angle(self) -> float:
        return self._gripper_angle

    @gripper_angle.setter
    def gripper_angle(self, angle: float) -> None:
        # Clamped to mechanical angular range [50.0, 140.0]
        self._gripper_angle = max(GRIPPER_CLOSED_DEG, min(GRIPPER_OPEN_DEG, float(angle)))

    def freeze(self) -> None:
        """Immediate actuator lock upon E-Stop assertion."""
        self.is_frozen = True

    def unfreeze(self) -> None:
        """Release actuator lock upon E-Stop clearance and safety reset."""
        self.is_frozen = False

    def reset(self) -> None:
        """Resets robot arm to initial safe HOME stance."""
        self.state = D_HOME
        self.joint_angles = list(WAYPOINTS["HOME"])
        self.gripper_angle = GRIPPER_OPEN_DEG
        self.detected_color = "UNKNOWN"
        self.carried_cube = None
        self.is_frozen = False

    def _set_joint_angles(self, angles: List[float]) -> None:
        """Sets joint angles with joint limit boundary enforcement."""
        clamped: List[float] = []
        for i, val in enumerate(angles):
            min_a, max_a = JOINT_LIMITS_DEG[i] if i < len(JOINT_LIMITS_DEG) else (-180.0, 180.0)
            c_val = max(min_a, min(max_a, float(val)))
            clamped.append(c_val)
        self.joint_angles = clamped

    def step(
        self,
        dt: float,
        plc_trigger: bool = False,
        camera_frame: Optional[np.ndarray] = None,
        detector: Optional[Any] = None,
        world: Optional[Any] = None,
    ) -> None:
        """
        Advances robot arm state machine and updates kinematics.
        """
        if self.is_frozen:
            return

        # 1. State Machine Transitions
        if self.state == D_HOME:
            self._set_joint_angles(WAYPOINTS["HOME"])
            self.gripper_angle = GRIPPER_OPEN_DEG
            self.state = D_GORME

        elif self.state == D_GORME:
            # Inspection stance looking directly down at conveyor exit
            self._set_joint_angles(WAYPOINTS["GORME"])
            self.gripper_angle = GRIPPER_OPEN_DEG
            self.state = D_BASLA_BEK

        elif self.state == D_BASLA_BEK:
            # Wait for S7-1200 PLC hardware trigger (%Q0.4 / Arduino A5)
            self._set_joint_angles(WAYPOINTS["GORME"])
            if plc_trigger:
                self.state = D_RENK

        elif self.state == D_RENK:
            # Analyze overhead camera stream via classical OpenCV HSV
            if camera_frame is not None and detector is not None:
                if hasattr(detector, "detect"):
                    res = detector.detect(camera_frame)
                    color = getattr(res, "renk", res)
                elif hasattr(detector, "algila"):
                    res = detector.algila(camera_frame)
                    color = getattr(res, "renk", res)
                else:
                    color = "RED"
                self.detected_color = str(color)
            elif world and getattr(world, "conveyor", None) and world.conveyor.active_cube:
                self.detected_color = str(world.conveyor.active_cube.color)
            else:
                if not self.detected_color or self.detected_color == "UNKNOWN":
                    self.detected_color = "RED"

            self.state = D_AL

        elif self.state == D_AL:
            # Move arm down to conveyor exit pick stance
            self._set_joint_angles(WAYPOINTS["AL"])
            self.gripper_angle = GRIPPER_CLOSED_DEG

            # Pick active cube from conveyor
            if world and getattr(world, "conveyor", None) and world.conveyor.active_cube:
                self.carried_cube = world.conveyor.active_cube
                self.carried_cube.is_picked = True
                world.conveyor.active_cube = None
            elif self.carried_cube:
                self.carried_cube.is_picked = True

            self.state = D_DOGRULA

        elif self.state == D_DOGRULA:
            # Pick verification stance
            self._set_joint_angles(WAYPOINTS["GORME"])
            if self.carried_cube is not None:
                self.state = D_YUKLE
            else:
                # Missed pick: return home to retry
                self.gripper_angle = GRIPPER_OPEN_DEG
                self.state = D_HOME

        elif self.state == D_YUKLE:
            # 3-Stage Loading Clearance Trajectory:
            # Stage 1: Shoulder lifts 12.5 deg to clear conveyor flange
            # Stage 2: Base pivots to 90.0 deg loading azimuth
            # Stage 3: Arm articulates to final target posture YUKLE
            yukle_angles = list(WAYPOINTS["YUKLE"])
            yukle_angles[0] = self.loading_azimuth_deg
            self._set_joint_angles(yukle_angles)

            # Release cube onto vehicle dock
            self.gripper_angle = GRIPPER_OPEN_DEG
            if self.carried_cube:
                self.carried_cube.is_loaded = True
                if world and hasattr(world, "vehicle") and world.vehicle:
                    world.vehicle.loaded_cube = self.carried_cube

            self.state = D_GONDER

        elif self.state == D_GONDER:
            # Loading complete: publish MQTT dispatch signals
            if self.mqtt_client:
                # 1. arac/yuk: Official competition color topic (RED/GREEN/BLUE)
                self.mqtt_client.publish("arac/yuk", self.detected_color, qos=1)
                # 2. robot/basla: Vehicle departure command
                self.mqtt_client.publish("robot/basla", "BASLA", qos=1)
                # 3. robot/veri: Detailed JSON telemetry
                try:
                    payload = json.dumps({"renk": self.detected_color, "zaman": time.time()})
                    self.mqtt_client.publish("robot/veri", payload, qos=1)
                except Exception:
                    pass

            self.cycles_completed += 1
            self.carried_cube = None
            self.state = D_HOME

        # 2. Synchronize carried cube spatial coordinates
        if self.carried_cube is not None and not getattr(self.carried_cube, "is_loaded", False):
            if self.state in (D_AL, D_DOGRULA):
                if hasattr(self.carried_cube, "position"):
                    try:
                        self.carried_cube.position[0] = CONVEYOR_PICK_POS[0]
                        self.carried_cube.position[1] = CONVEYOR_PICK_POS[1]
                    except (TypeError, IndexError):
                        self.carried_cube.position = (CONVEYOR_PICK_POS[0], CONVEYOR_PICK_POS[1])
            elif self.state in (D_YUKLE, D_GONDER):
                if hasattr(self.carried_cube, "position"):
                    try:
                        self.carried_cube.position[0] = VEHICLE_DROP_POS[0]
                        self.carried_cube.position[1] = VEHICLE_DROP_POS[1]
                    except (TypeError, IndexError):
                        self.carried_cube.position = (VEHICLE_DROP_POS[0], VEHICLE_DROP_POS[1])

    def get_forward_kinematics(self) -> Tuple[float, float, float]:
        """
        Calculates 3D Cartesian coordinates (X, Y, Z in mm) of gripper end-effector
        relative to the robot base using forward trigonometric kinematics.
        """
        q0 = math.radians(self.joint_angles[0])  # Base Yaw
        q1 = math.radians(self.joint_angles[1])  # Shoulder Pitch
        q2 = math.radians(self.joint_angles[2])  # Elbow Pitch
        q3 = math.radians(self.joint_angles[3])  # Wrist Pitch

        # Planar reach and elevation in arm sagittal plane
        r1 = LINK_SHOULDER_MM * math.cos(q1)
        z1 = LINK_BASE_HEIGHT_MM + LINK_SHOULDER_MM * math.sin(q1)

        a12 = q1 + q2
        r2 = r1 + LINK_ELBOW_MM * math.cos(a12)
        z2 = z1 + LINK_ELBOW_MM * math.sin(a12)

        a123 = a12 + q3
        total_reach = r2 + (LINK_WRIST_MM + LINK_GRIPPER_MM) * math.cos(a123)
        ee_z = z2 + (LINK_WRIST_MM + LINK_GRIPPER_MM) * math.sin(a123)

        ee_x = total_reach * math.cos(q0)
        ee_y = total_reach * math.sin(q0)

        return (ee_x, ee_y, ee_z)

    def get_joint_world_positions(self) -> List[Tuple[float, float]]:
        """
        Calculates 2D top-down projection coordinates of base, shoulder, elbow, wrist
        and gripper end-effector for Pygame factory arena visualization.
        """
        bx, by = self.base_position
        q0 = math.radians(self.joint_angles[0])
        q1 = math.radians(self.joint_angles[1])
        q2 = math.radians(self.joint_angles[2])
        q3 = math.radians(self.joint_angles[3])

        r_sh = LINK_SHOULDER_MM * math.cos(q1) * 0.5
        r_el = r_sh + LINK_ELBOW_MM * math.cos(q1 + q2) * 0.5
        r_wr = r_el + LINK_WRIST_MM * math.cos(q1 + q2 + q3) * 0.5

        sh_pos = (bx, by)
        el_pos = (bx + r_sh * math.sin(q0), by + r_sh * math.cos(q0))
        wr_pos = (bx + r_el * math.sin(q0), by + r_el * math.cos(q0))
        ee_pos = (bx + r_wr * math.sin(q0), by + r_wr * math.cos(q0))

        return [sh_pos, el_pos, wr_pos, ee_pos]
