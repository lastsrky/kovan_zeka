"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Centralized Configuration & Constants Module

Author: M1 Core Simulator Team
Module: simulator.config
"""

import math
from typing import Dict, List, Tuple
import numpy as np

# =====================================================================
# 1. DISPLAY & SIMULATION TIMING
# =====================================================================
SCREEN_WIDTH: int = 1600
SCREEN_HEIGHT: int = 900
ARENA_WIDTH: int = 1040
ARENA_HEIGHT: int = 900
HMI_WIDTH: int = 560
HMI_HEIGHT: int = 480

FPS: int = 60
PHYSICS_DT: float = 1.0 / FPS  # 16.667 ms
WINDOW_TITLE: str = "TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simülatörü"

# Metric scale: 1 pixel = 1 cm (0.01 m). 100 pixels = 1.0 meter.
SCALE_PX_PER_METER: float = 100.0
SCALE_METERS_PER_PX: float = 1.0 / SCALE_PX_PER_METER

# =====================================================================
# 2. COLOR PALETTE (RGB TUPLES)
# =====================================================================
# Floor & Environment
COLOR_FLOOR: Tuple[int, int, int] = (240, 242, 245)
COLOR_FLOOR_GRID: Tuple[int, int, int] = (225, 228, 233)
COLOR_WALL_BORDER: Tuple[int, int, int] = (160, 165, 175)

# Conveyor Belt
COLOR_CONVEYOR_FRAME: Tuple[int, int, int] = (70, 74, 82)
COLOR_CONVEYOR_BELT: Tuple[int, int, int] = (40, 44, 52)
COLOR_CONVEYOR_ROLLER: Tuple[int, int, int] = (120, 125, 135)
COLOR_CONVEYOR_ARROW: Tuple[int, int, int] = (80, 85, 95)

# Workpieces / Cubes (Exact RGB matching calibrated HSV)
COLOR_CUBE_RED: Tuple[int, int, int] = (220, 20, 25)
COLOR_CUBE_GREEN: Tuple[int, int, int] = (20, 210, 30)
COLOR_CUBE_BLUE: Tuple[int, int, int] = (25, 35, 220)
COLOR_CUBE_BORDER: Tuple[int, int, int] = (15, 15, 15)

# Parking Bays
COLOR_BAY_RED: Tuple[int, int, int] = (255, 30, 39)
COLOR_BAY_GREEN: Tuple[int, int, int] = (30, 199, 64)
COLOR_BAY_BLUE: Tuple[int, int, int] = (30, 100, 255)
COLOR_BAY_BORDER: Tuple[int, int, int] = (255, 255, 255)
COLOR_BAY_LABEL: Tuple[int, int, int] = (240, 240, 240)

# Track & Roadway
COLOR_ROAD_ASPHALT: Tuple[int, int, int] = (50, 52, 58)
COLOR_ROAD_OUTER_LINE: Tuple[int, int, int] = (255, 255, 255)
COLOR_ROAD_CENTER_LINE: Tuple[int, int, int] = (245, 215, 30)  # Dashed yellow
COLOR_ZEBRA_STRIPES: Tuple[int, int, int] = (250, 250, 250)

# Vehicle
COLOR_VEHICLE_BODY: Tuple[int, int, int] = (45, 95, 195)
COLOR_VEHICLE_ROOF: Tuple[int, int, int] = (30, 70, 150)
COLOR_VEHICLE_WHEEL: Tuple[int, int, int] = (20, 20, 20)
COLOR_VEHICLE_BED: Tuple[int, int, int] = (190, 195, 205)
COLOR_VEHICLE_HEADLIGHT: Tuple[int, int, int] = (255, 255, 210)

# Robot Arm
COLOR_ARM_BASE: Tuple[int, int, int] = (65, 68, 75)
COLOR_ARM_LINK_1: Tuple[int, int, int] = (235, 130, 20)  # Industrial orange
COLOR_ARM_LINK_2: Tuple[int, int, int] = (245, 150, 30)
COLOR_ARM_GRIPPER: Tuple[int, int, int] = (90, 95, 105)

# Optical Sensors & Beams
COLOR_SENSOR_HOUSING: Tuple[int, int, int] = (35, 38, 45)
COLOR_SENSOR_BEAM_OFF: Tuple[int, int, int] = (70, 75, 85)
COLOR_SENSOR_BEAM_ON: Tuple[int, int, int] = (255, 60, 20)  # Active IR beam

# PLC Signal Tower (Stack Lamp)
COLOR_TOWER_RED_OFF: Tuple[int, int, int] = (80, 20, 20)
COLOR_TOWER_RED_ON: Tuple[int, int, int] = (255, 30, 30)
COLOR_TOWER_AMBER_OFF: Tuple[int, int, int] = (80, 60, 15)
COLOR_TOWER_AMBER_ON: Tuple[int, int, int] = (255, 190, 20)
COLOR_TOWER_GREEN_OFF: Tuple[int, int, int] = (15, 60, 20)
COLOR_TOWER_GREEN_ON: Tuple[int, int, int] = (30, 240, 50)

# =====================================================================
# 3. FACTORY CELL & ARENA COORDINATES
# =====================================================================
# Conveyor Belt: (x, y, w, h)
CONVEYOR_RECT: Tuple[int, int, int, int] = (120, 100, 260, 60)
CONVEYOR_X: int = CONVEYOR_RECT[0]
CONVEYOR_Y: int = CONVEYOR_RECT[1]
CONVEYOR_WIDTH: int = CONVEYOR_RECT[2]
CONVEYOR_HEIGHT: int = CONVEYOR_RECT[3]
CONVEYOR_BELT_SPEED_NOMINAL: float = 20.0  # px/s
CONVEYOR_PHYSICAL_LENGTH_MM: float = 800.0
CONVEYOR_SPEED_MM_S: float = 80.0

# Sensors
# S1 (Infeed): x=140, y=100..160
SENSOR_S1_X: int = 140
SENSOR_S1_Y: int = 100
SENSOR_S1_HEIGHT: int = 60
SENSOR_S1_BEAM_P1: Tuple[int, int] = (SENSOR_S1_X, SENSOR_S1_Y)
SENSOR_S1_BEAM_P2: Tuple[int, int] = (SENSOR_S1_X, SENSOR_S1_Y + SENSOR_S1_HEIGHT)

# S2 (Discharge / Exit): x=360, y=100..160
SENSOR_S2_X: int = 360
SENSOR_S2_Y: int = 100
SENSOR_S2_HEIGHT: int = 60
SENSOR_S2_BEAM_P1: Tuple[int, int] = (SENSOR_S2_X, SENSOR_S2_Y)
SENSOR_S2_BEAM_P2: Tuple[int, int] = (SENSOR_S2_X, SENSOR_S2_Y + SENSOR_S2_HEIGHT)

# Robot Arm Workstation
ROBOT_BASE_POS: Tuple[int, int] = (380, 200)
ROBOT_CELL_RECT: Tuple[int, int, int, int] = (340, 160, 80, 80)
ROBOT_PICK_COORDINATE: Tuple[int, int] = (360, 130)  # Cube center at exit
ROBOT_PLACE_COORDINATE: Tuple[int, int] = (380, 270)  # Vehicle bed center

# Vehicle Loading Dock
VEHICLE_DOCK_RECT: Tuple[int, int, int, int] = (345, 247, 70, 45)
VEHICLE_DOCK_CENTER: Tuple[float, float] = (380.0, 270.0)
VEHICLE_INITIAL_HEADING: float = 0.0  # Radians (0.0 = East, along +X)

# Optical / Proximity Sensor S3 (Vehicle Present at Dock)
SENSOR_S3_CENTER: Tuple[float, float] = (380.0, 270.0)
SENSOR_S3_RADIUS: float = 20.0

# Stack Signal Tower
SIGNAL_TOWER_RECT: Tuple[int, int, int, int] = (380, 40, 30, 80)

# =====================================================================
# 4. TRACK & ROADWAY GEOMETRY
# =====================================================================
ROAD_WIDTH: float = 90.0
LANE_WIDTH: float = ROAD_WIDTH / 2.0  # 45.0 px

# Track Circuit Waypoints and Arcs
# Straight 1 (North): From Dock (380, 270) to East Turn Entrance (850, 270)
TRACK_STRAIGHT_1_START: Tuple[float, float] = (380.0, 270.0)
TRACK_STRAIGHT_1_END: Tuple[float, float] = (850.0, 270.0)

# East Curve: Semicircle around (850, 420) with R=150
EAST_CURVE_CENTER: Tuple[float, float] = (850.0, 420.0)
EAST_CURVE_RADIUS: float = 150.0

# Straight 2 (South): From East Turn Exit (850, 570) to West Turn Entrance (250, 570)
TRACK_STRAIGHT_2_START: Tuple[float, float] = (850.0, 570.0)
TRACK_STRAIGHT_2_END: Tuple[float, float] = (250.0, 570.0)

# West Curve: Semicircle around (250, 420) with R=150
WEST_CURVE_CENTER: Tuple[float, float] = (250.0, 420.0)
WEST_CURVE_RADIUS: float = 150.0

# Straight 3 (Dock Approach): From West Turn Exit (250, 270) to Dock (380, 270)
TRACK_STRAIGHT_3_START: Tuple[float, float] = (250.0, 270.0)
TRACK_STRAIGHT_3_END: Tuple[float, float] = (380.0, 270.0)

# Total Circuit Arc Length (px)
TRACK_TOTAL_LENGTH: float = (
    (850.0 - 380.0)
    + (math.pi * 150.0)
    + (850.0 - 250.0)
    + (math.pi * 150.0)
    + (380.0 - 250.0)
)

# Standard waypoints list (closed loop starting and ending at Dock)
TRACK_WAYPOINTS: List[Tuple[float, float]] = [
    (380.0, 270.0),  # Dock
    (850.0, 270.0),  # End of Straight 1
    (850.0, 570.0),  # End of East Curve
    (520.0, 570.0),  # Approaching parking
    (250.0, 570.0),  # End of Straight 2
    (250.0, 270.0),  # End of West Curve
    (380.0, 270.0),  # Loop close
]

# Pedestrian Crossing & Sign (ID 0)
SIGN_PEDESTRIAN_POS: Tuple[int, int] = (875, 420)
SIGN_PEDESTRIAN_SIZE: Tuple[int, int] = (30, 30)
ZEBRA_CROSSING_RECT: Tuple[int, int, int, int] = (805, 400, 90, 40)

# Parking Sign (ID 5)
SIGN_PARK_POS: Tuple[int, int] = (520, 600)
SIGN_PARK_SIZE: Tuple[int, int] = (30, 30)

# Parking Bays: Red, Green, Blue
BAY_WIDTH: int = 60
BAY_HEIGHT: int = 40
BAY_Y_CENTER: int = 625

BAY_RED_CENTER: Tuple[int, int] = (380, BAY_Y_CENTER)
BAY_GREEN_CENTER: Tuple[int, int] = (300, BAY_Y_CENTER)
BAY_BLUE_CENTER: Tuple[int, int] = (220, BAY_Y_CENTER)

BAY_RED_RECT: Tuple[int, int, int, int] = (
    BAY_RED_CENTER[0] - BAY_WIDTH // 2,
    BAY_RED_CENTER[1] - BAY_HEIGHT // 2,
    BAY_WIDTH,
    BAY_HEIGHT,
)
BAY_GREEN_RECT: Tuple[int, int, int, int] = (
    BAY_GREEN_CENTER[0] - BAY_WIDTH // 2,
    BAY_GREEN_CENTER[1] - BAY_HEIGHT // 2,
    BAY_WIDTH,
    BAY_HEIGHT,
)
BAY_BLUE_RECT: Tuple[int, int, int, int] = (
    BAY_BLUE_CENTER[0] - BAY_WIDTH // 2,
    BAY_BLUE_CENTER[1] - BAY_HEIGHT // 2,
    BAY_WIDTH,
    BAY_HEIGHT,
)

# Canonical 4-tuples (center_x, center_y, width, height) matching contract expectations
BAY_RED_TUPLE: Tuple[int, int, int, int] = (380, 625, 60, 40)
BAY_GREEN_TUPLE: Tuple[int, int, int, int] = (300, 625, 60, 40)
BAY_BLUE_TUPLE: Tuple[int, int, int, int] = (220, 625, 60, 40)

# =====================================================================
# 5. CUBE & VEHICLE PHYSICAL DIMENSIONS
# =====================================================================
CUBE_SIZE_PX: float = 20.0  # 20 cm x 20 cm representation
CUBE_SIZE_MM: float = 40.0  # 40 mm physical dimension

VEHICLE_LENGTH_PX: float = 50.0
VEHICLE_WIDTH_PX: float = 28.0
VEHICLE_WHEELBASE_PX: float = 35.0
VEHICLE_BED_OFFSET_PX: float = -12.0  # Rear cargo bed relative to vehicle center

# Vehicle Kinematics
VEHICLE_SERVO_CENTER_DEG: float = 110.0
VEHICLE_SERVO_MAX_DELTA_DEG: float = 35.0
VEHICLE_STEER_MIN_RAD: float = math.radians(-35.0)
VEHICLE_STEER_MAX_RAD: float = math.radians(35.0)

VEHICLE_MAX_SPEED_PX_S: float = 80.0  # ~0.8 m/s
VEHICLE_START_SPEED_PX_S: float = 36.0  # Nominal throttle 0.30 -> 36 px/s
VEHICLE_PARK_SPEED_PX_S: float = 24.0   # Nominal park throttle 0.267 -> 24 px/s
VEHICLE_ACCEL_MAX: float = 30.0         # px/s^2
VEHICLE_DECEL_MAX: float = 60.0         # px/s^2

# =====================================================================
# 6. CALIBRATED HSV COLOR DETECTION INTERVALS
# =====================================================================
# Robot Arm Overhead Camera HSV Ranges (from renk_kalibrasyon.json)
ARM_HSV_RANGES: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {
    "RED": [
        (np.array([168, 140, 111], dtype=np.uint8), np.array([179, 255, 255], dtype=np.uint8)),
        (np.array([0, 140, 111], dtype=np.uint8), np.array([8, 255, 255], dtype=np.uint8)),
    ],
    "GREEN": [
        (np.array([73, 230, 101], dtype=np.uint8), np.array([93, 255, 255], dtype=np.uint8)),
    ],
    "BLUE": [
        (np.array([90, 230, 150], dtype=np.uint8), np.array([110, 255, 255], dtype=np.uint8)),
    ],
}

ARM_DETECTION_DOLULUK_ESIGI: float = 0.40
ARM_DETECTION_MARJ: float = 0.12
ARM_CAMERA_ROI: Tuple[int, int, int, int] = (215, 120, 251, 240)

# Vehicle RealSense D455 Parking Bay Ground HSV Ranges (from park_zemin_renk.py)
VEHICLE_PARK_HSV_RANGES: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {
    "RED": [
        (np.array([0, 50, 50], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)),
        (np.array([170, 50, 50], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8)),
    ],
    "GREEN": [
        (np.array([35, 40, 40], dtype=np.uint8), np.array([85, 255, 255], dtype=np.uint8)),
    ],
    "BLUE": [
        (np.array([100, 40, 40], dtype=np.uint8), np.array([135, 255, 255], dtype=np.uint8)),
    ],
}

VEHICLE_PARK_DUR_MESAFE_CM: float = 25.0
VEHICLE_PARK_ZEMIN_MIN_CM: float = 25.0
VEHICLE_PARK_ZEMIN_MAX_CM: float = 350.0
VEHICLE_PARK_RED_AREA_MIN: int = 300
VEHICLE_PARK_K_GAIN: float = 0.125

# =====================================================================
# 7. VIRTUAL CAMERAS PARAMETERS
# =====================================================================
CAMERA_FRAME_WIDTH: int = 640
CAMERA_FRAME_HEIGHT: int = 480
CAMERA_FPS: int = 30

# D455 Camera Intrinsics / FOV
VEHICLE_CAM_FOV_H: float = 86.0  # Horizontal FOV (degrees)
VEHICLE_CAM_FOV_V: float = 57.0  # Vertical FOV (degrees)
VEHICLE_CAM_CROP_TOP_RATIO: float = 0.2917  # Crops top 140 px for lane tracking
VEHICLE_CAM_MAX_DEPTH_MM: int = 5000

# =====================================================================
# 8. S7-1200 PLC MEMORY ADDRESSES & TIMINGS
# =====================================================================
# Inputs (%I)
PLC_ADDR_START_PB: str = "%I0.0"
PLC_ADDR_STOP_PB: str = "%I0.1"
PLC_ADDR_ESTOP_PB: str = "%I0.2"
PLC_ADDR_RESET_PB: str = "%I0.3"
PLC_ADDR_ENTRY_SENSOR: str = "%I0.4"
PLC_ADDR_EXIT_SENSOR: str = "%I0.5"
PLC_ADDR_VEHICLE_READY: str = "%I0.6"

# Outputs (%Q)
PLC_ADDR_CONVEYOR_MOTOR: str = "%Q0.0"
PLC_ADDR_GREEN_LAMP: str = "%Q0.1"
PLC_ADDR_RED_LAMP: str = "%Q0.2"
PLC_ADDR_YELLOW_LAMP: str = "%Q0.3"
PLC_ADDR_ROBOT_TRIGGER: str = "%Q0.4"
PLC_ADDR_CYCLE_ACTIVE: str = "%Q0.5"

PLC_CYCLE_TIME_MS: float = 16.67  # 60 Hz cyclic scan

# =====================================================================
# 9. MQTT PROTOCOL TOPICS & ENDPOINTS
# =====================================================================
MQTT_BROKER_HOST: str = "127.0.0.1"
MQTT_BROKER_PORT: int = 1883
MQTT_CLIENT_ID_SIM: str = "tekno-sim-bridge"

TOPIC_ARAC_YUK: str = "arac/yuk"
TOPIC_ROBOT_VERI: str = "robot/veri"
TOPIC_ROBOT_BASLA: str = "robot/basla"
TOPIC_ROBOT_DURUM: str = "robot/durum"
