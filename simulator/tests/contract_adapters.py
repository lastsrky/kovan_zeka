"""
Opaque-Box Contract Adapters & Specification Oracles for TEKNOFEST 2026 SITL Simulator.
Derives directly from requirements R1-R4, PROJECT.md interface contracts,
and authoritative reference models in robotkol/ and otonomarac/.

Enables progressive testability:
- If simulator.core.* is implemented, delegates directly to concrete simulator classes.
- Otherwise, provides high-fidelity specification models that adhere 100% to
  the PROJECT.md architectural contracts and mathematical formulas.
"""

import sys
import os
import time
import math
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import cv2

# Add project root to sys.path to enable loading robotkol, otonomarac, simulator
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# CUBE & CONVEYOR SPECIFICATION MODELS
# ============================================================================

class SpecCube:
    """Represents a colored cube on the conveyor or carried by arm/vehicle."""
    def __init__(self, color: str, x: float = 0.0, y: float = 100.0, size: float = 40.0):
        color_upper = color.upper()
        if color_upper not in ("RED", "GREEN", "BLUE"):
            raise ValueError(f"Invalid cube color: {color}")
        self.color = color_upper
        self.x = float(x)
        self.y = float(y)
        self.size = float(size)
        self.is_picked = False
        self.is_loaded = False


class SpecConveyorBelt:
    """Models 800mm conveyor belt with entry (S1) and exit (S2) sensors."""
    def __init__(self, x: float = 120.0, y: float = 100.0, length: float = 260.0, speed: float = 80.0):
        self.x = x
        self.y = y
        self.length = length
        self.physical_length_mm = 800.0
        self.speed_mm_s = speed
        self.is_running = False
        self.active_cube: Optional[SpecCube] = None

    @property
    def has_cube_at_entry(self) -> bool:
        """Entry sensor S1 active when cube is in [0, 40] mm."""
        if self.active_cube and not self.active_cube.is_picked:
            return 0.0 <= self.active_cube.x <= 40.0
        return False

    @property
    def has_cube_at_exit(self) -> bool:
        """Exit sensor S2 active when cube is in [760, 800] mm."""
        if self.active_cube and not self.active_cube.is_picked:
            return 760.0 <= self.active_cube.x <= 800.0
        return False

    def add_cube(self, color: str) -> SpecCube:
        cube = SpecCube(color=color, x=0.0, y=self.y)
        self.active_cube = cube
        return cube

    def update(self, dt: float):
        if self.is_running and self.active_cube and not self.active_cube.is_picked:
            # Advance cube forward
            self.active_cube.x += self.speed_mm_s * dt
            if self.active_cube.x > self.physical_length_mm:
                self.active_cube.x = self.physical_length_mm


# ============================================================================
# FACTORY WORLD SPECIFICATION MODEL (F1)
# ============================================================================

class SpecFactoryWorld:
    """Models the 10.4m x 9.0m factory hall and 2D arena layout (F1)."""
    def __init__(self):
        self.arena_width = 1040
        self.arena_height = 900
        self.window_width = 1600
        self.window_height = 900
        self.conveyor = SpecConveyorBelt(x=120, y=100, length=260, speed=80)
        self.dock_pose = (380.0, 270.0, 0.0)  # Vehicle dock position (x, y, heading_rad)
        self.traffic_signs = {
            "pedestrian": (875, 420, 30, 30),  # Sign ID 0
            "parking": (520, 600, 30, 30)       # Sign ID 5
        }
        self.parking_bays = {
            "RED": (380, 625, 60, 40),
            "GREEN": (300, 625, 60, 40),
            "BLUE": (220, 625, 60, 40)
        }
        self.track_waypoints = [
            (380, 270),  # Dock
            (850, 270),  # End of Straight 1
            (850, 570),  # End of East Curve
            (520, 570),  # Approaching parking
            (250, 570),  # End of Straight 2
            (250, 270),  # End of West Curve
            (380, 270)   # Loop close
        ]

    def add_cube(self, color: str) -> SpecCube:
        return self.conveyor.add_cube(color)

    def step(self, dt: float):
        self.conveyor.update(dt)


# ============================================================================
# S7-1200 PLC ENGINE SPECIFICATION MODEL (F5, F6, F7, F8)
# ============================================================================

