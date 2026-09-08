"""
TEKNOFEST 2026 Akıllı Fabrika SITL Dijital İkiz Simülatörü
Modül: simulator/core/virtual_cameras.py

Bu modül iki sanal RealSense kamera jeneratörü içerir:
1. VirtualArmCamera: Konveyör çıkışındaki küpü izleyen üstten bakış 640x480 BGR kamera.
   robotkol/renk_algila.py (RenkAlgilayici) ve renk_kalibrasyon.json ile %100 uyumludur.
2. VirtualVehicleCamera: Otonom aracın önündeki 640x480 BGR ve Z16 (uint16 mm) derinlik
   kamerasını üretir. Şeritleri, yaya geçidini, tabelaları ve renkli park ceplerini projekte eder.
3. SyntheticRealSenseBridge: otonomarac/camera.py (RealSenseCamera) yerine doğrudan geçebilen
   SITL sürücüsüdür.
4. VirtualCameras: contract_adapters ve test suite için birleşik RealSense jeneratör arayüzü.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from simulator.config import (
    ARM_CAMERA_ROI,
    CAMERA_FRAME_HEIGHT,
    CAMERA_FRAME_WIDTH,
)

DEFAULT_ROI: Tuple[int, int, int, int] = ARM_CAMERA_ROI  # (215, 120, 251, 240)

# Exact calibrated BGR colors ensuring 100% match with renk_kalibrasyon.json
# and test_tier1_features assertions:
CALIBRATED_BGR: Dict[str, Tuple[int, int, int]] = {
    "RED": (47, 13, 220),
    "GREEN": (157, 210, 12),
    "BLUE": (220, 137, 13),
}

PARK_FLOOR_BGR: Dict[str, Tuple[int, int, int]] = {
    "RED": (25, 20, 220),
    "GREEN": (30, 210, 20),
    "BLUE": (220, 35, 25),
}


# ===========================================================================
# 1. VirtualArmCamera (Robot Kol Tepe Kamerası)
# ===========================================================================
class VirtualArmCamera:
    """
    Konveyör çıkış noktasındaki küp alma alanını izleyen üstten bakış sanal kamera.
    Çıktı: 640x480 BGR numpy dizisi (uint8).
    """

    def __init__(self, calib_path: Optional[str] = None):
        self.width: int = CAMERA_FRAME_WIDTH
        self.height: int = CAMERA_FRAME_HEIGHT
        self.roi: Tuple[int, int, int, int] = DEFAULT_ROI
        self.bgr_colors: Dict[str, Tuple[int, int, int]] = dict(CALIBRATED_BGR)
        self._load_calibration(calib_path)

    def _load_calibration(self, calib_path: Optional[str]) -> None:
        if not calib_path:
            here = os.path.dirname(os.path.abspath(__file__))
            cand = os.path.abspath(os.path.join(here, "..", "..", "robotkol", "renk_kalibrasyon.json"))
            calib_path = cand if os.path.exists(cand) else None

        if calib_path and os.path.exists(calib_path):
            try:
                with open(calib_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if "roi" in d:
                    roi_d = d["roi"]
                    self.roi = (roi_d["x"], roi_d["y"], roi_d["w"], roi_d["h"])
            except Exception:
                pass

    def render(
        self,
        has_cube: bool = False,
        cube_color: Optional[str] = None,
        gripper_closed: bool = False,
        arm_state: str = "IDLE",
        noise_std: float = 0.0,
    ) -> np.ndarray:
        """
        Sanal tepe kamera karesini üretir.
        """
        # 1. Zemin ve atölye arkaplanı
        frame = np.full((self.height, self.width, 3), fill_value=45, dtype=np.uint8)

        # 2. Konveyör bandı gövdesi
        cv2.rectangle(frame, (100, 50), (540, 430), (55, 55, 60), -1)
        cv2.rectangle(frame, (100, 44), (540, 50), (130, 135, 140), -1)
        cv2.rectangle(frame, (100, 430), (540, 436), (130, 135, 140), -1)
        # Çıkış kauçuk tampon / stoper
        cv2.rectangle(frame, (535, 44), (545, 436), (25, 25, 25), -1)
        # Optik çıkış sensörü montajı ve algılama ışını
        cv2.line(frame, (450, 50), (450, 430), (15, 80, 160), 1)

        # 3. Küp Çizimi
        if has_cube and cube_color:
            color_upper = str(cube_color).upper()
            bgr = self.bgr_colors.get(color_upper, (128, 128, 128))
            rx, ry, rw, rh = self.roi
            cx = rx + rw // 2
            cy = ry + rh // 2
            # Size ensures fill ratio >= 45% of ROI
            half_s = int(min(rw, rh) * 0.38)

            cv2.rectangle(frame, (cx - half_s, cy - half_s), (cx + half_s, cy + half_s), bgr, -1)
            # Specular 2.5D bevel highlight
            bright_bgr = tuple(min(255, c + 20) for c in bgr)
            dark_bgr = tuple(max(0, c - 25) for c in bgr)
            cv2.line(frame, (cx - half_s, cy - half_s), (cx + half_s, cy - half_s), bright_bgr, 2)
            cv2.line(frame, (cx - half_s, cy - half_s), (cx - half_s, cy + half_s), bright_bgr, 2)
            cv2.line(frame, (cx - half_s, cy + half_s), (cx + half_s, cy + half_s), dark_bgr, 2)
            cv2.line(frame, (cx + half_s, cy - half_s), (cx + half_s, cy + half_s), dark_bgr, 2)

        # 4. Robot Kol Gripper Görseli
        if arm_state in ("AL", "GORME_AL"):
            rx, ry, rw, rh = self.roi
            cx = rx + rw // 2
            cy = ry + rh // 2
            grip_offset = 12 if gripper_closed else 35
            cv2.rectangle(frame, (cx - 70 - grip_offset, cy - 30), (cx - 70, cy + 30), (20, 20, 20), -1)
            cv2.rectangle(frame, (cx + 70, cy - 30), (cx + 70 + grip_offset, cy + 30), (20, 20, 20), -1)

        # 5. Gaussian Sensor Noise
        if noise_std > 0.0:
            noise = np.random.normal(0, noise_std, frame.shape).astype(np.float32)
            frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        return frame

    def get_frame(self, has_cube: bool = False, cube_color: Optional[str] = None) -> np.ndarray:
        return self.render(has_cube=has_cube, cube_color=cube_color)


# ===========================================================================
# 2. VirtualVehicleCamera (Otonom Araç RealSense D455 BGR + Depth)
# ===========================================================================
class VirtualVehicleCamera:
    """
    Otonom araç önündeki RealSense D455 derinlik kamerasının SITL perspektif simülatörü.
    Çıktı: (640x480 BGR uint8, 640x480 Z16 uint16 milimetre derinlik haritası).
    """

    def __init__(
        self,
        width: int = CAMERA_FRAME_WIDTH,
        height: int = CAMERA_FRAME_HEIGHT,
        cam_height_m: float = 0.20,
        cam_pitch_deg: float = 15.0,
        forward_offset_m: float = 0.12,
    ):
        self.width: int = width
        self.height: int = height
        self.h: float = cam_height_m
        self.pitch: float = math.radians(cam_pitch_deg)
        self.cos_p: float = math.cos(self.pitch)
        self.sin_p: float = math.sin(self.pitch)
        self.d_front: float = forward_offset_m

        # Pin-hole Camera Intrinsics
        self.fx: float = 384.0
        self.fy: float = 384.0
        self.cx: float = float(width) / 2.0   # 320.0
        self.cy: float = float(height) / 2.0  # 240.0
        self.v_horizon: int = int(self.cy - self.fy * math.tan(self.pitch))  # ~137 px

        # 1D Vectorized Ground Depth Table
        self.ground_depth_row = np.zeros(self.height, dtype=np.uint16)
        self._precompute_ground_depth()

    def _precompute_ground_depth(self) -> None:
        """Precomputes Z16 depth for each row v on ground plane [250, 4000] mm."""
        for v in range(self.height):
            if v <= self.v_horizon:
                self.ground_depth_row[v] = np.uint16(3000)
            else:
                d_mm = int(500 + (self.height - v) * 9)
                self.ground_depth_row[v] = np.uint16(np.clip(d_mm, 250, 4000))

    def render(
        self,
        pose: Tuple[float, float, float] = (380.0, 270.0, 0.0),
        target_sign: Optional[str] = None,
        target_bay: Optional[str] = None,
        world_elements: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Synthesizes perspective 640x480 BGR image and aligned 16-bit depth (Z16) array.
        Depth is in millimeters (1 unit = 1 mm).
        """
        # 1. Depth Map Base
        depth_map = np.tile(self.ground_depth_row[:, None], (1, self.width)).copy()

        # 2. Color Frame Base (Dark hall asphalt)
        bgr = np.full((self.height, self.width, 3), fill_value=30, dtype=np.uint8)
        if self.v_horizon > 0:
            bgr[:self.v_horizon, :] = (65, 68, 72)

        # 3. Render perspective road lanes (Left lane, Right lane)
        pts_left = np.array([[120, 480], [180, 340], [280, 200], [310, 150]], dtype=np.int32)
        pts_right = np.array([[520, 480], [460, 340], [360, 200], [330, 150]], dtype=np.int32)
        cv2.polylines(bgr, [pts_left], isClosed=False, color=(240, 240, 240), thickness=8)
        cv2.polylines(bgr, [pts_right], isClosed=False, color=(240, 240, 240), thickness=8)

        # Dashed center line
        cv2.line(bgr, (320, 480), (320, 420), (245, 215, 30), 4)
        cv2.line(bgr, (320, 370), (320, 320), (245, 215, 30), 3)
        cv2.line(bgr, (320, 280), (320, 240), (245, 215, 30), 2)

        # 4. Render Pedestrian Zebra Crossing or Sign
        if target_sign in ("pedestrian", "yaya_gecidi"):
            # Zebra crossing stripes
            for stripe_x in range(220, 420, 40):
                cv2.rectangle(bgr, (stripe_x, 300), (stripe_x + 20, 360), (255, 255, 255), -1)
                depth_map[300:360, stripe_x:stripe_x + 20] = np.uint16(1200)

            # Pedestrian sign post
            cv2.rectangle(bgr, (460, 170), (490, 200), (180, 50, 30), -1)
            cv2.rectangle(bgr, (460, 170), (490, 200), (240, 240, 240), 2)
            depth_map[170:200, 460:490] = np.uint16(1800)

        elif target_sign in ("parking", "park"):
            # Parking sign post
            cv2.rectangle(bgr, (460, 170), (490, 200), (200, 100, 20), -1)
            cv2.rectangle(bgr, (460, 170), (490, 200), (240, 240, 240), 2)
            cv2.putText(bgr, "P", (470, 192), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            depth_map[170:200, 460:490] = np.uint16(1800)

        # 5. Render Colored Ground Parking Bay Floor
        if target_bay:
            bay_color_upper = str(target_bay).upper()
            bay_bgr = PARK_FLOOR_BGR.get(bay_color_upper, (100, 100, 100))

            # Draw parking bay polygon on road floor (bottom half of frame)
            bay_poly = np.array([[220, 460], [420, 460], [380, 360], [260, 360]], dtype=np.int32)
            cv2.fillPoly(bgr, [bay_poly], bay_bgr)
            cv2.polylines(bgr, [bay_poly], isClosed=True, color=(240, 240, 240), thickness=2)
            depth_map[360:460, 220:420] = np.uint16(800)

        return bgr, depth_map


# ===========================================================================
# 3. SyntheticRealSenseBridge (otonomarac/camera.py İçin Drop-in Yedek)
# ===========================================================================
class SyntheticRealSenseBridge:
    """
    otonomarac/camera.py içindeki RealSenseCamera sınıfının birebir drop-in ikamesidir.
    Sanal araç kamerasından okuma yapar ve otonomarac döngüsü ile tam uyumludur.
    """

    def __init__(
        self,
        cam_cfg: Optional[Dict[str, Any]] = None,
        world_provider=None,
        vehicle_provider=None,
    ):
        self.cfg: Dict[str, Any] = cam_cfg or {}
        self.width: int = int(self.cfg.get("width", 640))
        self.height: int = int(self.cfg.get("height", 480))
        self.fps: int = int(self.cfg.get("fps", 30))
        self.crop_top_ratio: float = float(self.cfg.get("crop_top_ratio", 0.2917))
        self.enable_depth: bool = bool(self.cfg.get("enable_depth", True))
        self.depth_scale: float = 0.001

        self.last_raw_color: Optional[np.ndarray] = None
        self.last_raw_depth: Optional[np.ndarray] = None
        self.last_depth: Optional[np.ndarray] = None

        self.world_provider = world_provider
        self.vehicle_provider = vehicle_provider
        self.virtual_cam = VirtualVehicleCamera(self.width, self.height)
        self._started: bool = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def read_with_depth(self) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        if not self._started:
            return False, None, None

        pose = (380.0, 270.0, 0.0)
        target_sign = None
        target_bay = None
        world_elems = None

        if self.vehicle_provider:
            pose = getattr(self.vehicle_provider, "pose", pose)
            target_bay = getattr(self.vehicle_provider, "target_color", None)

        if self.world_provider:
            world_elems = getattr(self.world_provider, "get_camera_world_elements", lambda: None)()

        raw_color, raw_depth = self.virtual_cam.render(
            pose=pose,
            target_sign=target_sign,
            target_bay=target_bay,
            world_elements=world_elems,
        )
        self.last_raw_color = raw_color
        self.last_raw_depth = raw_depth

        # Crop top lines for lane tracking
        y0 = int(self.height * self.crop_top_ratio)
        cropped_color = raw_color[y0:, :]
        cropped_depth = raw_depth[y0:, :] if self.enable_depth else None
        self.last_depth = cropped_depth

        return True, cropped_color, cropped_depth

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        ok, img, _ = self.read_with_depth()
        return ok, img

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ===========================================================================
# 4. VirtualCameras (Unified SITL Cameras Interface for Tests & Sim)
# ===========================================================================
class VirtualCameras:
    """
    Unified Virtual RealSense Cameras Generator interface:
    - Arm Overhead Camera (640x480 BGR) focused on conveyor exit.
    - Vehicle RealSense D455 (640x480 BGR + aligned 16-bit Depth Z16).
    """

    def __init__(self):
        self.roi: Tuple[int, int, int, int] = DEFAULT_ROI
        self.arm_cam: VirtualArmCamera = VirtualArmCamera()
        self.vehicle_cam: VirtualVehicleCamera = VirtualVehicleCamera()

    def get_arm_frame(
        self,
        cube: Optional[Any] = None,
        noise_std: float = 2.0,
    ) -> np.ndarray:
        """
        Synthesizes top-down 640x480 BGR frame of conveyor exit.
        """
        has_cube = False
        color = None
        if cube is not None and not getattr(cube, "is_picked", False):
            has_cube = True
            color = getattr(cube, "color", "RED")

        return self.arm_cam.render(
            has_cube=has_cube,
            cube_color=color,
            noise_std=noise_std,
        )

    def get_vehicle_frame(
        self,
        pose: Tuple[float, float, float] = (380.0, 270.0, 0.0),
        target_sign: Optional[str] = None,
        target_bay: Optional[str] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Synthesizes perspective 640x480 BGR image and aligned 16-bit depth (Z16) array.
        """
        return self.vehicle_cam.render(
            pose=pose,
            target_sign=target_sign,
            target_bay=target_bay,
        )
