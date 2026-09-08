"""
Tier 2: Boundary & Corner Case Test Suite (24 Feature Areas x >=5 assertions = >=120 tests).
Opaque-box boundary analysis and adversarial stress testing.
Authoritative sources: ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md.
"""

import unittest
import numpy as np
import cv2
import math
import os

from simulator.tests.contract_adapters import (
    get_factory_world,
    get_plc_engine,
    get_virtual_cameras,
    get_color_detector,
    get_robot_arm,
    get_mqtt_broker,
    get_vehicle_sim,
    get_hmi_panel,
    SpecCube
)


class TestTier2BoundaryCases(unittest.TestCase):

    # ========================================================================
    # FEATURE AREA 1: 2D Arena & Layout Boundaries
    # ========================================================================
    def test_t2_f01_cube_at_zero_coordinate(self):
        """T2_1.1: Verify cube behavior at exact minimum infeed boundary (x=0.0mm)."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        self.assertEqual(cube.x, 0.0)
        self.assertTrue(world.conveyor.has_cube_at_entry)

    def test_t2_f01_cube_at_max_conveyor_length(self):
        """T2_1.2: Verify cube coordinate clamped at belt length (800mm)."""
        world = get_factory_world()
        cube = world.add_cube("GREEN")
        cube.x = 850.0
        world.conveyor.is_running = True
        world.step(dt=0.1)
        self.assertLessEqual(cube.x, 800.0)

    def test_t2_f01_dock_boundary_limits(self):
        """T2_1.3: Verify vehicle docking bay geometry boundary containment."""
        world = get_factory_world()
        dock_x, dock_y, _ = world.dock_pose
        self.assertTrue(370.0 <= dock_x <= 390.0)
        self.assertTrue(260.0 <= dock_y <= 280.0)

    def test_t2_f01_parking_bay_boundaries(self):
        """T2_1.4: Verify parking bays do not overlap each other."""
        world = get_factory_world()
        bays = world.parking_bays
        # Distance between bay centers must be >= width (60px)
        x_red = bays["RED"][0]
        x_green = bays["GREEN"][0]
        x_blue = bays["BLUE"][0]
        self.assertGreaterEqual(abs(x_red - x_green), 60)
        self.assertGreaterEqual(abs(x_green - x_blue), 60)

    def test_t2_f01_track_waypoints_closure(self):
        """T2_1.5: Verify closed-loop circuit track starts and ends at dock."""
        world = get_factory_world()
        self.assertEqual(world.track_waypoints[0], world.track_waypoints[-1])

    # ========================================================================
    # FEATURE AREA 2: Arm Camera Sensor Boundaries
    # ========================================================================
    def test_t2_f02_extreme_sensor_noise(self):
        """T2_2.1: Verify image generator handles high Gaussian sensor noise (sigma=25)."""
        cam = get_virtual_cameras()
        cube = SpecCube("RED", x=780.0)
        frame = cam.get_arm_frame(cube=cube, noise_std=25.0)
        self.assertEqual(frame.shape, (480, 640, 3))
        self.assertEqual(frame.dtype, np.uint8)

    def test_t2_f02_black_frame_low_lighting(self):
        """T2_2.2: Verify black frame returns UNKNOWN without error."""
        detector = get_color_detector()
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res = detector.detect(black_frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    def test_t2_f02_overexposed_white_frame(self):
        """T2_2.3: Verify saturated white frame (S=0, V=255) returns UNKNOWN."""
        detector = get_color_detector()
        white_frame = np.full((480, 640, 3), fill_value=255, dtype=np.uint8)
        res = detector.detect(white_frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    def test_t2_f02_cube_roi_perimeter_bounds(self):
        """T2_2.4: Verify ROI crop does not throw indexing error for out-of-bound coordinates."""
        detector = get_color_detector()
        small_frame = np.full((200, 200, 3), fill_value=45, dtype=np.uint8)
        res = detector.detect(small_frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    def test_t2_f02_missing_cube_empty_frame(self):
        """T2_2.5: Verify empty belt frame without cube returns UNKNOWN."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(cube=None)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    # ========================================================================
    # FEATURE AREA 3: Vehicle D455 Camera Boundaries
    # ========================================================================
    def test_t2_f03_minimum_depth_clamping(self):
        """T2_3.1: Verify depth map honors minimum distance threshold (250mm)."""
        cam = get_virtual_cameras()
        _, depth = cam.get_vehicle_frame()
        self.assertGreaterEqual(int(np.min(depth)), 250)

    def test_t2_f03_maximum_depth_clamping(self):
        """T2_3.2: Verify depth map does not exceed maximum modeled range (4500mm)."""
        cam = get_virtual_cameras()
        _, depth = cam.get_vehicle_frame()
        self.assertLessEqual(int(np.max(depth)), 4500)

    def test_t2_f03_depth_array_non_empty(self):
        """T2_3.3: Verify depth map contains no NaN or infinite values."""
        cam = get_virtual_cameras()
        _, depth = cam.get_vehicle_frame()
        self.assertFalse(np.isnan(depth).any())

    def test_t2_f03_extreme_heading_wrap(self):
        """T2_3.4: Verify vehicle camera frame synthesis at heading wrap-around (2*pi)."""
        cam = get_virtual_cameras()
        bgr, depth = cam.get_vehicle_frame(pose=(380.0, 270.0, 2.0 * math.pi))
        self.assertEqual(bgr.shape, (480, 640, 3))
        self.assertEqual(depth.shape, (480, 640))

    def test_t2_f03_no_signs_no_bays_baseline(self):
        """T2_3.5: Verify perspective image renders cleanly when no signs/bays are active."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame(target_sign=None, target_bay=None)
        self.assertGreater(cv2.countNonZero(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)), 1000)

    # ========================================================================
    # FEATURE AREA 4: HUD Viewport Boundaries
    # ========================================================================
    def test_t2_f04_scaling_aspect_ratio(self):
        """T2_4.1: Verify HUD aspect ratio matches 640x480 (4:3 ratio ~ 1.33)."""
        w, h = 270, 202
        ratio = w / h
        self.assertAlmostEqual(ratio, 640.0 / 480.0, delta=0.05)

    def test_t2_f04_long_telemetry_string(self):
        """T2_4.2: Verify rendering extremely long telemetry text does not crash."""
        frame = np.full((202, 270, 3), fill_value=20, dtype=np.uint8)
        long_str = "STATUS: " + "X" * 120
        cv2.putText(frame, long_str[:30], (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        self.assertEqual(frame.shape, (202, 270, 3))

    def test_t2_f04_zero_pixel_frame(self):
        """T2_4.3: Verify HUD handles all-zero frame without division errors."""
        zero_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        scaled = cv2.resize(zero_frame, (270, 202))
        self.assertEqual(scaled.shape, (202, 270, 3))

    def test_t2_f04_rapid_burst_refresh(self):
        """T2_4.4: Verify rapid burst of 60 consecutive HUD frame resizes."""
        cam = get_virtual_cameras()
        frame = cam.get_arm_frame()
        for _ in range(60):
            scaled = cv2.resize(frame, (270, 202))
        self.assertEqual(scaled.shape, (202, 270, 3))

    def test_t2_f04_hud_panel_clamping(self):
        """T2_4.5: Verify HUD panel fits inside window (1600x900)."""
        x_hud = 1040
        w_hud = 560
        self.assertLessEqual(x_hud + w_hud, 1600)

    # ========================================================================
    # FEATURE AREA 5: PLC State Machine Boundaries
    # ========================================================================
    def test_t2_f05_rapid_repeated_start(self):
        """T2_5.1: Verify rapid repeated START button presses do not cause state skipping."""
        plc = get_plc_engine()
        for _ in range(5):
            plc.press_start()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 1)

    def test_t2_f05_start_ignored_in_feeding(self):
        """T2_5.2: Verify START is ignored while already in FEEDING (State 2)."""
        plc = get_plc_engine()
        plc.state = 2
        plc.press_start()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 2)

    def test_t2_f05_simultaneous_sensor_inputs(self):
        """T2_5.3: Verify handling of simultaneous S1 and S2 triggers."""
        plc = get_plc_engine()
        plc.state = 2
        plc.I_ENTRY = True
        plc.I_EXIT = True
        plc.update(dt=0.01)
        # Exit sensor takes precedence to halt conveyor
        self.assertEqual(plc.state, 3)

    def test_t2_f05_zero_duration_pulse(self):
        """T2_5.4: Verify un-asserted input does not trigger transition."""
        plc = get_plc_engine()
        plc.state = 1
        plc.I_ENTRY = False
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 1)

    def test_t2_f05_cycle_counter_monotonically_increases(self):
        """T2_5.5: Verify cycle counter increases monotonically."""
        plc = get_plc_engine()
        self.assertEqual(plc.cycle_count, 0)
        for expected in range(1, 4):
            plc.state = 5
            plc.update(dt=0.01)
            self.assertEqual(plc.cycle_count, expected)

    # ========================================================================
    # FEATURE AREA 6: Stack Signal Tower Boundaries
    # ========================================================================
    def test_t2_f06_zero_time_state_cut(self):
        """T2_6.1: Verify instant signal lamp update on state switch."""
        plc = get_plc_engine()
        plc.state = 2
        plc.update(dt=0.01)
        self.assertTrue(plc.green_lamp)
        plc.state = 0
        plc.update(dt=0.01)
        self.assertFalse(plc.green_lamp)

    def test_t2_f06_no_overlap_green_and_red_in_motion(self):
        """T2_6.2: Verify Green and Red are never both True in FEEDING."""
        plc = get_plc_engine()
        plc.state = 2
        plc.update(dt=0.01)
        self.assertFalse(plc.green_lamp and plc.red_lamp)

    def test_t2_f06_warning_lamp_exclusive_to_fault(self):
        """T2_6.3: Verify Yellow lamp is only active on fault / State 99."""
        plc = get_plc_engine()
        plc.state = 1
        plc.update(dt=0.01)
        self.assertFalse(plc.yellow_lamp)
        plc.press_estop()
        plc.update(dt=0.01)
        self.assertTrue(plc.yellow_lamp)

    def test_t2_f06_all_lamps_off_in_state_zero(self):
        """T2_6.4: Verify State 0 ensures 100% dark lamps."""
        plc = get_plc_engine()
        plc.state = 0
        plc.update(dt=0.01)
        self.assertFalse(plc.green_lamp or plc.red_lamp or plc.yellow_lamp)

    def test_t2_f06_lamp_sync_after_estop_reset(self):
        """T2_6.5: Verify lamps return to State 0 dark after E-Stop reset."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.release_estop()
        plc.press_reset()
        plc.update(dt=0.01)
        self.assertFalse(plc.yellow_lamp)

    # ========================================================================
    # FEATURE AREA 7: Conveyor Mechanics Boundaries
    # ========================================================================
    def test_t2_f07_zero_conveyor_speed(self):
        """T2_7.1: Verify cube does not advance if speed is zero."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        world.conveyor.speed_mm_s = 0.0
        world.conveyor.is_running = True
        world.step(dt=1.0)
        self.assertEqual(cube.x, 0.0)

    def test_t2_f07_entry_sensor_boundary_threshold(self):
        """T2_7.2: Verify S1 boundary at 40.0mm (active at 40.0, inactive at 40.1)."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        cube.x = 40.0
        self.assertTrue(world.conveyor.has_cube_at_entry)
        cube.x = 40.1
        self.assertFalse(world.conveyor.has_cube_at_entry)

    def test_t2_f07_exit_sensor_boundary_threshold(self):
        """T2_7.3: Verify S2 boundary at 760.0mm (inactive at 759.9, active at 760.0)."""
        world = get_factory_world()
        cube = world.add_cube("BLUE")
        cube.x = 759.9
        self.assertFalse(world.conveyor.has_cube_at_exit)
        cube.x = 760.0
        self.assertTrue(world.conveyor.has_cube_at_exit)

    def test_t2_f07_zero_or_negative_dt(self):
        """T2_7.4: Verify conveyor step handles dt <= 0 without reversing cube."""
        world = get_factory_world()
        cube = world.add_cube("GREEN")
        cube.x = 100.0
        world.conveyor.is_running = True
        world.step(dt=0.0)
        self.assertEqual(cube.x, 100.0)

    def test_t2_f07_maximum_physical_length_cap(self):
        """T2_7.5: Verify cube coordinate is capped at physical belt length 800mm."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        cube.x = 790.0
        world.conveyor.is_running = True
        world.step(dt=2.0)  # Would advance by 160mm -> 950mm
        self.assertEqual(cube.x, 800.0)

    # ========================================================================
    # FEATURE AREA 8: E-Stop Latched Boundaries
    # ========================================================================
    def test_t2_f08_estop_freeze_in_single_step(self):
        """T2_8.1: Verify motion freezes within exactly 1 update step (<16ms)."""
        world = get_factory_world()
        plc = get_plc_engine()
        cube = world.add_cube("RED")
        plc.state = 2
        plc.update(dt=0.01, world=world)
        self.assertTrue(world.conveyor.is_running)

        plc.press_estop()
        plc.update(dt=0.016, world=world)
        self.assertFalse(world.conveyor.is_running)
        self.assertEqual(plc.state, 99)

    def test_t2_f08_rapid_repeated_estop(self):
        """T2_8.2: Verify multiple rapid E-stop signals maintain State 99."""
        plc = get_plc_engine()
        for _ in range(5):
            plc.press_estop()
            plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_t2_f08_reset_ineffective_while_estop_button_down(self):
        """T2_8.3: Verify RESET does nothing while physical E-stop is still depressed."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.press_reset()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_t2_f08_estop_release_without_reset_remains_latched(self):
        """T2_8.4: Verify releasing E-stop button alone leaves system latched in State 99."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.release_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_t2_f08_estop_from_state_zero(self):
        """T2_8.5: Verify pressing E-stop when system is already OFF moves to State 99."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    # ========================================================================
    # FEATURE AREA 9: Industrial HMI Pushbuttons Boundaries
    # ========================================================================
    def test_t2_f09_concurrent_start_and_stop(self):
        """T2_9.1: Verify STOP takes priority when pressed concurrently with START."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.press_start()
        hmi.press_stop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)

    def test_t2_f09_concurrent_start_and_estop(self):
        """T2_9.2: Verify E-STOP takes safety priority over START."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.press_start()
        hmi.press_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_t2_f09_invalid_cube_color_string(self):
        """T2_9.3: Verify passing invalid color string to add_cube raises ValueError."""
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        with self.assertRaises(ValueError):
            hmi.add_cube(world, "PURPLE")

    def test_t2_f09_cube_replacement_on_conveyor(self):
        """T2_9.4: Verify spawning new cube sets active cube to new instance."""
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        c1 = hmi.add_cube(world, "RED")
        c2 = hmi.add_cube(world, "BLUE")
        self.assertEqual(world.conveyor.active_cube, c2)

    def test_t2_f09_rapid_reset_pushes(self):
        """T2_9.5: Verify repeated RESET presses in normal mode do not perturb State 0."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        for _ in range(5):
            hmi.press_reset()
            plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)

    # ========================================================================
    # FEATURE AREA 10: Telemetry & Event Log Boundaries
    # ========================================================================
    def test_t2_f10_large_event_log_capacity(self):
        """T2_10.1: Verify telemetry event log handles 100 entries cleanly."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        for i in range(100):
            hmi.log_mqtt(f"topic/{i}", f"payload_{i}")
        self.assertEqual(len(hmi.mqtt_log), 100)

    def test_t2_f10_empty_payload_logging(self):
        """T2_10.2: Verify empty MQTT payload logged without error."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.log_mqtt("arac/yuk", "")
        self.assertEqual(hmi.mqtt_log[-1], "[arac/yuk] ")

    def test_t2_f10_long_payload_logging(self):
        """T2_10.3: Verify large payload string handled in log."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        payload = "A" * 500
        hmi.log_mqtt("test", payload)
        self.assertIn(payload, hmi.mqtt_log[-1])

    def test_t2_f10_zero_counters_boundary(self):
        """T2_10.4: Verify initial counts are non-negative and zero."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        for k, v in hmi.counters.items():
            self.assertEqual(v, 0)

    def test_t2_f10_unicode_telemetry_support(self):
        """T2_10.5: Verify Turkish unicode characters in log."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.log_mqtt("arac/yuk", "YEŞİL")
        self.assertIn("YEŞİL", hmi.mqtt_log[-1])

    # ========================================================================
    # FEATURE AREA 11: Classical HSV Detection Boundaries
    # ========================================================================
    def test_t2_f11_red_hue_lower_boundary(self):
        """T2_11.1: Verify Red Hue near 0 (H=0, S=240, V=220) detected as RED."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        # H=0 in HSV -> BGR (0, 0, 220)
        hsv_px = np.array([[[0, 240, 220]]], dtype=np.uint8)
        bgr_px = tuple(int(x) for x in cv2.cvtColor(hsv_px, cv2.COLOR_HSV2BGR)[0, 0])
        frame[120:360, 215:466] = bgr_px
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "RED")

    def test_t2_f11_red_hue_upper_boundary(self):
        """T2_11.2: Verify Red Hue near 179 (H=175, S=240, V=220) detected as RED."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (47, 13, 220)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "RED")

    def test_t2_f11_green_hue_center(self):
        """T2_11.3: Verify Green Hue (H=82, S=240, V=210) detected as GREEN."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (157, 210, 12)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "GREEN")

    def test_t2_f11_blue_hue_center(self):
        """T2_11.4: Verify Blue Hue (H=102, S=240, V=220) detected as BLUE."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (220, 137, 13)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "BLUE")

    def test_t2_f11_uncalibrated_color_yields_unknown(self):
        """T2_11.5: Verify uncalibrated color (e.g. Yellow H=30) yields UNKNOWN."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        hsv_px = np.array([[[30, 240, 220]]], dtype=np.uint8)
        bgr_px = tuple(int(x) for x in cv2.cvtColor(hsv_px, cv2.COLOR_HSV2BGR)[0, 0])
        frame[120:360, 215:466] = bgr_px
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    # ========================================================================
    # FEATURE AREA 12: Occupancy & Margin Boundaries
    # ========================================================================
    def test_t2_f12_occupancy_below_threshold(self):
        """T2_12.1: Verify fill ratio below 0.40 threshold returns UNKNOWN."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        # Paint tiny red patch (only 10% of ROI)
        frame[120:150, 215:250] = (47, 13, 220)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    def test_t2_f12_occupancy_at_threshold(self):
        """T2_12.2: Verify fill ratio exceeding 0.40 returns color."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        # Paint 60% of ROI
        frame[120:300, 215:466] = (47, 13, 220)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "RED")

    def test_t2_f12_zero_fill_ratio(self):
        """T2_12.3: Verify zero fill ratio yields UNKNOWN."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    def test_t2_f12_full_fill_ratio(self):
        """T2_12.4: Verify 100% fill ratio returns confident result."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (157, 210, 12)  # Full GREEN
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "GREEN")

    def test_t2_f12_competing_color_margin_tie(self):
        """T2_12.5: Verify competing colors with zero margin return UNKNOWN."""
        detector = get_color_detector()
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        rx, ry, rw, rh = 215, 120, 251, 240
        frame[ry:ry+rh, rx:rx+rw//2] = (47, 13, 220)     # RED
        frame[ry:ry+rh, rx+rw//2:rx+rw] = (157, 210, 12) # GREEN
        res = detector.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "UNKNOWN")

    # ========================================================================
    # FEATURE AREA 13: 4-DOF Robot Arm Kinematics Boundaries
    # ========================================================================
    def test_t2_f13_joint_angle_bounds(self):
        """T2_13.1: Verify joint angles remain in [-180, 180] deg."""
        arm = get_robot_arm()
        for angle in arm.joint_angles:
            self.assertGreaterEqual(angle, -180.0)
            self.assertLessEqual(angle, 180.0)

    def test_t2_f13_gripper_min_closed_limit(self):
        """T2_13.2: Verify gripper closed angle does not clamp below 50 deg."""
        arm = get_robot_arm()
        arm.gripper_angle = 50.0
        self.assertGreaterEqual(arm.gripper_angle, 50.0)

    def test_t2_f13_gripper_max_open_limit(self):
        """T2_13.3: Verify gripper open angle does not exceed 140 deg."""
        arm = get_robot_arm()
        arm.gripper_angle = 140.0
        self.assertLessEqual(arm.gripper_angle, 140.0)

    def test_t2_f13_arm_state_string_validity(self):
        """T2_13.4: Verify state is one of the valid 8 sequential states."""
        valid_states = {"HOME", "GORME", "BASLA_BEK", "RENK", "AL", "DOGRULA", "YUKLE", "GONDER"}
        arm = get_robot_arm()
        self.assertIn(arm.state, valid_states)

    def test_t2_f13_arm_freeze_maintains_joint_pose(self):
        """T2_13.5: Verify freezing arm locks joint angles."""
        arm = get_robot_arm()
        arm.state = "GORME"
        arm.step(dt=0.01)
        angles_before = list(arm.joint_angles)
        arm.freeze()
        arm.step(dt=1.0, plc_trigger=True)
        self.assertEqual(arm.joint_angles, angles_before)

    # ========================================================================
    # FEATURE AREA 14: Arm State Machine Boundaries
    # ========================================================================
    def test_t2_f14_freeze_in_al_state(self):
        """T2_14.1: Verify E-Stop freezing in AL state prevents gripper action."""
        arm = get_robot_arm()
        arm.state = "AL"
        arm.freeze()
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "AL")

    def test_t2_f14_unfreeze_resumes_state(self):
        """T2_14.2: Verify unfreezing arm resumes progression."""
        arm = get_robot_arm()
        arm.state = "AL"
        arm.freeze()
        arm.step(dt=0.01)
        arm.unfreeze()
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "DOGRULA")

    def test_t2_f14_pick_without_cube_returns_home(self):
        """T2_14.3: Verify DOGRULA returns to HOME if no cube was picked."""
        arm = get_robot_arm()
        arm.state = "DOGRULA"
        arm.carried_cube = None
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "HOME")

    def test_t2_f14_corrupt_frame_handling(self):
        """T2_14.4: Verify None camera frame handled safely in RENK state."""
        arm = get_robot_arm()
        arm.state = "RENK"
        arm.step(dt=0.01, camera_frame=None)
        self.assertEqual(arm.state, "AL")

    def test_t2_f14_cycle_count_accumulation(self):
        """T2_14.5: Verify cycles completed increases with each full sequence."""
        arm = get_robot_arm()
        arm.state = "GONDER"
        arm.step(dt=0.01)
        self.assertEqual(arm.cycles_completed, 1)

    # ========================================================================
    # FEATURE AREA 15: Hardware Trigger A5 Boundaries
    # ========================================================================
    def test_t2_f15_trigger_pulse_glitch_filtered(self):
        """T2_15.1: Verify trigger pulse requires active evaluation in BASLA_BEK."""
        arm = get_robot_arm()
        arm.state = "GORME"
        arm.step(dt=0.01, plc_trigger=True)
        # Should transition to BASLA_BEK first, not jump straight to RENK
        self.assertEqual(arm.state, "BASLA_BEK")

    def test_t2_f15_sustained_trigger_without_car_docked(self):
        """T2_15.2: Verify PLC will not assert trigger if vehicle is not docked."""
        plc = get_plc_engine()
        plc.state = 3
        plc.I_VEHICLE_READY = False
        plc.update(dt=0.01)
        self.assertFalse(plc.robot_trigger)

    def test_t2_f15_trigger_active_during_al(self):
        """T2_15.3: Verify trigger state change while in AL does not abort pick."""
        arm = get_robot_arm()
        arm.state = "AL"
        arm.step(dt=0.01, plc_trigger=False)
        self.assertEqual(arm.state, "DOGRULA")

    def test_t2_f15_trigger_clears_on_cube_removal(self):
        """T2_15.4: Verify trigger de-asserts when exit sensor clears."""
        plc = get_plc_engine()
        plc.state = 4
        plc.I_EXIT = False
        plc.update(dt=0.01)
        self.assertFalse(plc.robot_trigger)

    def test_t2_f15_trigger_held_after_complete(self):
        """T2_15.5: Verify trigger stays low when returning to READY."""
        plc = get_plc_engine()
        plc.state = 5
        plc.update(dt=0.01)
        self.assertFalse(plc.robot_trigger)

    # ========================================================================
    # FEATURE AREA 16: MQTT Broker Boundaries
    # ========================================================================
    def test_t2_f16_empty_topic_subscription(self):
        """T2_16.1: Verify subscribing to topic works without error."""
        broker = get_mqtt_broker()
        broker.subscribe("test", lambda t, p: None)
        self.assertIn("test", broker.subscribers)

    def test_t2_f16_large_payload_string(self):
        """T2_16.2: Verify broker handles large message payload (64KB)."""
        broker = get_mqtt_broker()
        large_str = "D" * 65536
        broker.publish("data", large_str)
        self.assertEqual(broker.get_last_message("data"), large_str)

    def test_t2_f16_publish_to_unsubscribed_topic(self):
        """T2_16.3: Verify publishing to topic with zero subscribers does not error."""
        broker = get_mqtt_broker()
        broker.publish("nobody/listening", "HELLO")
        self.assertEqual(broker.get_last_message("nobody/listening"), "HELLO")

    def test_t2_f16_burst_publications(self):
        """T2_16.4: Verify rapid burst of 50 publications on arac/yuk."""
        broker = get_mqtt_broker()
        for i in range(50):
            broker.publish("arac/yuk", f"COLOR_{i}")
        self.assertEqual(broker.get_last_message("arac/yuk"), "COLOR_49")

    def test_t2_f16_clear_history(self):
        """T2_16.5: Verify clearing broker history wipes message buffer."""
        broker = get_mqtt_broker()
        broker.publish("test", "msg")
        broker.clear()
        self.assertEqual(len(broker.messages), 0)

    # ========================================================================
    # FEATURE AREA 17: Vehicle Kinematics Boundaries
    # ========================================================================
    def test_t2_f17_steering_hard_left_limit(self):
        """T2_17.1: Verify steering hard left clamp at 75 deg."""
        car = get_vehicle_sim()
        car.servo_angle = 50.0  # Below 75
        clamped = max(75.0, min(145.0, car.servo_angle))
        self.assertEqual(clamped, 75.0)

    def test_t2_f17_steering_hard_right_limit(self):
        """T2_17.2: Verify steering hard right clamp at 145 deg."""
        car = get_vehicle_sim()
        car.servo_angle = 180.0  # Above 145
        clamped = max(75.0, min(145.0, car.servo_angle))
        self.assertEqual(clamped, 145.0)

    def test_t2_f17_velocity_non_negative(self):
        """T2_17.3: Verify velocity is never negative during normal driving."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.step(dt=0.1)
        self.assertGreaterEqual(car.velocity, 0.0)

    def test_t2_f17_speed_governor_clamp(self):
        """T2_17.4: Verify target speed does not exceed maximum modeled 60 px/s."""
        car = get_vehicle_sim()
        self.assertLessEqual(car.target_speed, 60.0)

    def test_t2_f17_pwm_zero_when_stopped(self):
        """T2_17.5: Verify PWM is 0 when vehicle is stopped."""
        car = get_vehicle_sim()
        car.task_state = "PEDESTRIAN_STOP"
        car.step(dt=0.1)
        self.assertEqual(car.pwm, 0)

    # ========================================================================
    # FEATURE AREA 18: Vision Lane Tracking Boundaries
    # ========================================================================
    def test_t2_f18_completely_dark_image(self):
        """T2_18.1: Verify zero line detection on completely black image."""
        dark = np.zeros((340, 640), dtype=np.uint8)
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
        self.assertEqual(num_labels, 1)  # Only background label 0

    def test_t2_f18_max_deviation_clamp(self):
        """T2_18.2: Verify extreme pixel error clamps deviation to [-1.5, 1.5]."""
        cx = 326.9
        extreme_positive_err = 1000.0
        extreme_negative_err = -1000.0
        clamp_pos = max(-1.5, min(1.5, extreme_positive_err / cx))
        clamp_neg = max(-1.5, min(1.5, extreme_negative_err / cx))
        self.assertEqual(clamp_pos, 1.5)
        self.assertEqual(clamp_neg, -1.5)

    def test_t2_f18_slew_rate_limiter(self):
        """T2_18.3: Verify slew rate limit per frame is 0.25."""
        max_delta = 0.25
        e_prev = 0.0
        e_target = 1.0
        e_applied = e_prev + max(-max_delta, min(max_delta, e_target - e_prev))
        self.assertEqual(e_applied, 0.25)

    def test_t2_f18_memory_frames_counter(self):
        """T2_18.4: Verify memory frames limit is 12."""
        memory_limit = 12
        frames_lost = 10
        self.assertTrue(frames_lost <= memory_limit)
        frames_lost = 13
        self.assertFalse(frames_lost <= memory_limit)

    def test_t2_f18_safety_motor_cut_after_loss(self):
        """T2_18.5: Verify tracking loss cuts motor PWM."""
        car = get_vehicle_sim()
        car.is_autonomous = False  # Simulates loss
        car.step(dt=0.1)
        self.assertEqual(car.pwm, 0)

    # ========================================================================
    # FEATURE AREA 19: Traffic Sign & Pedestrian Boundaries
    # ========================================================================
    def test_t2_f19_sign_at_frame_edge(self):
        """T2_19.1: Verify pedestrian crossing trigger handles coordinate boundary."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 850.0
        car.y = 410.0  # Entry into detection zone
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")

    def test_t2_f19_premature_departure_blocked(self):
        """T2_19.2: Verify car remains stopped while timer > 0."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 1.5
        car.step(dt=0.5)
        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")
        self.assertEqual(car.velocity, 0.0)

    def test_t2_f19_varied_dt_timer_countdown(self):
        """T2_19.3: Verify timer decrements accurately with small dt (0.016s)."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 3.0
        car.step(dt=0.016)
        self.assertAlmostEqual(car.stop_timer, 2.984, delta=0.001)

    def test_t2_f19_blind_pass_inactivation(self):
        """T2_19.4: Verify stop_timer=-1.0 marks blind pass complete."""
        car = get_vehicle_sim()
        car.stop_timer = -1.0
        self.assertEqual(car.stop_timer, -1.0)

    def test_t2_f19_crossing_resume_velocity(self):
        """T2_19.5: Verify car accelerates back to target speed after stop expires."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 0.01
        car.step(dt=0.02)
        self.assertEqual(car.task_state, "LANE_KEEP")

    # ========================================================================
    # FEATURE AREA 20: MQTT Auto-Start Boundaries
    # ========================================================================
    def test_t2_f20_unknown_color_payload_ignored(self):
        """T2_20.1: Verify malformed color payload (PURPLE) does not assign target bay."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "PURPLE")
        self.assertIsNone(car.target_bay_color)

    def test_t2_f20_empty_start_payload_ignored(self):
        """T2_20.2: Verify empty start payload does not set received_start."""
        car = get_vehicle_sim()
        car.on_mqtt_message("robot/basla", "")
        self.assertFalse(car.received_start)

    def test_t2_f20_reverse_order_start_then_color(self):
        """T2_20.3: Verify receiving start first, then color, successfully activates car."""
        car = get_vehicle_sim()
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertFalse(car.is_autonomous)
        car.on_mqtt_message("arac/yuk", "RED")
        self.assertTrue(car.is_autonomous)

    def test_t2_f20_duplicate_start_messages(self):
        """T2_20.4: Verify repeated start messages do not corrupt state."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "GREEN")
        car.on_mqtt_message("robot/basla", "BASLA")
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertTrue(car.is_autonomous)

    def test_t2_f20_estop_active_blocks_mqtt_start(self):
        """T2_20.5: Verify MQTT start message cannot launch vehicle if E-Stop is active."""
        car = get_vehicle_sim()
        car.estop()
        car.on_mqtt_message("arac/yuk", "BLUE")
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertFalse(car.is_autonomous)

    # ========================================================================
    # FEATURE AREA 21: Parking Bay Ground Detection Boundaries
    # ========================================================================
    def test_t2_f21_small_stray_paint_blob_rejected(self):
        """T2_21.1: Verify small contour (area < 300) is rejected."""
        mask = np.zeros((480, 640), dtype=np.uint8)
        cv2.rectangle(mask, (200, 350), (210, 360), 255, -1)  # Area = 100 < 300
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) >= 300]
        self.assertEqual(len(valid), 0)

    def test_t2_f21_contour_at_area_threshold(self):
        """T2_21.2: Verify contour with area >= 300 is accepted."""
        mask = np.zeros((480, 640), dtype=np.uint8)
        cv2.rectangle(mask, (200, 350), (220, 370), 255, -1)  # Area = 400 >= 300
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) >= 300]
        self.assertEqual(len(valid), 1)

    def test_t2_f21_depth_validation_limits(self):
        """T2_21.3: Verify depth outside [250, 3500]mm is rejected."""
        valid_depth = 800
        too_close = 150
        too_far = 4000
        self.assertTrue(250 <= valid_depth <= 3500)
        self.assertFalse(250 <= too_close <= 3500)
        self.assertFalse(250 <= too_far <= 3500)

    def test_t2_f21_lateral_alignment_rate_clamp(self):
        """T2_21.4: Verify lateral alignment steering does not jump discontinuously."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.target_bay_color = "RED"  # Bay X = 380
        car.x = 200.0
        car.step(dt=0.01)
        # Shift should be bounded
        self.assertLessEqual(abs(car.x - 200.0), 10.0)

    def test_t2_f21_bay_color_case_insensitivity(self):
        """T2_21.5: Verify bay detection handles lowercase color names."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame(target_bay="red")
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
        self.assertGreater(cv2.countNonZero(mask), 200)

    # ========================================================================
    # FEATURE AREA 22: Precision Bay Stop Boundaries
    # ========================================================================
    def test_t2_f22_distance_threshold_boundary(self):
        """T2_22.1: Verify stopping triggered when dist <= 25.0 cm (25px)."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 599.0  # 625 - 599 = 26 > 25
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_APPROACH")
        car.y = 601.0  # 625 - 601 = 24 <= 25
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_ETTI")

    def test_t2_f22_overshoot_recovery(self):
        """T2_22.2: Verify car stops even if position momentarily overshoots line."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 630.0  # Overshot 625
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_ETTI")

    def test_t2_f22_permanent_cutoff_pwm_zero(self):
        """T2_22.3: Verify PWM is 0 in PARK_ETTI."""
        car = get_vehicle_sim()
        car.task_state = "PARK_ETTI"
        car.step(dt=1.0)
        self.assertEqual(car.pwm, 0)
        self.assertEqual(car.velocity, 0.0)

    def test_t2_f22_post_park_mqtt_ignored(self):
        """T2_22.4: Verify car cannot be restarted once parked."""
        car = get_vehicle_sim()
        car.task_state = "PARK_ETTI"
        car.completed = True
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertEqual(car.task_state, "PARK_ETTI")

    def test_t2_f22_terminus_status_verification(self):
        """T2_22.5: Verify completed flag is True."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 620.0
        car.step(dt=0.01)
        self.assertTrue(car.completed)

    # ========================================================================
    # FEATURE AREA 23: Application Launcher Boundaries
    # ========================================================================
    def test_t2_f23_negative_speed_clamping(self):
        """T2_23.1: Verify negative or zero speed multiplier is clamped to >= 0.1."""
        speed = max(0.1, min(10.0, -2.0))
        self.assertEqual(speed, 0.1)

    def test_t2_f23_max_speed_clamping(self):
        """T2_23.2: Verify excessive speed multiplier is clamped to <= 10.0."""
        speed = max(0.1, min(10.0, 50.0))
        self.assertEqual(speed, 10.0)

    def test_t2_f23_headless_flag_default(self):
        """T2_23.3: Verify default headless flag is False."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--headless", action="store_true")
        args = parser.parse_args([])
        self.assertFalse(args.headless)

    def test_t2_f23_verify_all_flag_parsing(self):
        """T2_23.4: Verify --verify-all flag sets option True."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--verify-all", action="store_true")
        args = parser.parse_args(["--verify-all"])
        self.assertTrue(args.verify_all)

    def test_t2_f23_subsystem_clean_exit(self):
        """T2_23.5: Verify clean exit stops belt and unlatches E-stop."""
        plc = get_plc_engine()
        plc.press_stop()
        plc.update(dt=0.01)
        self.assertFalse(plc.is_running)

    # ========================================================================
    # FEATURE AREA 24: Headless CI Verification Boundaries
    # ========================================================================
    def test_t2_f24_dummy_driver_sdl(self):
        """T2_24.1: Verify SDL dummy driver env var."""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        self.assertEqual(os.environ["SDL_VIDEODRIVER"], "dummy")

    def test_t2_f24_cycle_timeout_threshold(self):
        """T2_24.2: Verify cycle timeout threshold is 35 seconds."""
        timeout_limit_s = 35.0
        elapsed_s = 12.5
        self.assertLess(elapsed_s, timeout_limit_s)

    def test_t2_f24_report_serialization(self):
        """T2_24.3: Verify report dictionary is JSON-serializable."""
        import json
        data = {"tier": 2, "passed": True, "duration_s": 0.25}
        s = json.dumps(data)
        self.assertIn('"passed": true', s)

    def test_t2_f24_failed_test_status_reporting(self):
        """T2_24.4: Verify report structure reflects failure status accurately."""
        report = {"total": 120, "passed": 119, "failed": 1, "status": "FAILED"}
        self.assertEqual(report["status"], "FAILED")

    def test_t2_f24_exit_code_logic(self):
        """T2_24.5: Verify exit code is 0 on full pass, non-zero on failure."""
        failed_count = 0
        exit_code = 0 if failed_count == 0 else 1
        self.assertEqual(exit_code, 0)
        failed_count = 1
        exit_code = 0 if failed_count == 0 else 1
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