class SpecPLCEngine:
    """
    S7-1200 Discrete State Machine Engine (%I0.0-%I0.6, %Q0.0-%Q0.5).
    Replicates ladder logic:
    State 0: OFF
    State 1: READY
    State 2: FEEDING (conveyor moving, green lamp on)
    State 3: EXIT_STOPPED (conveyor stopped at exit, red lamp on)
    State 4: TRIGGER_ROBOT (robot trigger asserted)
    State 5: CYCLE_COMPLETE
    State 99: ESTOP_FREEZE (immediate motor cutoff, frozen until reset)
    """
    def __init__(self):
        # Digital Inputs (%I)
        self.I_START = False     # %I0.0
        self.I_STOP = False      # %I0.1
        self.I_ESTOP = False     # %I0.2 (True when button is pressed / latched)
        self.I_RESET = False     # %I0.3
        self.I_ENTRY = False     # %I0.4 (S1)
        self.I_EXIT = False      # %I0.5 (S2)
        self.I_VEHICLE_READY = True  # %I0.6 (S3: Car at dock)

        # Digital Outputs (%Q)
        self.Q_CONVEYOR_MOTOR = False  # %Q0.0
        self.Q_GREEN_LAMP = False      # %Q0.1
        self.Q_RED_LAMP = False        # %Q0.2
        self.Q_YELLOW_LAMP = False     # %Q0.3
        self.Q_ROBOT_TRIGGER = False   # %Q0.4
        self.Q_CYCLE_ACTIVE = False    # %Q0.5

        # Internal State
        self.state = 0  # 0: OFF, 1: READY, 2: FEEDING, 3: EXIT_STOPPED, 4: TRIGGER_ROBOT, 5: COMPLETE, 99: ESTOP
        self.cycle_count = 0
        self._estop_latched = False

    @property
    def is_running(self) -> bool:
        return self.Q_CONVEYOR_MOTOR

    @property
    def green_lamp(self) -> bool:
        return self.Q_GREEN_LAMP

    @property
    def red_lamp(self) -> bool:
        return self.Q_RED_LAMP

    @property
    def yellow_lamp(self) -> bool:
        return self.Q_YELLOW_LAMP

    @property
    def robot_trigger(self) -> bool:
        return self.Q_ROBOT_TRIGGER

    @property
    def estop_active(self) -> bool:
        return self._estop_latched

    def press_start(self):
        if not self._estop_latched:
            self.I_START = True

    def press_stop(self):
        self.I_STOP = True

    def press_estop(self):
        self.I_ESTOP = True
        self._estop_latched = True

    def release_estop(self):
        self.I_ESTOP = False

    def press_reset(self):
        self.I_RESET = True

    def update(self, dt: float, world: Optional[SpecFactoryWorld] = None):
        """Executes one PLC scan cycle."""
        # Update inputs from physical world if provided
        if world:
            self.I_ENTRY = world.conveyor.has_cube_at_entry
            self.I_EXIT = world.conveyor.has_cube_at_exit

        # E-STOP Priority Check (Immediate Cutoff <16ms)
        if self.I_ESTOP or self._estop_latched:
            self.state = 99
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_YELLOW_LAMP = True  # Warning lamp blinking/active
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False
            if world:
                world.conveyor.is_running = False

            # Reset check: Only clears if physical E-Stop is released AND Reset is pressed
            if not self.I_ESTOP and self.I_RESET:
                self._estop_latched = False
                self.I_RESET = False
                self.state = 0
                self.Q_YELLOW_LAMP = False
            return

        # Normal STOP button check
        if self.I_STOP:
            self.state = 0
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False
            self.I_STOP = False
            if world:
                world.conveyor.is_running = False
            return

        # Discrete State Machine Transition Logic
        if self.state == 0:  # OFF
            if self.I_START:
                self.I_START = False
                self.state = 1  # READY

        elif self.state == 1:  # READY
            if self.I_ENTRY:  # Cube detected at infeed
                self.state = 2  # FEEDING

        elif self.state == 2:  # FEEDING
            if self.I_EXIT:  # Cube arrived at exit
                self.state = 3  # EXIT_STOPPED

        elif self.state == 3:  # EXIT_STOPPED
            if self.I_VEHICLE_READY:
                self.state = 4  # TRIGGER_ROBOT

        elif self.state == 4:  # TRIGGER_ROBOT
            # Transition to 5 when cube is picked (exit sensor clears)
            if not self.I_EXIT:
                self.state = 5

        elif self.state == 5:  # CYCLE_COMPLETE
            self.cycle_count += 1
            self.state = 1  # Automatic loop back to READY

        # Evaluate Outputs Based on Current State
        if self.state == 0:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False
        elif self.state == 1:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True  # Ready/idle lamp
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True
        elif self.state == 2:
            self.Q_CONVEYOR_MOTOR = True
            self.Q_GREEN_LAMP = True  # Belt running
            self.Q_RED_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True
        elif self.state == 3:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True  # Stopped with part
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True
        elif self.state == 4:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True
            self.Q_ROBOT_TRIGGER = True  # S7-1200 %Q0.4 active trigger
            self.Q_CYCLE_ACTIVE = True
        elif self.state == 5:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True

        # Synchronize physical conveyor motor with PLC output %Q0.0
        if world:
            world.conveyor.is_running = self.Q_CONVEYOR_MOTOR


