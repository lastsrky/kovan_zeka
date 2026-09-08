"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Adversarial Stress Testing Suite for Virtual Cameras & Pygame Renderer

Author: teamwork_preview_challenger_m1_2_rep
Module: simulator.tests.test_adversarial_cameras_rendering
"""

import json
import math
import os
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pygame

from simulator.config import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    ARM_CAMERA_ROI,
    CAMERA_FRAME_HEIGHT,
    CAMERA_FRAME_WIDTH,
)
from simulator.core.factory_world import Cube, CubeColor, CubeState, FactoryWorld
from simulator.core.virtual_cameras import (
    CALIBRATED_BGR,
    DEFAULT_ROI,
    PARK_FLOOR_BGR,
    SyntheticRealSenseBridge,
    VirtualArmCamera,
    VirtualCameras,
    VirtualVehicleCamera,
)
from simulator.gui.camera_view import (
    CAMERA_VIEW_HEIGHT,
    CAMERA_VIEW_WIDTH,
    CameraHUDView,
    bgr_to_pygame_surface,
    create_no_signal_surface,
)
from simulator.gui.renderer import ArenaRenderer


class TestVirtualArmCameraAdversarial(unittest.TestCase):
    """Adversarial challenge tests for VirtualArmCamera and overhead inspection."""

    def setUp(self):
        self.cam = VirtualArmCamera()

    def test_roi_boundary_clipping_and_out_of_bounds(self):
        """Verify camera rendering handles ROIs at boundary, negative, and offscreen."""
        test_rois = [
            (0, 0, 100, 100),              # Top-left corner
            (590, 430, 100, 100),          # Partially out of frame bottom-right
            (-50, -50, 100, 100),          # Partially out of frame top-left
            (1000, 1000, 100, 100),        # Completely offscreen
            (0, 0, 0, 0),                  # Degenerate zero-size ROI
            (-100, 200, 50, 50),           # Off left edge
            (200, -100, 50, 50),           # Off top edge
            (0, 0, 640, 480),              # Full-frame ROI
        ]

        for roi in test_rois:
            self.cam.roi = roi
            frame = self.cam.render(has_cube=True, cube_color="RED", gripper_closed=True, arm_state="AL")
            self.assertEqual(frame.shape, (480, 640, 3), f"Shape mismatch for ROI {roi}")
            self.assertEqual(frame.dtype, np.uint8, f"Dtype mismatch for ROI {roi}")
            self.assertTrue(np.all(frame >= 0) and np.all(frame <= 255))

    def test_cube_states_and_empty_belt(self):
        """Verify rendering empty belt, None color, unknown colors, and numeric inputs."""
        # 1. Empty belt
        frame_empty = self.cam.render(has_cube=False)
        self.assertEqual(frame_empty.shape, (480, 640, 3))
        self.assertEqual(frame_empty.dtype, np.uint8)

        # 2. Cube present but color is None or empty string
        frame_none_color = self.cam.render(has_cube=True, cube_color=None)
        self.assertEqual(frame_none_color.shape, (480, 640, 3))

        frame_empty_str = self.cam.render(has_cube=True, cube_color="")
        self.assertEqual(frame_empty_str.shape, (480, 640, 3))

        # 3. Non-standard color strings
        colors = ["red", "green", "blue", "RED ", " blue", "UNKNOWN", "YELLOW", "CYAN", 999]
        for c in colors:
            frame = self.cam.render(has_cube=True, cube_color=c)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)

    def test_sensor_noise_extremes(self):
        """Verify sensor noise does not cause overflow, underflow, or non-uint8 arrays."""
        noise_levels = [0.0, 0.1, 5.0, 25.0, 100.0, 300.0, -10.0]
        for n in noise_levels:
            frame = self.cam.render(has_cube=True, cube_color="RED", noise_std=n)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertGreaterEqual(int(np.min(frame)), 0)
            self.assertLessEqual(int(np.max(frame)), 255)

    def test_calibration_file_resilience(self):
        """Verify camera initialization survives corrupt or missing calibration JSON."""
        # Non-existent file
        cam_missing = VirtualArmCamera(calib_path="non_existent_dir/no_file.json")
        self.assertEqual(cam_missing.roi, DEFAULT_ROI)

        # Corrupt JSON
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{invalid json content ...")
            bad_json_path = f.name
        try:
            cam_bad_json = VirtualArmCamera(calib_path=bad_json_path)
            self.assertEqual(cam_bad_json.roi, DEFAULT_ROI)
        finally:
            if os.path.exists(bad_json_path):
                os.remove(bad_json_path)

        # Valid JSON but missing 'roi'
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(json.dumps({"other_field": 123}))
            empty_keys_path = f.name
        try:
            cam_no_roi = VirtualArmCamera(calib_path=empty_keys_path)
            self.assertEqual(cam_no_roi.roi, DEFAULT_ROI)
        finally:
            if os.path.exists(empty_keys_path):
                os.remove(empty_keys_path)

    def test_gripper_and_arm_states(self):
        """Verify arm states and gripper visuals render without matrix dimension errors."""
        states = ["IDLE", "AL", "GORME_AL", "BASLA_BEK", "UNKNOWN_STATE", "", None]
        for st in states:
            for grip in [True, False]:
                frame = self.cam.render(has_cube=True, cube_color="GREEN", gripper_closed=grip, arm_state=st)
                self.assertEqual(frame.shape, (480, 640, 3))


class TestVirtualVehicleCameraAdversarial(unittest.TestCase):
    """Adversarial challenge tests for VirtualVehicleCamera depth maps and perspective."""

    def setUp(self):
        self.cam = VirtualVehicleCamera()

    def test_depth_strict_uint16_and_no_nan_inf(self):
        """Verify vehicle camera depth map is strictly positive uint16 with no NaN or Inf."""
        poses = [
            (380.0, 270.0, 0.0),
            (0.0, 0.0, 0.0),
            (-1000.0, 5000.0, -math.pi),
            (1e5, 1e5, 4.0 * math.pi),
            (850.0, 420.0, math.pi / 2.0),
            (250.0, 570.0, -math.pi / 2.0),
        ]
        signs = [None, "pedestrian", "yaya_gecidi", "parking", "park", "bogus_sign", ""]
        bays = [None, "RED", "GREEN", "BLUE", "red", "green", "blue", "unknown", ""]

        for pose in poses:
            for s in signs:
                for b in bays:
                    bgr, depth = self.cam.render(pose=pose, target_sign=s, target_bay=b)
                    self.assertEqual(bgr.shape, (480, 640, 3))
                    self.assertEqual(bgr.dtype, np.uint8)
                    self.assertEqual(depth.shape, (480, 640))
                    self.assertEqual(depth.dtype, np.uint16, "Depth array MUST be strictly uint16")
                    self.assertTrue(np.all(depth > 0), "Depth values MUST be strictly positive (> 0)")
                    self.assertFalse(np.isnan(depth).any(), "Depth array must contain no NaN")
                    self.assertFalse(np.isinf(depth).any(), "Depth array must contain no Inf")
                    self.assertGreaterEqual(int(np.min(depth)), 250, "Depth must honor minimum range (250mm)")
                    self.assertLessEqual(int(np.max(depth)), 4500, "Depth must honor maximum range (4500mm)")

    def test_depth_monotonic_ground_gradient(self):
        """Verify ground depth below horizon decreases monotonically as row index increases."""
        bgr, depth = self.cam.render(target_sign=None, target_bay=None)
        v_horiz = self.cam.v_horizon

        # Check values above/at horizon: constant 3000 mm
        self.assertTrue(np.all(depth[:v_horiz, :] == 3000))
        self.assertTrue(np.all(depth[v_horiz, :] == 3000))

        # Check column 320 below horizon: strictly non-increasing (monotonically getting closer)
        column_depths = [int(depth[v, 320]) for v in range(v_horiz + 1, 480)]
        for i in range(len(column_depths) - 1):
            self.assertGreaterEqual(
                column_depths[i],
                column_depths[i + 1],
                f"Depth at row {v_horiz + 1 + i} ({column_depths[i]}) < row {v_horiz + 2 + i} ({column_depths[i + 1]})",
            )

        # Near ground check (row 479)
        self.assertEqual(int(depth[479, 320]), 509)

    def test_depth_discrete_features_bounds(self):
        """Verify depth map accurately imprints pedestrian zebra, signs, and parking floor."""
        # 1. Pedestrian Crossing
        _, depth_ped = self.cam.render(target_sign="pedestrian")
        # Stripe at stripe_x=220, y in [300:360] has depth 1200 mm
        self.assertEqual(int(depth_ped[330, 230]), 1200)
        # Sign post at x in [460:490], y in [170:200] has depth 1800 mm
        self.assertEqual(int(depth_ped[180, 470]), 1800)

        # 2. Parking Sign
        _, depth_park = self.cam.render(target_sign="parking")
        self.assertEqual(int(depth_park[180, 470]), 1800)

        # 3. Ground Parking Bay Floor
        _, depth_bay = self.cam.render(target_bay="BLUE")
        self.assertEqual(int(depth_bay[400, 300]), 800)

    def test_camera_geometry_perturbation(self):
        """Verify camera initialization under various pitch angles and heights."""
        pitches = [0.0, 5.0, 15.0, 30.0, 45.0, 75.0]
        heights = [0.10, 0.20, 0.50, 1.50]

        for p in pitches:
            for h in heights:
                cam = VirtualVehicleCamera(cam_height_m=h, cam_pitch_deg=p)
                _, depth = cam.render()
                self.assertEqual(depth.dtype, np.uint16)
                self.assertTrue(np.all(depth > 0))
                self.assertFalse(np.isnan(depth).any())

    def test_synthetic_realsense_bridge_lifecycle(self):
        """Verify lifecycle of SyntheticRealSenseBridge drop-in SITL driver."""
        bridge = SyntheticRealSenseBridge({"width": 640, "height": 480, "crop_top_ratio": 0.2917, "enable_depth": True})

        # Before start
        ok, c, d = bridge.read_with_depth()
        self.assertFalse(ok)
        self.assertIsNone(c)
        self.assertIsNone(d)

        # After start
        bridge.start()
        ok, c, d = bridge.read_with_depth()
        self.assertTrue(ok)
        self.assertEqual(c.shape, (340, 640, 3))
        self.assertEqual(d.shape, (340, 640))
        self.assertEqual(d.dtype, np.uint16)
        self.assertTrue(np.all(d > 0))

        # Test read() color-only
        ok2, c2 = bridge.read()
        self.assertTrue(ok2)
        self.assertEqual(c2.shape, (340, 640, 3))

        bridge.stop()
        ok3, _, _ = bridge.read_with_depth()
        self.assertFalse(ok3)

        # Context manager
        with SyntheticRealSenseBridge({"enable_depth": False}) as b:
            ok4, c4, d4 = b.read_with_depth()
            self.assertTrue(ok4)
            self.assertIsNotNone(c4)
            self.assertIsNone(d4)


class TestPygameRendererHeadlessStress(unittest.TestCase):
    """Stress tests Pygame ArenaRenderer under headless conditions and rapid execution."""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.world = FactoryWorld()

    def test_surface_dimension_extremes(self):
        """Verify ArenaRenderer functions across extreme target surface dimensions."""
        sizes = [
            (1040, 900),   # Standard arena dimensions
            (1600, 900),   # Full application display window
            (800, 600),    # Mid-size scaling
            (320, 240),    # Small surface
            (1, 1),        # Minimal 1x1 surface
            (0, 0),        # Degenerate 0x0 surface
        ]

        for sz in sizes:
            surf = pygame.Surface(sz)
            renderer = ArenaRenderer(surf)
            renderer.render(self.world)
            if sz[0] > 0 and sz[1] > 0:
                buf = pygame.surfarray.array3d(surf)
                self.assertEqual(buf.shape, (sz[0], sz[1], 3))
                self.assertEqual(buf.dtype, np.uint8)
                self.assertGreater(int(buf.sum()), 0, f"Surface {sz} was completely black")

    def test_font_fallback_resilience(self):
        """Verify ArenaRenderer handles missing system fonts gracefully via fallback."""
        def mock_bad_sysfont(*args, **kwargs):
            raise RuntimeError("System font not available")

        orig_sysfont = pygame.font.SysFont
        pygame.font.SysFont = mock_bad_sysfont
        try:
            surf = pygame.Surface((1040, 900))
            renderer = ArenaRenderer(surf)
            renderer.render(self.world)
            buf = pygame.surfarray.array3d(surf)
            self.assertGreater(int(buf.sum()), 0)
        finally:
            pygame.font.SysFont = orig_sysfont

    def test_rapid_headless_burst_500_frames(self):
        """Verify rapid burst of 500 consecutive render calls maintains high performance."""
        surf = pygame.Surface((1040, 900))
        renderer = ArenaRenderer(surf)

        self.world.add_cube("RED")
        self.world.conveyor.is_running = True

        t_start = time.perf_counter()
        for i in range(500):
            dt = 0.01667 if i % 10 != 0 else 0.0
            self.world.step(dt)
            renderer.render(self.world, dt=dt)

        t_end = time.perf_counter()
        elapsed = t_end - t_start
        fps = 500.0 / elapsed
        # Headless rendering should comfortably exceed 60 FPS
        self.assertGreater(fps, 60.0, f"Rendering speed {fps:.1f} FPS is below required 60 FPS")

    def test_offscreen_buffer_integrity(self):
        """Verify that rendered offscreen Pygame surface buffer has valid pixel data."""
        surf = pygame.Surface((1040, 900))
        renderer = ArenaRenderer(surf)
        renderer.render(self.world)

        buf = pygame.surfarray.array3d(surf)
        self.assertEqual(buf.shape, (1040, 900, 3))
        self.assertEqual(buf.dtype, np.uint8)
        self.assertFalse(np.isnan(buf).any())
        self.assertGreater(int(buf.sum()), 1_000_000)

        # Check specific coordinate colors (floor background is (245, 247, 250))
        pixel_corner = surf.get_at((50, 50))
        self.assertIn(pixel_corner[0], range(240, 256))
        self.assertIn(pixel_corner[1], range(240, 256))
        self.assertIn(pixel_corner[2], range(240, 256))

    def test_renderer_entity_extremes(self):
        """Verify renderer survives missing/corrupt states and entity extremes."""
        surf = pygame.Surface((1040, 900))
        renderer = ArenaRenderer(surf)

        # 1. Corrupt/missing PLC states
        plc_states = [None, {}, {"red_lamp": True, "green_lamp": True, "amber_lamp": True}, {"bogus": 123}]
        for plc in plc_states:
            renderer.render(self.world, plc_state=plc)

        # 2. Corrupt/missing arm states
        arm_states = [
            None,
            {},
            {"theta_base": 1e4, "theta_elbow": -1e4, "gripper_closed": True},
            {"theta_base": 0.0, "theta_elbow": 0.0, "held_cube": Cube("RED", x=780.0)},
        ]
        for arm in arm_states:
            renderer.render(self.world, arm_state=arm)

        # 3. Multiple cubes on conveyor
        for color in ["RED", "GREEN", "BLUE"]:
            self.world.conveyor.cubes.append(Cube(color, x=100.0))
        renderer.render(self.world)


class TestCameraHUDViewAdversarial(unittest.TestCase):
    """Stress tests CameraHUDView and OpenCV-to-Pygame surface conversion."""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.screen = pygame.Surface((1600, 900))
        self.hud = CameraHUDView(self.screen)

    def test_bgr_to_pygame_surface_malformed_inputs(self):
        """Verify bgr_to_pygame_surface safely handles None, empty, 1x1, and non-arrays."""
        test_inputs = [
            None,
            np.array([]),
            np.zeros((0, 0, 3), dtype=np.uint8),
            np.zeros((1, 1, 3), dtype=np.uint8),
            np.full((100, 100, 3), fill_value=128, dtype=np.uint8),
            "invalid_string_input",
            12345,
        ]

        for inp in test_inputs:
            surf = bgr_to_pygame_surface(inp, (270, 202))
            self.assertIsInstance(surf, pygame.Surface)
            self.assertEqual(surf.get_size(), (270, 202))

    def test_depth_pip_extremes(self):
        """Verify depth picture-in-picture handles all-zero, all-65535, and out-of-range depths."""
        depth_cases = [
            np.zeros((480, 640), dtype=np.uint16),
            np.full((480, 640), fill_value=65535, dtype=np.uint16),
            np.full((480, 640), fill_value=1200, dtype=np.uint16),
            np.array([], dtype=np.uint16),
        ]

        for d in depth_cases:
            self.hud.render_vehicle_camera(
                frame_bgr=np.zeros((480, 640, 3), dtype=np.uint8),
                depth_z16=d,
                telemetry={"steer_angle": 110.0, "track_status": "LOCKED"},
            )

    def test_telemetry_overlays_extremes(self):
        """Verify telemetry overlays handle extreme and None values."""
        telemetry_cases = [
            None,
            {},
            {
                "steer_angle": 999999.0,
                "track_status": "SUPER_EXTREME_LONG_STATUS_STRING",
                "sign_label": "PEDESTRIAN_CROSSING_AHEAD_WARNING",
                "bay_distance_cm": 99999.9,
                "target_point": (-5000, 50000),
            },
            {
                "steer_angle": -999999.0,
                "track_status": "",
                "sign_label": "",
                "bay_distance_cm": -10.0,
                "target_point": (0, 0),
            },
        ]

        for tel in telemetry_cases:
            self.hud.render_vehicle_camera(
                frame_bgr=np.full((480, 640, 3), fill_value=30, dtype=np.uint8),
                depth_z16=np.full((480, 640), fill_value=1500, dtype=np.uint16),
                telemetry=tel,
            )


if __name__ == "__main__":
    unittest.main()
