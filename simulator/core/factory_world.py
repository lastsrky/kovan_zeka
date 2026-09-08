"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Continuous 2D Simulation Physics Engine

Author: M1 Core Simulator Team
Module: simulator.core.factory_world
"""

from __future__ import annotations
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from simulator.config import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    BAY_BLUE_CENTER,
    BAY_BLUE_RECT,
    BAY_BLUE_TUPLE,
    BAY_GREEN_CENTER,
    BAY_GREEN_RECT,
    BAY_GREEN_TUPLE,
    BAY_RED_CENTER,
    BAY_RED_RECT,
    BAY_RED_TUPLE,
    COLOR_CUBE_BLUE,
    COLOR_CUBE_GREEN,
    COLOR_CUBE_RED,
    CONVEYOR_BELT_SPEED_NOMINAL,
    CONVEYOR_PHYSICAL_LENGTH_MM,
    CONVEYOR_RECT,
    CONVEYOR_SPEED_MM_S,
    CUBE_SIZE_PX,
    EAST_CURVE_CENTER,
    EAST_CURVE_RADIUS,
    ROAD_WIDTH,
    ROBOT_BASE_POS,
    ROBOT_PICK_COORDINATE,
    ROBOT_PLACE_COORDINATE,
    SCALE_METERS_PER_PX,
    SCALE_PX_PER_METER,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SENSOR_S1_HEIGHT,
    SENSOR_S1_X,
    SENSOR_S1_Y,
    SENSOR_S2_HEIGHT,
    SENSOR_S2_X,
    SENSOR_S2_Y,
    SENSOR_S3_CENTER,
    SENSOR_S3_RADIUS,
    SIGN_PARK_POS,
    SIGN_PARK_SIZE,
    SIGN_PEDESTRIAN_POS,
    SIGN_PEDESTRIAN_SIZE,
    TRACK_STRAIGHT_1_END,
    TRACK_STRAIGHT_1_START,
    TRACK_STRAIGHT_2_END,
    TRACK_STRAIGHT_2_START,
    TRACK_STRAIGHT_3_END,
    TRACK_STRAIGHT_3_START,
    TRACK_WAYPOINTS,
    VEHICLE_ACCEL_MAX,
    VEHICLE_BED_OFFSET_PX,
    VEHICLE_DECEL_MAX,
    VEHICLE_DOCK_CENTER,
    VEHICLE_INITIAL_HEADING,
    VEHICLE_LENGTH_PX,
    VEHICLE_MAX_SPEED_PX_S,
    VEHICLE_STEER_MAX_RAD,
    VEHICLE_STEER_MIN_RAD,
    VEHICLE_WHEELBASE_PX,
    VEHICLE_WIDTH_PX,
    WEST_CURVE_CENTER,
    WEST_CURVE_RADIUS,
)


# =====================================================================
# 1. ENUMERATIONS & STATE DEFINITIONS
# =====================================================================
class CubeColor(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"


class CubeState(Enum):
    SPAWNED = auto()       # S1 infeed zone
    ON_CONVEYOR = auto()   # Advancing along belt towards exit
    AT_EXIT = auto()       # Stopped at discharge, detected by S2
    HELD_BY_ARM = auto()   # Latched by 4-DOF robot arm gripper
    ON_VEHICLE = auto()    # Transported on autonomous vehicle cargo bed
    DELIVERED = auto()     # Parked inside designated color bay


class VehicleDrivingState(str, Enum):
    DOCKED = "DOCKED"             # Waiting at loading dock
    LANE_FOLLOW = "LANE_FOLLOW"   # Standard visual lane keeping
    PEDESTRIAN_STOP = "PED_STOP"  # Halting for pedestrian zebra crossing
    PEDESTRIAN_PASS = "PED_PASS"  # Blind straight crossing
    PARK_APPROACH = "PARK_APP"    # Approaching parking bay via floor HSV
    PARKED_FINISHED = "PARKED"    # Terminal mission complete
    ESTOP_FROZEN = "ESTOP"        # Hardware emergency stop freeze


# =====================================================================
# 2. CUBE ENTITY
# =====================================================================
class Cube:
    """
    Represents an industrial workpiece cube in continuous 2D space.
    Synchronizes conveyor longitudinal coordinate (x in mm, [0, 800])
    with continuous 2D Euclidean arena coordinates.
    """
    def __init__(
        self,
        color: Union[str, CubeColor],
        x: float = 0.0,
        y: float = 100.0,
        size: float = 40.0,
        cube_id: Optional[str] = None,
    ):
        color_str = color.value if isinstance(color, CubeColor) else str(color).upper()
        if color_str not in ("RED", "GREEN", "BLUE"):
            raise ValueError(f"Invalid cube color: {color}")

        self.color: str = color_str
        self.cube_id: str = cube_id or f"CUBE_{color_str}_{id(self) % 1000:03d}"
        self._x: float = float(x)  # Longitudinal conveyor coordinate in mm [0, 800]
        self.y: float = float(y)
        self.size: float = float(size)
        self.is_picked: bool = False
        self.is_loaded: bool = False
        self.state: CubeState = CubeState.SPAWNED
        self.carrier: Optional[object] = None

        if self.color == "RED":
            self.rgb: Tuple[int, int, int] = COLOR_CUBE_RED
        elif self.color == "GREEN":
            self.rgb = COLOR_CUBE_GREEN
        elif self.color == "BLUE":
            self.rgb = COLOR_CUBE_BLUE
        else:
            self.rgb = (200, 200, 200)

        # 2D arena position [px_x, px_y]
        self.position: np.ndarray = np.zeros(2, dtype=np.float64)
        self._sync_position()

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, val: float):
        self._x = float(val)
        self._sync_position()

    def _sync_position(self):
        """Maps conveyor coordinate x (0 to 800 mm) to 2D arena pixels [120, 360]."""
        if not self.is_picked and not self.is_loaded:
            px_x = 120.0 + (max(0.0, min(800.0, self._x)) / 800.0) * 240.0
            px_y = self.y + 30.0
            self.position[0] = px_x
            self.position[1] = px_y

    def get_aabb(self) -> Tuple[float, float, float, float]:
        """Returns Axis-Aligned Bounding Box (xmin, ymin, xmax, ymax) in 2D pixels."""
        half = CUBE_SIZE_PX / 2.0
        return (self.position[0] - half, self.position[1] - half,
                self.position[0] + half, self.position[1] + half)

    def update_carried(self, carrier_pose: Tuple[float, float, float], offset: float = 0.0):
        """Updates cube coordinates when physically carried by an entity."""
        cx, cy, heading = carrier_pose
        self.position[0] = cx + offset * math.cos(heading)
        self.position[1] = cy + offset * math.sin(heading)


# =====================================================================
# 3. OPTICAL SENSOR ENTITIES
# =====================================================================
class BeamSensor:
    """Models an industrial optical beam-break sensor."""
    def __init__(self, sensor_id: str, p1: Tuple[float, float], p2: Tuple[float, float]):
        self.sensor_id: str = sensor_id
        self.p1: np.ndarray = np.array(p1, dtype=np.float64)
        self.p2: np.ndarray = np.array(p2, dtype=np.float64)
        self.is_active: bool = False
        self.detected_cube: Optional[Cube] = None

    def evaluate(self, cubes: List[Cube]) -> bool:
        self.is_active = False
        self.detected_cube = None

        bx = self.p1[0]
        by_min = min(self.p1[1], self.p2[1])
        by_max = max(self.p1[1], self.p2[1])

        for cube in cubes:
            if cube.is_picked or cube.is_loaded or cube.state == CubeState.DELIVERED:
                continue

            xmin, ymin, xmax, ymax = cube.get_aabb()
            if (xmin <= bx <= xmax) and (max(ymin, by_min) <= min(ymax, by_max)):
                self.is_active = True
                self.detected_cube = cube
                break

        return self.is_active


class ProximitySensor:
    """Models an inductive / optical proximity sensor with a circular detection radius."""
    def __init__(self, sensor_id: str, center: Tuple[float, float], radius: float):
        self.sensor_id: str = sensor_id
        self.center: np.ndarray = np.array(center, dtype=np.float64)
        self.radius: float = radius
        self.is_active: bool = False

    def evaluate(self, target_pos: Tuple[float, float]) -> bool:
        dist = math.hypot(target_pos[0] - self.center[0], target_pos[1] - self.center[1])
        self.is_active = (dist <= self.radius)
        return self.is_active


# =====================================================================
# 4. CONVEYOR BELT SUBSYSTEM
# =====================================================================
class ConveyorBelt:
    """
    Models the S7-1200 driven conveyor belt with entry/exit sensors
    and automated cube transit mechanics.
    """
    def __init__(
        self,
        x: float = 120.0,
        y: float = 100.0,
        length: float = 260.0,
        speed: float = 80.0,
    ):
        self.x: float = x
        self.y: float = y
        self.length: float = length
        self.width: float = length
        self.height: float = 60.0
        self.physical_length_mm: float = CONVEYOR_PHYSICAL_LENGTH_MM  # 800.0 mm
        self.speed_mm_s: float = speed                                # 80.0 mm/s
        self.speed: float = CONVEYOR_BELT_SPEED_NOMINAL               # 20.0 px/s
        self.is_running: bool = False

        # Physical optical beam sensors
        self.sensor_s1 = BeamSensor(
            "S1_ENTRY",
            (SENSOR_S1_X, SENSOR_S1_Y),
            (SENSOR_S1_X, SENSOR_S1_Y + SENSOR_S1_HEIGHT),
        )
        self.sensor_s2 = BeamSensor(
            "S2_EXIT",
            (SENSOR_S2_X, SENSOR_S2_Y),
            (SENSOR_S2_X, SENSOR_S2_Y + SENSOR_S2_HEIGHT),
        )

        self.cubes: List[Cube] = []
        self._active_cube: Optional[Cube] = None
        self._next_cube_id: int = 1
        self.roller_animation_offset: float = 0.0

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

    @property
    def active_cube(self) -> Optional[Cube]:
        """Returns the primary cube currently on the belt (if any)."""
        if self._active_cube is not None:
            if self._active_cube.is_picked or self._active_cube.is_loaded or self._active_cube.state == CubeState.DELIVERED:
                return None
            return self._active_cube
        return None

    @active_cube.setter
    def active_cube(self, val: Optional[Cube]):
        self._active_cube = val

    def add_cube(self, color: str) -> Cube:
        """Adds a new cube at the infeed station."""
        cube = Cube(color=color, x=0.0, y=self.y, cube_id=f"CUBE_{self._next_cube_id:03d}")
        self._next_cube_id += 1
        self.cubes.append(cube)
        self._active_cube = cube
        self.sensor_s1.evaluate(self.cubes)
        self.sensor_s2.evaluate(self.cubes)
        return cube

    def spawn_cube(self, color_name: str) -> Optional[Cube]:
        """Convenience method matching add_cube."""
        return self.add_cube(color_name)

    def update(self, dt: float):
        """Advances active cube forward along belt when motor is running."""
        if self.is_running and self.active_cube and not self.active_cube.is_picked:
            self.roller_animation_offset = (self.roller_animation_offset + self.speed * dt) % 24.0
            self.active_cube.state = CubeState.ON_CONVEYOR
            self.active_cube.x += self.speed_mm_s * dt

            # Clamp at conveyor discharge
            if self.active_cube.x >= self.physical_length_mm:
                self.active_cube.x = self.physical_length_mm
                self.active_cube.state = CubeState.AT_EXIT

        # Evaluate optical sensors
        self.sensor_s1.evaluate(self.cubes)
        self.sensor_s2.evaluate(self.cubes)

    def remove_cube_at_exit(self) -> Optional[Cube]:
        """Transfers cube to robot arm gripper."""
        for i, cube in enumerate(self.cubes):
            if cube.state == CubeState.AT_EXIT or cube.x >= 760.0:
                cube.is_picked = True
                cube.state = CubeState.HELD_BY_ARM
                self._active_cube = None
                return self.cubes.pop(i)
        return None

    def reset(self):
        self.cubes.clear()
        self._active_cube = None
        self.is_running = False
        self.roller_animation_offset = 0.0
        self.sensor_s1.evaluate(self.cubes)
        self.sensor_s2.evaluate(self.cubes)


# =====================================================================
# 5. TRACK CIRCUIT & PATH GEOMETRY
# =====================================================================
class TrackSegmentType(Enum):
    STRAIGHT = auto()
    ARC_CW = auto()


class TrackSegment:
    def __init__(
        self,
        seg_type: TrackSegmentType,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        center_pos: Optional[Tuple[float, float]] = None,
        radius: Optional[float] = None,
        start_angle: Optional[float] = None,
        end_angle: Optional[float] = None,
        length: float = 0.0,
    ):
        self.seg_type = seg_type
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.center_pos = center_pos
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.length = length


class Track:
    """
    Parametric closed-loop 2-lane circuit track.
    Provides ground truth spline evaluation, lane boundary geometry,
    lookahead projections, and distance-to-centerline queries.
    """
    def __init__(self, road_width: float = ROAD_WIDTH):
        self.road_width: float = road_width
        self.lane_width: float = road_width / 2.0
        self.segments: List[TrackSegment] = []
        self._build_circuit()

    def _build_circuit(self):
        # Segment 1: Straight North (Dock to East Turn)
        len1 = TRACK_STRAIGHT_1_END[0] - TRACK_STRAIGHT_1_START[0]
        self.segments.append(
            TrackSegment(
                seg_type=TrackSegmentType.STRAIGHT,
                start_pos=TRACK_STRAIGHT_1_START,
                end_pos=TRACK_STRAIGHT_1_END,
                length=len1,
            )
        )

        # Segment 2: East Arc (Semicircle Clockwise)
        len2 = math.pi * EAST_CURVE_RADIUS
        self.segments.append(
            TrackSegment(
                seg_type=TrackSegmentType.ARC_CW,
                start_pos=TRACK_STRAIGHT_1_END,
                end_pos=TRACK_STRAIGHT_2_START,
                center_pos=EAST_CURVE_CENTER,
                radius=EAST_CURVE_RADIUS,
                start_angle=-math.pi / 2.0,
                end_angle=math.pi / 2.0,
                length=len2,
            )
        )

        # Segment 3: Straight South (Heading West from 850 to 250)
        len3 = TRACK_STRAIGHT_2_START[0] - TRACK_STRAIGHT_2_END[0]
        self.segments.append(
            TrackSegment(
                seg_type=TrackSegmentType.STRAIGHT,
                start_pos=TRACK_STRAIGHT_2_START,
                end_pos=TRACK_STRAIGHT_2_END,
                length=len3,
            )
        )

        # Segment 4: West Arc (Semicircle Clockwise)
        len4 = math.pi * WEST_CURVE_RADIUS
        self.segments.append(
            TrackSegment(
                seg_type=TrackSegmentType.ARC_CW,
                start_pos=TRACK_STRAIGHT_2_END,
                end_pos=TRACK_STRAIGHT_3_START,
                center_pos=WEST_CURVE_CENTER,
                radius=WEST_CURVE_RADIUS,
                start_angle=math.pi / 2.0,
                end_angle=3.0 * math.pi / 2.0,
                length=len4,
            )
        )

        # Segment 5: Straight Dock Approach (250 to 380)
        len5 = TRACK_STRAIGHT_3_END[0] - TRACK_STRAIGHT_3_START[0]
        self.segments.append(
            TrackSegment(
                seg_type=TrackSegmentType.STRAIGHT,
                start_pos=TRACK_STRAIGHT_3_START,
                end_pos=TRACK_STRAIGHT_3_END,
                length=len5,
            )
        )

        self.total_length: float = sum(s.length for s in self.segments)

    def get_closest_centerline_point(
        self, pos: Tuple[float, float]
    ) -> Tuple[float, float, float, float]:
        """Returns: (proj_x, proj_y, tangent_heading_rad, lateral_distance_error)"""
        px, py = pos
        best_dist = float("inf")
        best_proj = (px, py)
        best_heading = 0.0

        for seg in self.segments:
            if seg.seg_type == TrackSegmentType.STRAIGHT:
                x1, y1 = seg.start_pos
                x2, y2 = seg.end_pos
                dx = x2 - x1
                dy = y2 - y1
                seg_len = seg.length
                if seg_len <= 1e-6:
                    continue

                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (seg_len * seg_len)))
                qx = x1 + t * dx
                qy = y1 + t * dy
                dist = math.hypot(px - qx, py - qy)

                if dist < best_dist:
                    best_dist = dist
                    best_proj = (qx, qy)
                    best_heading = math.atan2(dy, dx)

            elif seg.seg_type == TrackSegmentType.ARC_CW:
                cx, cy = seg.center_pos
                R = seg.radius
                angle = math.atan2(py - cy, px - cx)

                a_diff = (angle - seg.start_angle) % (2.0 * math.pi)
                arc_span = (seg.end_angle - seg.start_angle) % (2.0 * math.pi)
                if arc_span == 0:
                    arc_span = 2.0 * math.pi

                t_clamped = max(0.0, min(1.0, a_diff / arc_span))
                clamped_angle = seg.start_angle + t_clamped * arc_span

                qx = cx + R * math.cos(clamped_angle)
                qy = cy + R * math.sin(clamped_angle)
                dist = math.hypot(px - qx, py - qy)

                if dist < best_dist:
                    best_dist = dist
                    best_proj = (qx, qy)
                    best_heading = clamped_angle + math.pi / 2.0

        return best_proj[0], best_proj[1], best_heading, best_dist

    def get_lookahead_point(
        self, pos: Tuple[float, float], lookahead_dist: float = 60.0
    ) -> Tuple[float, float, float]:
        """Returns target tracking waypoint (x, y, heading) along track ahead of vehicle."""
        proj_x, proj_y, heading, _ = self.get_closest_centerline_point(pos)
        target_x = proj_x + lookahead_dist * math.cos(heading)
        target_y = proj_y + lookahead_dist * math.sin(heading)
        tx, ty, th, _ = self.get_closest_centerline_point((target_x, target_y))
        return tx, ty, th


# =====================================================================
# 6. VEHICLE PHYSICS STATE (KINEMATIC BICYCLE MODEL)
# =====================================================================
class Vehicle:
    """
    Simulates the autonomous ground vehicle using a 2D Kinematic Bicycle Model.
    Accepts normalized steering commands [-1.0, 1.0] and throttle [0.0, 1.0].
    """
    def __init__(
        self,
        initial_pose: Tuple[float, float, float] = (
            VEHICLE_DOCK_CENTER[0],
            VEHICLE_DOCK_CENTER[1],
            VEHICLE_INITIAL_HEADING,
        ),
        wheelbase: float = VEHICLE_WHEELBASE_PX,
    ):
        self.x: float = initial_pose[0]
        self.y: float = initial_pose[1]
        self.heading: float = initial_pose[2]
        self.speed: float = 0.0
        self.steering_angle: float = 0.0

        self.wheelbase: float = wheelbase
        self.length: float = VEHICLE_LENGTH_PX
        self.width: float = VEHICLE_WIDTH_PX
        self.bed_offset: float = VEHICLE_BED_OFFSET_PX

        self.target_speed: float = 0.0
        self.target_steer: float = 0.0

        self.loaded_cube: Optional[Cube] = None
        self.target_color: Optional[str] = None
        self.driving_state: VehicleDrivingState = VehicleDrivingState.DOCKED
        self.estop_active: bool = False

    @property
    def pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.heading

    @property
    def cargo_bed_position(self) -> Tuple[float, float]:
        bx = self.x + self.bed_offset * math.cos(self.heading)
        by = self.y + self.bed_offset * math.sin(self.heading)
        return bx, by

    def set_controls(self, throttle: float, normalized_steer: float):
        if self.estop_active:
            self.target_speed = 0.0
            return

        throttle_clamped = max(0.0, min(1.0, throttle))
        self.target_speed = throttle_clamped * VEHICLE_MAX_SPEED_PX_S

        steer_clamped = max(-1.0, min(1.0, normalized_steer))
        self.target_steer = steer_clamped * VEHICLE_STEER_MAX_RAD

    def step(self, dt: float):
        if self.estop_active:
            self.speed = 0.0
            return

        # Slew rate steering integration
        steer_rate = 5.0
        delta_err = self.target_steer - self.steering_angle
        self.steering_angle += max(-steer_rate * dt, min(steer_rate * dt, delta_err))
        self.steering_angle = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, self.steering_angle))

        # Speed ramp
        if self.speed < self.target_speed:
            self.speed = min(self.target_speed, self.speed + VEHICLE_ACCEL_MAX * dt)
        elif self.speed > self.target_speed:
            self.speed = max(self.target_speed, self.speed - VEHICLE_DECEL_MAX * dt)

        # Kinematic bicycle equations
        self.x += self.speed * math.cos(self.heading) * dt
        self.y += self.speed * math.sin(self.heading) * dt
        self.heading += (self.speed / self.wheelbase) * math.tan(self.steering_angle) * dt
        self.heading = (self.heading + math.pi) % (2.0 * math.pi) - math.pi

        # Update carried cube position
        if self.loaded_cube:
            self.loaded_cube.update_carried((self.x, self.y, self.heading), offset=self.bed_offset)

    def load_cube(self, cube: Cube):
        self.loaded_cube = cube
        cube.is_loaded = True
        cube.is_picked = False
        cube.state = CubeState.ON_VEHICLE
        cube.carrier = self
        cube.update_carried((self.x, self.y, self.heading), offset=self.bed_offset)

    def unload_cube(self) -> Optional[Cube]:
        cube = self.loaded_cube
        if cube:
            cube.carrier = None
            cube.is_loaded = False
            cube.state = CubeState.DELIVERED
            self.loaded_cube = None
        return cube

    def trigger_estop(self):
        self.estop_active = True
        self.speed = 0.0
        self.target_speed = 0.0
        self.driving_state = VehicleDrivingState.ESTOP_FROZEN

    def release_estop(self):
        self.estop_active = False
        if self.driving_state == VehicleDrivingState.ESTOP_FROZEN:
            self.driving_state = VehicleDrivingState.LANE_FOLLOW

    def reset(self, pose: Tuple[float, float, float] = (VEHICLE_DOCK_CENTER[0], VEHICLE_DOCK_CENTER[1], VEHICLE_INITIAL_HEADING)):
        self.x, self.y, self.heading = pose
        self.speed = 0.0
        self.target_speed = 0.0
        self.steering_angle = 0.0
        self.target_steer = 0.0
        self.loaded_cube = None
        self.target_color = None
        self.driving_state = VehicleDrivingState.DOCKED
        self.estop_active = False


# =====================================================================
# 7. PARKING BAY ENTITY (Subclass of tuple for contract parity)
# =====================================================================
class ParkingBay(tuple):
    """
    Represents a ground color parking bay.
    Inherits from tuple (center_x, center_y, width, height) so it equals
    the contract specification tuple (e.g. (380, 625, 60, 40)) while exposing
    rich attributes like center, rect, color_type, rgb, and contains_point.
    """
    name: str
    color_type: CubeColor
    rect: Tuple[int, int, int, int]
    center: Tuple[float, float]
    rgb: Tuple[int, int, int]

    def __new__(
        cls,
        name: str,
        color_type: CubeColor,
        rect: Tuple[int, int, int, int],
        center: Tuple[float, float],
        rgb: Tuple[int, int, int],
        spec_tuple: Tuple[int, int, int, int],
    ):
        instance = super().__new__(cls, spec_tuple)
        instance.name = name
        instance.color_type = color_type
        instance.rect = rect
        instance.center = center
        instance.rgb = rgb
        return instance

    def contains_point(self, pos: Tuple[float, float]) -> bool:
        x, y = pos
        rx, ry, rw, rh = self.rect
        return (rx <= x <= rx + rw) and (ry <= y <= ry + rh)


# =====================================================================
# 8. FACTORY WORLD MASTER CLASS
# =====================================================================
class FactoryWorld:
    """
    Coordinates all continuous physical entities in the 2D arena:
    - ConveyorBelt & Infeed/Exit Optical Sensors
    - Track & Lane Centerline Geometry
    - Autonomous Vehicle & Kinematics
    - Robot Arm Pick/Place Workstation Stub
    - RGB Ground Color Parking Bays & Traffic Signs
    """
    def __init__(self):
        # Display and arena dimensions
        self.window_width: int = SCREEN_WIDTH
        self.window_height: int = SCREEN_HEIGHT
        self.arena_width: int = ARENA_WIDTH
        self.arena_height: int = ARENA_HEIGHT
        self.width: int = ARENA_WIDTH
        self.height: int = ARENA_HEIGHT

        # Timing and scaling
        self.time: float = 0.0
        self.is_paused: bool = False
        self.time_scale: float = 1.0

        # Subsystems
        self.conveyor = ConveyorBelt()
        self.track = Track()
        self.vehicle = Vehicle()
        self.dock_pose: Tuple[float, float, float] = (VEHICLE_DOCK_CENTER[0], VEHICLE_DOCK_CENTER[1], VEHICLE_INITIAL_HEADING)
        self.dock_sensor = ProximitySensor("S3_DOCK", SENSOR_S3_CENTER, SENSOR_S3_RADIUS)

        # Parking Bays matching (center_x, center_y, w, h)
        self.parking_bays: Dict[str, ParkingBay] = {
            "RED": ParkingBay("RED", CubeColor.RED, BAY_RED_RECT, BAY_RED_CENTER, COLOR_CUBE_RED, BAY_RED_TUPLE),
            "GREEN": ParkingBay("GREEN", CubeColor.GREEN, BAY_GREEN_RECT, BAY_GREEN_CENTER, COLOR_CUBE_GREEN, BAY_GREEN_TUPLE),
            "BLUE": ParkingBay("BLUE", CubeColor.BLUE, BAY_BLUE_RECT, BAY_BLUE_CENTER, COLOR_CUBE_BLUE, BAY_BLUE_TUPLE),
        }

        # Traffic Signs dictionary
        self.traffic_signs: Dict[str, Tuple[int, int, int, int]] = {
            "pedestrian": (SIGN_PEDESTRIAN_POS[0], SIGN_PEDESTRIAN_POS[1], SIGN_PEDESTRIAN_SIZE[0], SIGN_PEDESTRIAN_SIZE[1]),
            "parking": (SIGN_PARK_POS[0], SIGN_PARK_POS[1], SIGN_PARK_SIZE[0], SIGN_PARK_SIZE[1]),
        }

        # Closed-loop track waypoints
        self.track_waypoints: List[Tuple[float, float]] = list(TRACK_WAYPOINTS)

    def add_cube(self, color_name: str) -> Cube:
        """Convenience method to feed a cube onto the conveyor."""
        return self.conveyor.add_cube(color_name)

    def get_dock_sensor_reading(self) -> bool:
        """Evaluates whether vehicle is properly docked at the station."""
        return self.dock_sensor.evaluate((self.vehicle.x, self.vehicle.y))

    def step(self, dt: float):
        """Advances entire simulation universe by dt seconds."""
        if self.is_paused:
            return

        effective_dt = dt * self.time_scale
        self.time += effective_dt

        # Advance conveyor physics
        self.conveyor.update(effective_dt)

        # Advance vehicle kinematics
        self.vehicle.step(effective_dt)

        # Evaluate docking sensor
        self.dock_sensor.evaluate((self.vehicle.x, self.vehicle.y))

        # Check vehicle terminal parking arrival
        if (
            self.vehicle.driving_state == VehicleDrivingState.PARK_APPROACH
            and self.vehicle.target_color in self.parking_bays
        ):
            target_bay = self.parking_bays[self.vehicle.target_color]
            dist_to_bay = math.hypot(self.vehicle.x - target_bay.center[0], self.vehicle.y - target_bay.center[1])
            if dist_to_bay <= 25.0:
                self.vehicle.speed = 0.0
                self.vehicle.target_speed = 0.0
                self.vehicle.driving_state = VehicleDrivingState.PARKED_FINISHED
                self.vehicle.unload_cube()

    def apply_estop(self):
        """Immediately locks all actuators across the factory floor."""
        self.conveyor.is_running = False
        self.vehicle.trigger_estop()

    def reset_estop(self):
        """Releases actuator locks."""
        self.vehicle.release_estop()

    def reset(self):
        """Clears all entities and restores pristine starting configuration."""
        self.time = 0.0
        self.conveyor.reset()
        self.vehicle.reset()
        self.dock_sensor.evaluate((self.vehicle.x, self.vehicle.y))

    def get_camera_world_elements(self) -> Dict[str, Any]:
        """Provides world geometry elements formatted for perspective camera projection."""
        # Convert metric meters coordinates for camera perspective math
        scale = SCALE_METERS_PER_PX
        return {
            "parking_bays": {
                name: [
                    (bay.rect[0] * scale, bay.rect[1] * scale),
                    ((bay.rect[0] + bay.rect[2]) * scale, bay.rect[1] * scale),
                    ((bay.rect[0] + bay.rect[2]) * scale, (bay.rect[1] + bay.rect[3]) * scale),
                    (bay.rect[0] * scale, (bay.rect[1] + bay.rect[3]) * scale),
                ]
                for name, bay in self.parking_bays.items()
            },
            "signs": [
                {"id": 0, "name": "pedestrian", "x": SIGN_PEDESTRIAN_POS[0] * scale, "y": SIGN_PEDESTRIAN_POS[1] * scale, "z": 0.35},
                {"id": 5, "name": "parking", "x": SIGN_PARK_POS[0] * scale, "y": SIGN_PARK_POS[1] * scale, "z": 0.35},
            ]
        }