# ============================================================================
# VIRTUAL CAMERAS SPECIFICATION MODEL (F2, F3, F4)
# ============================================================================

class SpecVirtualCameras:
    """
    Virtual RealSense Camera Generator:
    - Arm Overhead RealSense Camera (640x480 BGR) focused on conveyor exit.
    - Vehicle RealSense D455 (640x480 BGR + 16-bit Depth Z16).
    """
    def __init__(self):
        self.roi = (215, 120, 251, 240)  # Calibrated ROI (x, y, w, h)

    def get_arm_frame(self, cube: Optional[SpecCube] = None, noise_std: float = 2.0) -> np.ndarray:
        """
        Synthesizes top-down 640x480 BGR frame of conveyor exit.
        Colors match exact calibrated values from renk_kalibrasyon.json:
        RED: RGB (220, 20, 25) -> BGR (25, 20, 220)
        GREEN: RGB (20, 210, 30) -> BGR (30, 210, 20)
        BLUE: RGB (25, 35, 220) -> BGR (220, 35, 25)
        """
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)  # Steel grey belt background
        # Conveyor belt track area
        cv2.rectangle(frame, (100, 50), (540, 430), (55, 55, 60), -1)

        if cube and not cube.is_picked:
            # Draw cube inside ROI with fill ratio >= 45% of ROI
            rx, ry, rw, rh = self.roi
            cx = rx + rw // 2
            cy = ry + rh // 2
            half_s = int(min(rw, rh) * 0.38)

            if cube.color == "RED":
                bgr = (47, 13, 220)
            elif cube.color == "GREEN":
                bgr = (157, 210, 12)
            elif cube.color == "BLUE":
                bgr = (220, 137, 13)
            else:
                bgr = (128, 128, 128)

            cv2.rectangle(frame, (cx - half_s, cy - half_s), (cx + half_s, cy + half_s), bgr, -1)

        # Add Gaussian sensor noise
        if noise_std > 0:
            noise = np.random.normal(0, noise_std, frame.shape).astype(np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return frame

    def get_vehicle_frame(self, pose: Tuple[float, float, float] = (380.0, 270.0, 0.0),
                          target_sign: Optional[str] = None,
                          target_bay: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Synthesizes perspective 640x480 BGR image and aligned 16-bit depth (Z16) array.
        Depth is in millimeters (1 unit = 1 mm).
        """
        bgr = np.full((480, 640, 3), fill_value=30, dtype=np.uint8)  # Dark hall asphalt
        depth = np.full((480, 640), fill_value=3000, dtype=np.uint16)  # Default 3000mm

        # Render perspective road lanes (Left lane, Right lane)
        # In perspective, lines converge towards vanishing point (320, 140)
        pts_left = np.array([[120, 480], [180, 340], [280, 200], [310, 150]], dtype=np.int32)
        pts_right = np.array([[520, 480], [460, 340], [360, 200], [330, 150]], dtype=np.int32)
        cv2.polylines(bgr, [pts_left], isClosed=False, color=(240, 240, 240), thickness=8)
        cv2.polylines(bgr, [pts_right], isClosed=False, color=(240, 240, 240), thickness=8)

        # Depth gradient for ground plane: closer at bottom (500mm), farther at top (3500mm)
        for y in range(140, 480):
            d_mm = int(500 + (480 - y) * 9)
            depth[y, :] = np.clip(d_mm, 250, 4000)

        # Render pedestrian zebra stripes or sign if present
        if target_sign == "pedestrian":
            # Zebra crossing stripes
            for stripe_x in range(220, 420, 40):
                cv2.rectangle(bgr, (stripe_x, 300), (stripe_x + 20, 360), (255, 255, 255), -1)
                depth[300:360, stripe_x:stripe_x+20] = 1200  # 1.2m away

        # Render colored ground parking bay if approaching
        if target_bay:
            bay_color_upper = target_bay.upper()
            if bay_color_upper == "RED":
                bay_bgr = (25, 20, 220)
            elif bay_color_upper == "GREEN":
                bay_bgr = (30, 210, 20)
            elif bay_color_upper == "BLUE":
                bay_bgr = (220, 35, 25)
            else:
                bay_bgr = (100, 100, 100)

            # Draw parking bay polygon on road floor (bottom half of frame)
            bay_poly = np.array([[220, 460], [420, 460], [380, 360], [260, 360]], dtype=np.int32)
            cv2.fillPoly(bgr, [bay_poly], bay_bgr)
            depth[360:460, 220:420] = 800  # 800mm away

        return bgr, depth


# ============================================================================
# CLASSICAL HSV COLOR DETECTOR (F11, F12)
# ============================================================================

class SpecColorResult:
    def __init__(self, color: str, confidence: float, fill_ratio: float, margin: float):
        self.renk = color
        self.guven = float(confidence)
        self.doluluk = float(fill_ratio)
        self.marj = float(margin)


class SpecColorDetector:
    """
    Classical OpenCV HSV Color Detector.
    Strictly matches robotkol/renk_algila.py and renk_kalibrasyon.json:
    - No deep learning/AI.
    - Two-interval RED: [0, 10] and [170, 179].
    - Single-interval GREEN: [40, 85].
    - Single-interval BLUE: [95, 130].
    - Occupancy threshold: doluluk >= 0.40.
    - Confidence margin: margin >= 0.12.
    """
    def __init__(self):
        # Default HSV ranges from renk_algila.py
        self.hsv_ranges = {
            "RED": [
                ((0, 100, 70), (10, 255, 255)),
                ((170, 100, 70), (179, 255, 255))
            ],
            "GREEN": [
                ((40, 70, 55), (85, 255, 255))
            ],
            "BLUE": [
                ((95, 90, 55), (130, 255, 255))
            ]
        }
        self.kalib = type("Kalib", (), {"hsv": self.hsv_ranges})()
        self.doluluk_esigi = 0.40
        self.marj = 0.12
        self.roi = (215, 120, 251, 240)

    def detect(self, frame: np.ndarray) -> SpecColorResult:
        h, w = frame.shape[:2]
        rx, ry, rw, rh = self.roi
        rx = max(0, min(rx, w - 1))
        ry = max(0, min(ry, h - 1))
        rw = max(1, min(rw, w - rx))
        rh = max(1, min(rh, h - ry))
        roi = frame[ry:ry+rh, rx:rx+rw]
        total_pixels = float(rw * rh)

        blurred = cv2.GaussianBlur(roi, (5, 5), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        kernel = np.ones((3, 3), np.uint8)

        ratios: Dict[str, float] = {}
        for color, ranges in self.hsv_ranges.items():
            mask_total = np.zeros((rh, rw), dtype=np.uint8)
            for lower, upper in ranges:
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                m = cv2.inRange(hsv, lower_np, upper_np)
                mask_total = cv2.bitwise_or(mask_total, m)
            mask_cleaned = cv2.morphologyEx(mask_total, cv2.MORPH_OPEN, kernel)
            cnt = cv2.countNonZero(mask_cleaned)
            ratios[color] = cnt / total_pixels

        sorted_colors = sorted(ratios.items(), key=lambda item: item[1], reverse=True)
        top_color, top_ratio = sorted_colors[0]
        second_ratio = sorted_colors[1][1] if len(sorted_colors) > 1 else 0.0
        margin = top_ratio - second_ratio

        if top_ratio >= self.doluluk_esigi and margin >= self.marj:
            return SpecColorResult(top_color, top_ratio, top_ratio, margin)
        else:
            return SpecColorResult("UNKNOWN", top_ratio, top_ratio, margin)

    def algila(self, frame: np.ndarray) -> SpecColorResult:
        return self.detect(frame)


class ColorDetectorAdapter:
    """Adapts RenkAlgilayici or SpecColorDetector to ensure uniform detect() and algila() interface."""
    def __init__(self, inner=None):
        if inner is not None:
            self.inner = inner
        else:
            try:
                from robotkol.renk_algila import RenkAlgilayici
                self.inner = RenkAlgilayici()
            except (ImportError, AttributeError):
                self.inner = SpecColorDetector()

        # Provide uniform attributes
        self.hsv_ranges = getattr(self.inner, "hsv_ranges", None)
        if self.hsv_ranges is None and hasattr(self.inner, "kalib"):
            self.hsv_ranges = self.inner.kalib.hsv
        self.kalib = getattr(self.inner, "kalib", type("Kalib", (), {"hsv": self.hsv_ranges})())

    def detect(self, frame: np.ndarray) -> SpecColorResult:
        if hasattr(self.inner, "detect"):
            return self.inner.detect(frame)
        elif hasattr(self.inner, "algila"):
            res = self.inner.algila(frame)
            return SpecColorResult(
                color=res.renk,
                confidence=res.doluluk,
                fill_ratio=res.doluluk,
                margin=0.2 if res.emin else 0.0
            )
        raise AttributeError("Inner detector has neither detect nor algila")

    def algila(self, frame: np.ndarray) -> SpecColorResult:
        return self.detect(frame)


# ============================================================================
# 4-DOF ROBOT ARM SIMULATION SPECIFICATION MODEL (F13, F14, F15)
# ============================================================================

class SpecRobotArmSim:
    """
    4-DOF Manipulator and State Machine:
    HOME -> GORME -> BASLA_BEK -> RENK -> AL -> DOGRULA -> YUKLE -> GONDER
    Monitors PLC trigger (%Q0.4 / Arduino A5) while in BASLA_BEK.
    """
    def __init__(self, mqtt_client=None):
        self.state = "HOME"
        self.gripper_angle = 140.0  # 140: open, 50: closed
        self.joint_angles = [0.0, 0.0, 0.0, 0.0]  # Base, Shoulder, Elbow, Wrist
        self.detected_color = "UNKNOWN"
        self.carried_cube: Optional[SpecCube] = None
        self.mqtt_client = mqtt_client
        self.is_frozen = False
        self.cycles_completed = 0

    def freeze(self):
        self.is_frozen = True

    def unfreeze(self):
        self.is_frozen = False

    def step(self, dt: float, plc_trigger: bool = False,
             camera_frame: Optional[np.ndarray] = None,
             detector: Optional[SpecColorDetector] = None,
             world: Optional[SpecFactoryWorld] = None):
        """Advances robot arm state machine."""
        if self.is_frozen:
            return

        if self.state == "HOME":
            self.joint_angles = [0.0, 10.0, -10.0, 0.0]
            self.gripper_angle = 140.0
            self.state = "GORME"

        elif self.state == "GORME":
            self.joint_angles = [0.0, 45.0, 30.0, -15.0]
            self.state = "BASLA_BEK"

        elif self.state == "BASLA_BEK":
            # Wait for PLC start trigger (%Q0.4)
            if plc_trigger:
                self.state = "RENK"

        elif self.state == "RENK":
            if camera_frame is not None and detector is not None:
                res = detector.detect(camera_frame)
                self.detected_color = res.renk
            else:
                self.detected_color = "RED"  # Fallback
            self.state = "AL"

        elif self.state == "AL":
            # Pick cube from conveyor exit
            self.joint_angles = [0.0, 80.0, 60.0, -40.0]
            self.gripper_angle = 50.0  # Close gripper
            if world and world.conveyor.active_cube:
                self.carried_cube = world.conveyor.active_cube
                self.carried_cube.is_picked = True
                world.conveyor.active_cube = None
            self.state = "DOGRULA"

        elif self.state == "DOGRULA":
            # Verify pick
            if self.carried_cube is not None:
                self.state = "YUKLE"
            else:
                self.state = "HOME"

        elif self.state == "YUKLE":
            # Move arm over docked autonomous car
            self.joint_angles = [90.0, 50.0, 20.0, -20.0]
            self.gripper_angle = 140.0  # Release cube onto vehicle
            if self.carried_cube:
                self.carried_cube.is_loaded = True
            self.state = "GONDER"

        elif self.state == "GONDER":
            # Publish MQTT message
            if self.mqtt_client:
                self.mqtt_client.publish("arac/yuk", self.detected_color, qos=1)
                self.mqtt_client.publish("robot/basla", "BASLA", qos=1)
            self.cycles_completed += 1
            self.carried_cube = None
            self.state = "HOME"


# ============================================================================
# EMBEDDED MQTT BROKER / BRIDGE (F16)
# ============================================================================

class SpecMQTTBroker:
    """
    Lightweight Embedded In-Memory MQTT Broker.
    Topic publication: arac/yuk (RED/GREEN/BLUE), robot/basla, robot/veri.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Any]] = {}
        self.messages: List[Tuple[str, str, float]] = []

    def subscribe(self, topic: str, callback):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False):
        self.messages.append((topic, payload, time.time()))
        if topic in self.subscribers:
            for cb in self.subscribers[topic]:
                try:
                    cb(topic, payload)
                except Exception as e:
                    pass

    def get_last_message(self, topic: str) -> Optional[str]:
        for t, p, _ in reversed(self.messages):
            if t == topic:
                return p
        return None

    def clear(self):
        self.messages.clear()


# ============================================================================
# AUTONOMOUS VEHICLE SIMULATION SPECIFICATION MODEL (F17, F18, F19, F20, F21, F22)
# ============================================================================

class SpecVehicleSim:
    """
    Autonomous Vehicle Simulation:
    - 2D Bicycle Kinematics: x, y, theta, velocity, steering_angle in [75, 145] deg (center 110).
    - Vision Lane Tracking PID controller.
    - MQTT Auto-Start on arac/yuk + robot/basla.
    - Pedestrian crossing sign detection & 3.0s stop.
    - Color Parking Bay Alignment & Precision Bay Stop (d <= 25 cm -> ETTI, PWM=0).
    """
    def __init__(self, world: Optional[SpecFactoryWorld] = None):
        self.world = world
        self.x = 380.0
        self.y = 270.0
        self.heading = 0.0  # Radians (0 = East)
        self.velocity = 0.0  # px/s
        self.target_speed = 60.0  # px/s
        self.wheelbase = 25.0  # px (25 cm)
        self.servo_angle = 110.0  # 110: center, [75, 145]
        self.pwm = 0

        # Autonomous state
        self.is_autonomous = False
        self.received_color: Optional[str] = None
        self.received_start = False
        self.task_state = "IDLE"  # IDLE, LANE_KEEP, PEDESTRIAN_STOP, PARK_APPROACH, PARK_ETTI
        self.stop_timer = 0.0
        self.is_estop = False
        self.target_bay_color: Optional[str] = None
        self.completed = False

    def on_mqtt_message(self, topic: str, payload: str):
        if topic == "arac/yuk":
            norm = payload.strip().upper()
            if norm in ("KIRMIZI", "RED"):
                self.received_color = "RED"
            elif norm in ("YESIL", "YEŞIL", "GREEN"):
                self.received_color = "GREEN"
            elif norm in ("MAVI", "BLUE"):
                self.received_color = "BLUE"
            self.target_bay_color = self.received_color
        elif topic == "robot/basla":
            if "BASLA" in payload.upper():
                self.received_start = True

        # Auto-start condition: both color and start received
        if self.received_color and self.received_start and not self.is_estop:
            self.is_autonomous = True
            self.task_state = "LANE_KEEP"

    def estop(self):
        self.is_estop = True
        self.velocity = 0.0
        self.pwm = 0

    def reset_estop(self):
        self.is_estop = False

    def step(self, dt: float):
        """Simulates vehicle physics and task progression."""
        if self.is_estop:
            self.velocity = 0.0
            self.pwm = 0
            return

        if not self.is_autonomous:
            return

        if self.task_state == "LANE_KEEP":
            self.velocity = self.target_speed
            self.pwm = 90
            # Follow track: dock (380,270) -> straight 1 -> turn 1 (850,270 to 850,570)
            if self.x < 850 and self.y <= 300:
                self.x += self.velocity * dt
                self.heading = 0.0
                self.servo_angle = 110.0
            elif self.x >= 850 and self.y < 570:
                # East Curve turn
                self.servo_angle = 135.0  # Turn right
                self.y += self.velocity * dt
                self.heading = math.pi / 2.0
                # Check pedestrian crossing sign (y ≈ 420)
                if 410 <= self.y <= 440 and self.stop_timer == 0.0:
                    self.task_state = "PEDESTRIAN_STOP"
                    self.stop_timer = 3.0
                    self.velocity = 0.0
                    self.pwm = 0
            elif self.y >= 570 and self.x > 400:
                # Heading West on Straight 2 towards parking bays
                self.x -= self.velocity * dt
                self.heading = math.pi
                self.servo_angle = 110.0
                if self.x <= 460:
                    self.task_state = "PARK_APPROACH"

        elif self.task_state == "PEDESTRIAN_STOP":
            self.velocity = 0.0
            self.pwm = 0
            self.stop_timer -= dt
            if self.stop_timer <= 0.0:
                self.stop_timer = -1.0  # Mark completed
                self.task_state = "LANE_KEEP"
                self.velocity = self.target_speed
                self.pwm = 90

        elif self.task_state == "PARK_APPROACH":
            self.velocity = 30.0  # Slow approach
            self.pwm = 60
            # Target parking bay coordinate
            target_x = 380.0
            if self.target_bay_color == "GREEN":
                target_x = 300.0
            elif self.target_bay_color == "BLUE":
                target_x = 220.0

            # Proportional alignment towards bay X
            dx = target_x - self.x
            self.x += dx * min(1.0, 3.0 * dt)
            self.y += self.velocity * dt * 0.5

            # Distance to stop line (y=625)
            dist_to_bay = 625.0 - self.y
            if dist_to_bay <= 25.0:  # <= 25 cm Precision Bay Stop
                self.task_state = "PARK_ETTI"
                self.velocity = 0.0
                self.pwm = 0
                self.completed = True

        elif self.task_state == "PARK_ETTI":
            self.velocity = 0.0
            self.pwm = 0


# ============================================================================
# HMI PANEL SPECIFICATION MODEL (F9, F10)
# ============================================================================

class SpecHMIPanel:
    """Industrial HMI Pushbuttons and Live Telemetry."""
    def __init__(self, plc: SpecPLCEngine):
        self.plc = plc
        self.counters = {
            "total": 0,
            "RED": 0,
            "GREEN": 0,
            "BLUE": 0
        }
        self.mqtt_log: List[str] = []

    def press_start(self):
        self.plc.press_start()

    def press_stop(self):
        self.plc.press_stop()

    def press_estop(self):
        self.plc.press_estop()

    def press_reset(self):
        self.plc.press_reset()

    def add_cube(self, world: SpecFactoryWorld, color: str):
        cube = world.add_cube(color)
        color_upper = color.upper()
        if color_upper in self.counters:
            self.counters[color_upper] += 1
        self.counters["total"] += 1
        return cube

    def log_mqtt(self, topic: str, payload: str):
        entry = f"[{topic}] {payload}"
        self.mqtt_log.append(entry)


# ============================================================================
# DYNAMIC ADAPTER FACTORY (Checks for simulator.core vs Spec fallback)
# ============================================================================

def get_factory_world():
    try:
        from simulator.core.factory_world import FactoryWorld
        return FactoryWorld()
    except (ImportError, AttributeError):
        return SpecFactoryWorld()


def get_plc_engine():
    try:
        from simulator.core.plc_engine import PLCEngine
        return PLCEngine()
    except (ImportError, AttributeError):
        return SpecPLCEngine()


def get_virtual_cameras():
    try:
        from simulator.core.virtual_cameras import VirtualCameras
        return VirtualCameras()
    except (ImportError, AttributeError):
        return SpecVirtualCameras()


def get_color_detector():
    try:
        from simulator.core.color_detector_sim import ColorDetectorSim
        return ColorDetectorSim()
    except (ImportError, AttributeError):
        return ColorDetectorAdapter()


def get_robot_arm(mqtt_client=None):
    try:
        from simulator.core.robot_arm_sim import RobotArmSim
        return RobotArmSim(mqtt_client=mqtt_client)
    except (ImportError, AttributeError):
        return SpecRobotArmSim(mqtt_client=mqtt_client)


def get_mqtt_broker():
    try:
        from simulator.core.mqtt_broker import MQTTBroker
        return MQTTBroker()
    except (ImportError, AttributeError):
        return SpecMQTTBroker()


def get_vehicle_sim(world=None):
    try:
        from simulator.core.vehicle_sim import VehicleSim
        return VehicleSim(world=world)
    except (ImportError, AttributeError):
        return SpecVehicleSim(world=world)


def get_hmi_panel(plc):
    try:
        from simulator.gui.hmi_panel import HMIPanel
        return HMIPanel(plc)
    except (ImportError, AttributeError):
        return SpecHMIPanel(plc)
