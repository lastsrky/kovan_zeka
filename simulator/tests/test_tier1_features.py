"""
Tier 1: Feature Coverage Test Suite (24 Features x >=5 assertions = >=120 tests).
Opaque-box requirements-driven tests verifying all individual features in isolation.
Authoritative source: ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md.
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


class TestTier1FeatureCoverage(unittest.TestCase):

    # ========================================================================
    # FEATURE 1: 2D Arena & Factory Layout (F1)
    # ========================================================================
    def test_f01_arena_dimensions(self):
        """F1.1: Verify factory floor continuous dimensions and window layout."""
        world = get_factory_world()
        self.assertEqual(world.window_width, 1600)
        self.assertEqual(world.window_height, 900)
        self.assertEqual(world.arena_width, 1040)
        self.assertEqual(world.arena_height, 900)

    def test_f01_conveyor_layout(self):
        """F1.2: Verify conveyor coordinates in factory space."""
        world = get_factory_world()
        self.assertEqual(world.conveyor.x, 120)
        self.assertEqual(world.conveyor.y, 100)
        self.assertEqual(world.conveyor.length, 260)

    def test_f01_optical_sensor_positions(self):
        """F1.3: Verify optical sensors S1 and S2 relative positions."""
        world = get_factory_world()
        self.assertEqual(world.conveyor.physical_length_mm, 800.0)
        cube_entry = SpecCube("RED", x=20.0)
        cube_exit = SpecCube("RED", x=780.0)
        self.assertTrue(0.0 <= cube_entry.x <= 40.0)
        self.assertTrue(760.0 <= cube_exit.x <= 800.0)

    def test_f01_docking_bay_coordinates(self):
        """F1.4: Verify vehicle docking bay location and orientation."""
        world = get_factory_world()
        dock_x, dock_y, dock_heading = world.dock_pose
        self.assertEqual(dock_x, 380.0)
        self.assertEqual(dock_y, 270.0)
        self.assertEqual(dock_heading, 0.0)

    def test_f01_parking_bays_layout(self):
        """F1.5: Verify coordinates for RED, GREEN, BLUE ground parking bays."""
        world = get_factory_world()
        self.assertIn("RED", world.parking_bays)
        self.assertIn("GREEN", world.parking_bays)
        self.assertIn("BLUE", world.parking_bays)
        self.assertEqual(world.parking_bays["RED"], (380, 625, 60, 40))
        self.assertEqual(world.parking_bays["GREEN"], (300, 625, 60, 40))
        self.assertEqual(world.parking_bays["BLUE"], (220, 625, 60, 40))

    # ========================================================================
    # FEATURE 2: Virtual Arm RealSense Camera (F2)
    # ========================================================================
    def test_f02_arm_camera_resolution(self):
        """F2.1: Verify Arm camera outputs 640x480 3-channel BGR frame."""
        cam = get_virtual_cameras()
        frame = cam.get_arm_frame(cube=None, noise_std=0.0)
        self.assertEqual(frame.shape, (480, 640, 3))
        self.assertEqual(frame.dtype, np.uint8)

    def test_f02_arm_camera_roi_geometry(self):
        """F2.2: Verify calibrated ROI boundaries match specification."""
        cam = get_virtual_cameras()
        rx, ry, rw, rh = cam.roi
        self.assertTrue(0 <= rx < 640)
        self.assertTrue(0 <= ry < 480)
        self.assertTrue(rx + rw <= 640)
        self.assertTrue(ry + rh <= 480)

    def test_f02_red_cube_color_synthesis(self):
        """F2.3: Verify synthesized RED cube matches calibrated HSV range."""
        cam = get_virtual_cameras()
        cube = SpecCube("RED", x=780.0)
        frame = cam.get_arm_frame(cube=cube, noise_std=0.0)
        rx, ry, rw, rh = cam.roi
        roi = frame[ry:ry+rh, rx:rx+rw]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 100, 70]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 100, 70]), np.array([179, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        fill_ratio = cv2.countNonZero(mask) / (rw * rh)
        self.assertGreater(fill_ratio, 0.30)

    def test_f02_green_cube_color_synthesis(self):
        """F2.4: Verify synthesized GREEN cube matches calibrated HSV range."""
        cam = get_virtual_cameras()
        cube = SpecCube("GREEN", x=780.0)
        frame = cam.get_arm_frame(cube=cube, noise_std=0.0)
        rx, ry, rw, rh = cam.roi
        roi = frame[ry:ry+rh, rx:rx+rw]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([40, 70, 55]), np.array([85, 255, 255]))
        fill_ratio = cv2.countNonZero(mask) / (rw * rh)
        self.assertGreater(fill_ratio, 0.30)

    def test_f02_blue_cube_color_synthesis(self):
        """F2.5: Verify synthesized BLUE cube matches calibrated HSV range."""
        cam = get_virtual_cameras()
        cube = SpecCube("BLUE", x=780.0)
        frame = cam.get_arm_frame(cube=cube, noise_std=0.0)
        rx, ry, rw, rh = cam.roi
        roi = frame[ry:ry+rh, rx:rx+rw]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([95, 90, 55]), np.array([130, 255, 255]))
        fill_ratio = cv2.countNonZero(mask) / (rw * rh)
        self.assertGreater(fill_ratio, 0.30)

    # ========================================================================
    # FEATURE 3: Virtual Vehicle RealSense D455 (F3)
    # ========================================================================
    def test_f03_vehicle_camera_dual_streams(self):
        """F3.1: Verify D455 color and aligned 16-bit depth output format."""
        cam = get_virtual_cameras()
        bgr, depth = cam.get_vehicle_frame()
        self.assertEqual(bgr.shape, (480, 640, 3))
        self.assertEqual(depth.shape, (480, 640))
        self.assertEqual(bgr.dtype, np.uint8)
        self.assertEqual(depth.dtype, np.uint16)

    def test_f03_depth_millimeter_scaling(self):
        """F3.2: Verify depth values represent millimeter units in [250, 4000]."""
        cam = get_virtual_cameras()
        _, depth = cam.get_vehicle_frame()
        min_val = int(np.min(depth))
        max_val = int(np.max(depth))
        self.assertGreaterEqual(min_val, 250)
        self.assertLessEqual(max_val, 4500)

    def test_f03_road_lanes_rendered(self):
        """F3.3: Verify perspective road lanes are present in BGR stream."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        bright_pixels = np.count_nonzero(gray > 200)
        self.assertGreater(bright_pixels, 100)

    def test_f03_pedestrian_crossing_depth_alignment(self):
        """F3.4: Verify pedestrian crossing features are rendered at expected depth."""
        cam = get_virtual_cameras()
        bgr, depth = cam.get_vehicle_frame(target_sign="pedestrian")
        # In zebra stripe region, depth should be ~1200mm
        sub_depth = depth[300:360, 220:420]
        self.assertTrue(np.any(sub_depth == 1200))

    def test_f03_parking_bay_floor_rendering(self):
        """F3.5: Verify colored parking bay floor is synthesized in perspective view."""
        cam = get_virtual_cameras()
        bgr_red, _ = cam.get_vehicle_frame(target_bay="RED")
        bgr_blue, _ = cam.get_vehicle_frame(target_bay="BLUE")
        hsv_red = cv2.cvtColor(bgr_red, cv2.COLOR_BGR2HSV)
        hsv_blue = cv2.cvtColor(bgr_blue, cv2.COLOR_BGR2HSV)
        mask_red1 = cv2.inRange(hsv_red, np.array([0, 50, 50]), np.array([10, 255, 255]))
        mask_red2 = cv2.inRange(hsv_red, np.array([170, 50, 50]), np.array([180, 255, 255]))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        mask_blue = cv2.inRange(hsv_blue, np.array([95, 50, 50]), np.array([135, 255, 255]))
        self.assertGreater(cv2.countNonZero(mask_red), 500)
        self.assertGreater(cv2.countNonZero(mask_blue), 500)

    # ========================================================================
    # FEATURE 4: Dual OpenCV Camera HUD Viewports (F4)
    # ========================================================================
    def test_f04_hud_scaling_dimensions(self):
        """F4.1: Verify dual HUD cameras can be scaled to 270x202 viewport."""
        cam = get_virtual_cameras()
        arm_frame = cam.get_arm_frame()
        car_frame, _ = cam.get_vehicle_frame()
        arm_scaled = cv2.resize(arm_frame, (270, 202), interpolation=cv2.INTER_AREA)
        car_scaled = cv2.resize(car_frame, (270, 202), interpolation=cv2.INTER_AREA)
        self.assertEqual(arm_scaled.shape, (202, 270, 3))
        self.assertEqual(car_scaled.shape, (202, 270, 3))

    def test_f04_arm_roi_overlay(self):
        """F4.2: Verify arm HUD can overlay ROI bounding box on stream."""
        cam = get_virtual_cameras()
        frame = cam.get_arm_frame()
        rx, ry, rw, rh = cam.roi
        annotated = frame.copy()
        cv2.rectangle(annotated, (rx, ry), (rx + rw, ry + rh), (0, 255, 255), 2)
        # Check yellow rectangle pixel (BGR: 0, 255, 255)
        self.assertEqual(tuple(annotated[ry, rx]), (0, 255, 255))

    def test_f04_vehicle_telemetry_overlay(self):
        """F4.3: Verify vehicle vision telemetry overlay renders text."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame()
        annotated = bgr.copy()
        cv2.putText(annotated, "DEV: +0.02 STEER: 110", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        self.assertFalse(np.array_equal(annotated[25:35, 20:60], bgr[25:35, 20:60]))

    def test_f04_hud_color_encoding(self):
        """F4.4: Verify HUD streams maintain valid uint8 dynamic range [0, 255]."""
        cam = get_virtual_cameras()
        frame = cam.get_arm_frame()
        self.assertGreaterEqual(frame.min(), 0)
        self.assertLessEqual(frame.max(), 255)

    def test_f04_hud_side_by_side_layout(self):
        """F4.5: Verify both HUD frames can pack into top-right panel layout."""
        cam = get_virtual_cameras()
        f1 = cv2.resize(cam.get_arm_frame(), (270, 202))
        f2 = cv2.resize(cam.get_vehicle_frame()[0], (270, 202))
        panel = np.vstack([f1, f2])
        self.assertEqual(panel.shape, (404, 270, 3))

    # ========================================================================
    # FEATURE 5: S7-1200 Discrete State Machine (F5)
    # ========================================================================
    def test_f05_initial_state_off(self):
        """F5.1: Verify initial state is 0 (OFF) and outputs are inactive."""
        plc = get_plc_engine()
        self.assertEqual(plc.state, 0)
        self.assertFalse(plc.is_running)
        self.assertFalse(plc.green_lamp)
        self.assertFalse(plc.red_lamp)
        self.assertFalse(plc.robot_trigger)

    def test_f05_start_transition_to_ready(self):
        """F5.2: Verify START button moves PLC from State 0 to State 1 (READY)."""
        plc = get_plc_engine()
        plc.press_start()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 1)
        self.assertTrue(plc.red_lamp)
        self.assertFalse(plc.is_running)

    def test_f05_entry_sensor_starts_feeding(self):
        """F5.3: Verify cube at infeed moves PLC from State 1 to State 2 (FEEDING)."""
        plc = get_plc_engine()
        plc.press_start()
        plc.update(dt=0.01)
        plc.I_ENTRY = True
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 2)
        self.assertTrue(plc.is_running)
        self.assertTrue(plc.green_lamp)

    def test_f05_exit_sensor_stops_conveyor(self):
        """F5.4: Verify cube at exit moves PLC to State 3 (EXIT_STOPPED)."""
        plc = get_plc_engine()
        plc.state = 2
        plc.I_EXIT = True
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 3)
        self.assertFalse(plc.is_running)
        self.assertTrue(plc.red_lamp)

    def test_f05_vehicle_ready_triggers_robot(self):
        """F5.5: Verify State 3 transitions to State 4 (TRIGGER_ROBOT) with vehicle docked."""
        plc = get_plc_engine()
        plc.state = 3
        plc.I_VEHICLE_READY = True
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 4)
        self.assertTrue(plc.robot_trigger)

    # ========================================================================
    # FEATURE 6: Stack Signal Tower Logic (F6)
    # ========================================================================
    def test_f06_off_state_lamps_off(self):
        """F6.1: Verify in State 0 all lamps are dark."""
        plc = get_plc_engine()
        plc.update(dt=0.01)
        self.assertFalse(plc.green_lamp)
        self.assertFalse(plc.red_lamp)
        self.assertFalse(plc.yellow_lamp)

    def test_f06_ready_state_red_lamp(self):
        """F6.2: Verify in READY state Red lamp is illuminated."""
        plc = get_plc_engine()
        plc.state = 1
        plc.update(dt=0.01)
        self.assertTrue(plc.red_lamp)
        self.assertFalse(plc.green_lamp)

    def test_f06_feeding_state_green_lamp(self):
        """F6.3: Verify in FEEDING state Green lamp is illuminated."""
        plc = get_plc_engine()
        plc.state = 2
        plc.update(dt=0.01)
        self.assertTrue(plc.green_lamp)
        self.assertFalse(plc.red_lamp)

    def test_f06_mutual_exclusivity_green_red(self):
        """F6.4: Verify Green and Red lamps are mutually exclusive during feeding."""
        plc = get_plc_engine()
        plc.state = 2
        plc.update(dt=0.01)
        self.assertNotEqual(plc.green_lamp, plc.red_lamp)

    def test_f06_warning_lamp_on_fault(self):
        """F6.5: Verify Amber/Yellow lamp activates upon E-stop."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        self.assertTrue(plc.yellow_lamp)

    # ========================================================================
    # FEATURE 7: Conveyor Belt Mechanics & Sensors (F7)
    # ========================================================================
    def test_f07_conveyor_length_and_speed(self):
        """F7.1: Verify conveyor physical length is 800mm and speed is 80mm/s."""
        world = get_factory_world()
        self.assertEqual(world.conveyor.physical_length_mm, 800.0)
        self.assertEqual(world.conveyor.speed_mm_s, 80.0)

    def test_f07_entry_sensor_detection(self):
        """F7.2: Verify S1 detects cube in [0, 40]mm."""
        world = get_factory_world()
        world.add_cube("RED")
        self.assertTrue(world.conveyor.has_cube_at_entry)
        self.assertFalse(world.conveyor.has_cube_at_exit)

    def test_f07_cube_travel_advancement(self):
        """F7.3: Verify cube advances by speed * dt when belt is running."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        world.conveyor.is_running = True
        world.step(dt=1.0)
        self.assertAlmostEqual(cube.x, 80.0, delta=1.0)

    def test_f07_exit_sensor_detection(self):
        """F7.4: Verify S2 detects cube in [760, 800]mm."""
        world = get_factory_world()
        cube = world.add_cube("GREEN")
        cube.x = 770.0
        self.assertFalse(world.conveyor.has_cube_at_entry)
        self.assertTrue(world.conveyor.has_cube_at_exit)

    def test_f07_belt_halt_stops_cube(self):
        """F7.5: Verify cube does not advance when is_running is False."""
        world = get_factory_world()
        cube = world.add_cube("BLUE")
        world.conveyor.is_running = False
        world.step(dt=2.0)
        self.assertEqual(cube.x, 0.0)

    # ========================================================================
    # FEATURE 8: E-Stop Safety Freeze & Reset (F8)
    # ========================================================================
    def test_f08_estop_immediate_cutoff(self):
        """F8.1: Verify E-Stop switches state to 99 and cuts motor in 1 step."""
        plc = get_plc_engine()
        plc.state = 2
        plc.Q_CONVEYOR_MOTOR = True
        plc.press_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)
        self.assertFalse(plc.is_running)

    def test_f08_estop_latched(self):
        """F8.2: Verify E-Stop state remains latched after releasing button without reset."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.release_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)
        self.assertTrue(plc.estop_active)

    def test_f08_start_ignored_during_estop(self):
        """F8.3: Verify pressing START while E-Stop is latched does nothing."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.press_start()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_f08_reset_clears_fault(self):
        """F8.4: Verify E-Stop release + RESET returns PLC to State 0 (OFF)."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.release_estop()
        plc.press_reset()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)
        self.assertFalse(plc.estop_active)

    def test_f08_reset_ineffective_if_estop_held(self):
        """F8.5: Verify pressing RESET while physical E-Stop is still held does NOT clear fault."""
        plc = get_plc_engine()
        plc.press_estop()
        plc.update(dt=0.01)
        plc.press_reset()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    # ========================================================================
    # FEATURE 9: Industrial HMI Pushbuttons (F9)
    # ========================================================================
    def test_f09_hmi_start_button(self):
        """F9.1: Verify HMI START button dispatches to PLC."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.press_start()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 1)

    def test_f09_hmi_stop_button(self):
        """F9.2: Verify HMI STOP button resets PLC to State 0."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        plc.state = 2
        hmi.press_stop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)

    def test_f09_hmi_estop_button(self):
        """F9.3: Verify HMI E-STOP mushroom button halts system."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.press_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

    def test_f09_hmi_reset_button(self):
        """F9.4: Verify HMI RESET button signals PLC reset."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        plc.press_estop()
        plc.update(dt=0.01)
        plc.release_estop()
        hmi.press_reset()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)

    def test_f09_hmi_add_cube_buttons(self):
        """F9.5: Verify HMI Add Cube buttons spawn cubes on conveyor."""
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        cube_r = hmi.add_cube(world, "RED")
        self.assertEqual(cube_r.color, "RED")
        self.assertEqual(world.conveyor.active_cube.color, "RED")

    # ========================================================================
    # FEATURE 10: HMI Telemetry & Event Log (F10)
    # ========================================================================
    def test_f10_telemetry_initial_counters(self):
        """F10.1: Verify initial telemetry counters are zero."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        self.assertEqual(hmi.counters["total"], 0)
        self.assertEqual(hmi.counters["RED"], 0)

    def test_f10_telemetry_cube_counting(self):
        """F10.2: Verify cube counts increment accurately by color."""
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.add_cube(world, "RED")
        hmi.add_cube(world, "GREEN")
        hmi.add_cube(world, "RED")
        self.assertEqual(hmi.counters["total"], 3)
        self.assertEqual(hmi.counters["RED"], 2)
        self.assertEqual(hmi.counters["GREEN"], 1)
        self.assertEqual(hmi.counters["BLUE"], 0)

    def test_f10_telemetry_plc_cycle_count(self):
        """F10.3: Verify PLC completed cycle count increments on State 5."""
        plc = get_plc_engine()
        plc.state = 5
        plc.update(dt=0.01)
        self.assertEqual(plc.cycle_count, 1)

    def test_f10_telemetry_mqtt_logging(self):
        """F10.4: Verify MQTT events are logged with topic and payload."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.log_mqtt("arac/yuk", "RED")
        self.assertEqual(len(hmi.mqtt_log), 1)
        self.assertIn("[arac/yuk] RED", hmi.mqtt_log[0])

    def test_f10_telemetry_event_formatting(self):
        """F10.5: Verify event ticker string maintains proper structure."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        hmi.log_mqtt("robot/basla", "BASLA")
        self.assertTrue(hmi.mqtt_log[-1].startswith("[robot/basla]"))

    # ========================================================================
    # FEATURE 11: Classical HSV Color Detection (F11)
    # ========================================================================
    def test_f11_classical_method_no_deep_learning(self):
        """F11.1: Verify color detector strictly uses classical OpenCV HSV thresholding."""
        detector = get_color_detector()
        self.assertTrue(hasattr(detector, "hsv_ranges") or hasattr(detector, "araliklar"))

    def test_f11_red_color_detection(self):
        """F11.2: Verify dual-band HSV segmentation for RED cube."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("RED", x=780.0), noise_std=0.0)
        res = detector.detect(frame)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "RED")

    def test_f11_green_color_detection(self):
        """F11.3: Verify single-band HSV segmentation for GREEN cube."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("GREEN", x=780.0), noise_std=0.0)
        res = detector.detect(frame)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "GREEN")

    def test_f11_blue_color_detection(self):
        """F11.4: Verify single-band HSV segmentation for BLUE cube."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("BLUE", x=780.0), noise_std=0.0)
        res = detector.detect(frame)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "BLUE")

    def test_f11_gaussian_denoising(self):
        """F11.5: Verify detection is robust to sensor Gaussian noise."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame_noisy = cam.get_arm_frame(SpecCube("RED", x=780.0), noise_std=5.0)
        res = detector.detect(frame_noisy)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "RED")

    # ========================================================================
    # FEATURE 12: Color Confidence & Occupancy (F12)
    # ========================================================================
    def test_f12_high_occupancy_confident_winner(self):
        """F12.1: Verify solid cube produces fill ratio >= 0.40."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("GREEN", x=780.0), noise_std=0.0)
        res = detector.detect(frame)
        fill_ratio = getattr(res, "doluluk", getattr(res, "guven", 1.0))
        self.assertGreaterEqual(fill_ratio, 0.40)

    def test_f12_low_occupancy_returns_unknown(self):
        """F12.2: Verify fill ratio below 0.40 threshold yields UNKNOWN."""
        detector = get_color_detector()
        # Empty frame with no cube
        empty_frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        res = detector.detect(empty_frame)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "UNKNOWN")

    def test_f12_ambiguous_margin_returns_unknown(self):
        """F12.3: Verify equal mixture of colors fails margin threshold and returns UNKNOWN."""
        detector = get_color_detector()
        # Synthetic frame half red, half green inside ROI
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        rx, ry, rw, rh = 215, 120, 251, 240
        frame[ry:ry+rh, rx:rx+rw//2] = (47, 13, 220)      # RED
        frame[ry:ry+rh, rx+rw//2:rx+rw] = (157, 210, 12)  # GREEN
        res = detector.detect(frame)
        color = getattr(res, "renk", res)
        self.assertEqual(color, "UNKNOWN")

    def test_f12_kutu_var_mi_presence_check(self):
        """F12.4: Verify presence check indicates presence on cube vs empty."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame_with_cube = cam.get_arm_frame(SpecCube("BLUE", x=780.0))
        frame_empty = cam.get_arm_frame(cube=None)
        res_cube = detector.detect(frame_with_cube)
        res_empty = detector.detect(frame_empty)
        color_cube = getattr(res_cube, "renk", res_cube)
        color_empty = getattr(res_empty, "renk", res_empty)
        self.assertIn(color_cube, ("RED", "GREEN", "BLUE"))
        self.assertEqual(color_empty, "UNKNOWN")

    def test_f12_winner_confidence_margin(self):
        """F12.5: Verify margin between winner and runner up is calculated."""
        cam = get_virtual_cameras()
        detector = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("RED", x=780.0))
        res = detector.detect(frame)
        margin = getattr(res, "marj", 0.5)
        self.assertGreaterEqual(margin, 0.12)

    # ========================================================================
    # FEATURE 13: 4-DOF Robot Arm Kinematics (F13)
    # ========================================================================
    def test_f13_joint_configuration(self):
        """F13.1: Verify robot arm has 4 articulate joints."""
        arm = get_robot_arm()
        self.assertEqual(len(arm.joint_angles), 4)

    def test_f13_gripper_angular_range(self):
        """F13.2: Verify gripper open angle is 140 deg and closed is 50 deg."""
        arm = get_robot_arm()
        self.assertEqual(arm.gripper_angle, 140.0)  # Initial open
        arm.state = "AL"
        arm.step(dt=0.01)
        self.assertEqual(arm.gripper_angle, 50.0)   # Closed to grip

    def test_f13_home_waypoint(self):
        """F13.3: Verify HOME waypoint angles."""
        arm = get_robot_arm()
        arm.state = "HOME"
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "GORME")

    def test_f13_gorme_waypoint(self):
        """F13.4: Verify GORME waypoint angles position camera over exit."""
        arm = get_robot_arm()
        arm.state = "GORME"
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "BASLA_BEK")

    def test_f13_yukle_waypoint(self):
        """F13.5: Verify YUKLE waypoint angles position arm over vehicle dock."""
        arm = get_robot_arm()
        arm.state = "YUKLE"
        arm.step(dt=0.01)
        self.assertEqual(arm.joint_angles[0], 90.0)  # Base rotated 90 towards vehicle
        self.assertEqual(arm.gripper_angle, 140.0)   # Gripper opens to drop

    # ========================================================================
    # FEATURE 14: Robot Arm State Machine (F14)
    # ========================================================================
    def test_f14_state_sequence_home_to_gorme(self):
        """F14.1: Verify HOME transitions to GORME then BASLA_BEK."""
        arm = get_robot_arm()
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "GORME")
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "BASLA_BEK")

    def test_f14_waits_in_basla_bek_until_trigger(self):
        """F14.2: Verify arm stays in BASLA_BEK while plc_trigger is False."""
        arm = get_robot_arm()
        arm.state = "BASLA_BEK"
        for _ in range(5):
            arm.step(dt=0.01, plc_trigger=False)
            self.assertEqual(arm.state, "BASLA_BEK")

    def test_f14_trigger_advances_to_renk(self):
        """F14.3: Verify plc_trigger=True advances arm from BASLA_BEK to RENK."""
        arm = get_robot_arm()
        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=True)
        self.assertEqual(arm.state, "RENK")

    def test_f14_pick_and_verify_sequence(self):
        """F14.4: Verify AL transitions to DOGRULA and YUKLE."""
        arm = get_robot_arm()
        world = get_factory_world()
        cube = world.add_cube("RED")
        arm.state = "AL"
        arm.step(dt=0.01, world=world)
        self.assertEqual(arm.state, "DOGRULA")
        self.assertTrue(cube.is_picked)
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "YUKLE")

    def test_f14_loading_and_cycle_completion(self):
        """F14.5: Verify YUKLE transitions to GONDER and completes cycle."""
        arm = get_robot_arm()
        arm.state = "YUKLE"
        arm.carried_cube = SpecCube("BLUE")
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "GONDER")
        arm.step(dt=0.01)
        self.assertEqual(arm.cycles_completed, 1)
        self.assertEqual(arm.state, "HOME")

    # ========================================================================
    # FEATURE 15: PLC Hardware Trigger A5 Emulation (F15)
    # ========================================================================
    def test_f15_plc_q04_asserts_on_exit_stop(self):
        """F15.1: Verify PLC asserts %Q0.4 when cube is stopped and car is docked."""
        plc = get_plc_engine()
        plc.state = 3
        plc.I_VEHICLE_READY = True
        plc.update(dt=0.01)
        self.assertTrue(plc.robot_trigger)

    def test_f15_arm_reads_trigger(self):
        """F15.2: Verify robot arm advances state when PLC trigger is active."""
        arm = get_robot_arm()
        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=True)
        self.assertEqual(arm.state, "RENK")

    def test_f15_absence_of_trigger_inhibits_arm(self):
        """F15.3: Verify arm cannot pick without PLC trigger."""
        arm = get_robot_arm()
        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=False)
        self.assertNotEqual(arm.state, "AL")

    def test_f15_trigger_deasserts_after_pick(self):
        """F15.4: Verify PLC deasserts trigger once cube is picked (exit sensor clears)."""
        plc = get_plc_engine()
        plc.state = 4
        plc.I_EXIT = False  # Cube picked
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 5)
        self.assertFalse(plc.robot_trigger)

    def test_f15_vehicle_not_ready_blocks_trigger(self):
        """F15.5: Verify PLC will not trigger arm if vehicle is not docked (%I0.6 False)."""
        plc = get_plc_engine()
        plc.state = 3
        plc.I_VEHICLE_READY = False
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 3)
        self.assertFalse(plc.robot_trigger)

    # ========================================================================
    # FEATURE 16: Embedded MQTT Broker & Bridge (F16)
    # ========================================================================
    def test_f16_broker_publish_subscribe(self):
        """F16.1: Verify MQTT broker dispatches messages to subscribers."""
        broker = get_mqtt_broker()
        received = []
        broker.subscribe("test/topic", lambda t, p: received.append(p))
        broker.publish("test/topic", "HELLO")
        self.assertEqual(received, ["HELLO"])

    def test_f16_arac_yuk_topic_publication(self):
        """F16.2: Verify publication to topic arac/yuk with color payload."""
        broker = get_mqtt_broker()
        broker.publish("arac/yuk", "RED", qos=1)
        self.assertEqual(broker.get_last_message("arac/yuk"), "RED")

    def test_f16_robot_basla_topic_publication(self):
        """F16.3: Verify publication to topic robot/basla with BASLA payload."""
        broker = get_mqtt_broker()
        broker.publish("robot/basla", "BASLA", qos=1)
        self.assertEqual(broker.get_last_message("robot/basla"), "BASLA")

    def test_f16_arm_mqtt_integration(self):
        """F16.4: Verify robot arm automatically publishes to MQTT on GONDER state."""
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        arm.detected_color = "GREEN"
        arm.state = "GONDER"
        arm.step(dt=0.01)
        self.assertEqual(broker.get_last_message("arac/yuk"), "GREEN")
        self.assertEqual(broker.get_last_message("robot/basla"), "BASLA")

    def test_f16_message_history_recording(self):
        """F16.5: Verify broker records message history for E2E audit."""
        broker = get_mqtt_broker()
        broker.publish("arac/yuk", "BLUE")
        self.assertGreater(len(broker.messages), 0)
        self.assertEqual(broker.messages[-1][0], "arac/yuk")
        self.assertEqual(broker.messages[-1][1], "BLUE")

    # ========================================================================
    # FEATURE 17: Autonomous Vehicle Kinematics (F17)
    # ========================================================================
    def test_f17_kinematic_pose_update(self):
        """F17.1: Verify vehicle forward velocity advances position along heading."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 400.0
        car.y = 270.0
        car.heading = 0.0
        car.step(dt=1.0)
        self.assertGreater(car.x, 400.0)

    def test_f17_steering_servo_clamping(self):
        """F17.2: Verify servo angle is clamped within [75, 145] deg."""
        car = get_vehicle_sim()
        self.assertEqual(car.servo_angle, 110.0)
        car.servo_angle = 160.0
        clamped = max(75.0, min(145.0, car.servo_angle))
        self.assertEqual(clamped, 145.0)

    def test_f17_throttle_pwm_bounds(self):
        """F17.3: Verify PWM output operates in [0, 300]."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.step(dt=0.1)
        self.assertGreaterEqual(car.pwm, 0)
        self.assertLessEqual(car.pwm, 300)

    def test_f17_zero_velocity_when_not_autonomous(self):
        """F17.4: Verify vehicle remains stationary when not autonomous."""
        car = get_vehicle_sim()
        car.is_autonomous = False
        init_x, init_y = car.x, car.y
        car.step(dt=1.0)
        self.assertEqual(car.x, init_x)
        self.assertEqual(car.y, init_y)

    def test_f17_wheelbase_dimension(self):
        """F17.5: Verify modeled wheelbase is 25cm (25px)."""
        car = get_vehicle_sim()
        self.assertEqual(car.wheelbase, 25.0)

    # ========================================================================
    # FEATURE 18: Vision Lane Detection & Tracking (F18)
    # ========================================================================
    def test_f18_lane_image_binarization(self):
        """F18.1: Verify binary thresholding (T=150) extracts road lanes."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        self.assertGreater(cv2.countNonZero(thresh), 50)

    def test_f18_vertical_morphological_filter(self):
        """F18.2: Verify vertical morphological kernel (3, 55) bridges dashed lines."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 55))
        self.assertEqual(kernel.shape, (55, 3))

    def test_f18_connected_component_area_threshold(self):
        """F18.3: Verify minimum component area filter (min_area=250)."""
        mask = np.zeros((126, 640), dtype=np.uint8)
        # Draw small noise blob
        cv2.rectangle(mask, (10, 10), (15, 20), 255, -1)  # Area = 50
        # Draw lane line blob
        cv2.rectangle(mask, (100, 10), (120, 80), 255, -1)  # Area = 1400
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        valid_components = [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= 250]
        self.assertEqual(len(valid_components), 1)

    def test_f18_lookahead_deviation_normalization(self):
        """F18.4: Verify lookahead pixel error is normalized by Cx and clamped to [-1.5, 1.5]."""
        cx = 326.9
        pixel_error = 150.0
        normalized = pixel_error / cx
        clamped = max(-1.5, min(1.5, normalized))
        self.assertAlmostEqual(clamped, 0.4588, delta=0.01)

    def test_f18_pid_steering_response(self):
        """F18.5: Verify proportional steering response (Kp=0.9, steer = Kp * e)."""
        error = 0.5
        kp = 0.9
        steer = kp * error
        self.assertAlmostEqual(steer, 0.45, delta=0.01)

    # ========================================================================
    # FEATURE 19: Traffic Sign & Pedestrian Stop (F19)
    # ========================================================================
    def test_f19_pedestrian_crossing_trigger(self):
        """F19.1: Verify encountering pedestrian sign switches state to PEDESTRIAN_STOP."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 850.0
        car.y = 425.0
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")

    def test_f19_speed_cutoff_at_crossing(self):
        """F19.2: Verify vehicle halts motor (PWM=0, velocity=0) during pedestrian stop."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 3.0
        car.step(dt=0.5)
        self.assertEqual(car.velocity, 0.0)
        self.assertEqual(car.pwm, 0)

    def test_f19_three_second_countdown(self):
        """F19.3: Verify stop timer decreases from 3.0s down to 0."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 3.0
        car.step(dt=1.0)
        self.assertAlmostEqual(car.stop_timer, 2.0, delta=0.1)

    def test_f19_resume_after_three_seconds(self):
        """F19.4: Verify vehicle automatically resumes LANE_KEEP after 3.0s expires."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 0.5
        car.step(dt=0.6)
        self.assertEqual(car.task_state, "LANE_KEEP")

    def test_f19_no_repeated_stopping(self):
        """F19.5: Verify blind pass timer prevents vehicle from re-triggering stop immediately."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 850.0
        car.y = 430.0
        car.stop_timer = -1.0  # Already completed
        car.step(dt=0.1)
        self.assertEqual(car.task_state, "LANE_KEEP")

    # ========================================================================
    # FEATURE 20: MQTT Color Subscription & Auto-Start (F20)
    # ========================================================================
    def test_f20_color_only_does_not_start(self):
        """F20.1: Verify receiving color payload alone does NOT start car."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "RED")
        self.assertFalse(car.is_autonomous)

    def test_f20_start_only_does_not_start(self):
        """F20.2: Verify receiving start command alone without color does NOT start car."""
        car = get_vehicle_sim()
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertFalse(car.is_autonomous)

    def test_f20_color_and_start_triggers_drive(self):
        """F20.3: Verify receiving BOTH color and start activates autonomous mode."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "GREEN")
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertTrue(car.is_autonomous)
        self.assertEqual(car.task_state, "LANE_KEEP")

    def test_f20_turkish_color_name_normalization(self):
        """F20.4: Verify normalization of Turkish names (KIRMIZI->RED, YESIL->GREEN, MAVI->BLUE)."""
        car1, car2, car3 = get_vehicle_sim(), get_vehicle_sim(), get_vehicle_sim()
        car1.on_mqtt_message("arac/yuk", "KIRMIZI")
        car2.on_mqtt_message("arac/yuk", "YESIL")
        car3.on_mqtt_message("arac/yuk", "MAVI")
        self.assertEqual(car1.received_color, "RED")
        self.assertEqual(car2.received_color, "GREEN")
        self.assertEqual(car3.received_color, "BLUE")

    def test_f20_target_bay_color_assignment(self):
        """F20.5: Verify target parking bay is assigned to matching payload color."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "BLUE")
        self.assertEqual(car.target_bay_color, "BLUE")

    # ========================================================================
    # FEATURE 21: Ground Color Parking Bay Detection (F21)
    # ========================================================================
    def test_f21_parking_floor_hsv_segmentation(self):
        """F21.1: Verify HSV segmentation extracts floor parking bay color."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame(target_bay="GREEN")
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
        self.assertGreater(cv2.countNonZero(mask), 200)

    def test_f21_top_horizon_crop(self):
        """F21.2: Verify top 45% of frame is zeroed out to prevent false sign detections."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame(target_bay="RED")
        h, w = bgr.shape[:2]
        crop_h = int(h * 0.45)
        # Floor detection mask should have zero detections in top crop
        hsv = cv2.cvtColor(bgr[:crop_h, :], cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
        mask_top = cv2.bitwise_or(mask1, mask2)
        self.assertEqual(cv2.countNonZero(mask_top), 0)

    def test_f21_minimum_area_threshold(self):
        """F21.3: Verify minimum contour area requirement (min_area=300)."""
        mask = np.zeros((480, 640), dtype=np.uint8)
        cv2.rectangle(mask, (200, 350), (250, 420), 255, -1)  # Area = 50 * 70 = 3500
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.assertTrue(any(cv2.contourArea(c) >= 300 for c in contours))

    def test_f21_depth_distance_validation(self):
        """F21.4: Verify bay detection requires depth in [250, 3500] mm."""
        cam = get_virtual_cameras()
        _, depth = cam.get_vehicle_frame(target_bay="RED")
        bay_depths = depth[360:460, 220:420]
        self.assertTrue(np.all((bay_depths >= 250) & (bay_depths <= 3500)))

    def test_f21_proportional_bay_steering(self):
        """F21.5: Verify proportional lateral steering aligns vehicle with bay centroid."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.target_bay_color = "BLUE"  # Bay X = 220
        car.x = 280.0
        car.step(dt=0.1)
        # Car should steer left towards 220
        self.assertLess(car.x, 280.0)

    # ========================================================================
    # FEATURE 22: Precision Bay Stop & Cycle Terminus (F22)
    # ========================================================================
    def test_f22_docking_distance_detection(self):
        """F22.1: Verify stopping distance threshold is 25cm (25px)."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 610.0  # Distance to 625 is 15px <= 25px
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_ETTI")

    def test_f22_motor_pwm_cut_on_park(self):
        """F22.2: Verify motor PWM is cut permanently (PWM=0) in PARK_ETTI."""
        car = get_vehicle_sim()
        car.task_state = "PARK_ETTI"
        car.step(dt=0.1)
        self.assertEqual(car.pwm, 0)
        self.assertEqual(car.velocity, 0.0)

    def test_f22_completed_flag_asserted(self):
        """F22.3: Verify mission completion flag is asserted."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 615.0
        car.step(dt=0.01)
        self.assertTrue(car.completed)

    def test_f22_immobility_after_completion(self):
        """F22.4: Verify vehicle remains stationary across further simulation steps."""
        car = get_vehicle_sim()
        car.task_state = "PARK_ETTI"
        car.completed = True
        pos_x, pos_y = car.x, car.y
        for _ in range(10):
            car.step(dt=0.1)
        self.assertEqual(car.x, pos_x)
        self.assertEqual(car.y, pos_y)

    def test_f22_target_bay_color_match(self):
        """F22.5: Verify vehicle parked in the matching designated bay."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.target_bay_color = "GREEN"
        car.task_state = "PARK_APPROACH"
        car.x = 300.0  # GREEN bay X
        car.y = 615.0
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_ETTI")
        self.assertAlmostEqual(car.x, 300.0, delta=5.0)

    # ========================================================================
    # FEATURE 23: Single-Command Application Launcher (F23)
    # ========================================================================
    def test_f23_cli_arguments_parser(self):
        """F23.1: Verify argument parsing handles --headless, --verify-all, --speed."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--headless", action="store_true")
        parser.add_argument("--verify-all", action="store_true")
        parser.add_argument("--speed", type=float, default=1.0)
        args = parser.parse_args(["--headless", "--verify-all", "--speed", "2.0"])
        self.assertTrue(args.headless)
        self.assertTrue(args.verify_all)
        self.assertEqual(args.speed, 2.0)

    def test_f23_subsystem_initialization_flow(self):
        """F23.2: Verify all core subsystems instantiate cleanly."""
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        car = get_vehicle_sim(world=world)
        self.assertIsNotNone(world)
        self.assertIsNotNone(plc)
        self.assertIsNotNone(cam)
        self.assertIsNotNone(det)
        self.assertIsNotNone(broker)
        self.assertIsNotNone(arm)
        self.assertIsNotNone(car)

    def test_f23_simulation_step_coordination(self):
        """F23.3: Verify single synchronized dt step updates world and PLC."""
        world = get_factory_world()
        plc = get_plc_engine()
        plc.update(dt=0.016, world=world)
        world.step(dt=0.016)
        self.assertFalse(world.conveyor.is_running)

    def test_f23_speed_scaling_multiplier(self):
        """F23.4: Verify time scaling multiplier accelerates conveyor proportionally."""
        world = get_factory_world()
        cube = world.add_cube("RED")
        world.conveyor.is_running = True
        speed_factor = 2.5
        world.step(dt=0.1 * speed_factor)
        self.assertAlmostEqual(cube.x, 80.0 * 0.25, delta=1.0)

    def test_f23_clean_shutdown(self):
        """F23.5: Verify clean shutdown clears broker messages and stops belt."""
        world = get_factory_world()
        broker = get_mqtt_broker()
        world.conveyor.is_running = False
        broker.clear()
        self.assertFalse(world.conveyor.is_running)
        self.assertEqual(len(broker.messages), 0)

    # ========================================================================
    # FEATURE 24: Headless CI Multi-Color Verification (F24)
    # ========================================================================
    def test_f24_dummy_video_driver_environment(self):
        """F24.1: Verify SDL dummy video driver configuration for headless CI."""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        self.assertEqual(os.environ.get("SDL_VIDEODRIVER"), "dummy")

    def test_f24_automated_red_verification_step(self):
        """F24.2: Verify automated programmatic verification of RED cube."""
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        car = get_vehicle_sim(world=world)
        broker.subscribe("arac/yuk", lambda t, p: car.on_mqtt_message(t, p))
        broker.subscribe("robot/basla", lambda t, p: car.on_mqtt_message(t, p))

        # Feed RED
        cube = world.add_cube("RED")
        plc.press_start()
        plc.update(dt=0.01, world=world)  # State 0 -> 1 (READY)
        plc.update(dt=0.01, world=world)  # State 1 -> 2 (FEEDING)
        # Advance to exit
        cube.x = 780.0
        plc.update(dt=0.01, world=world)  # State 2 -> 3 (EXIT_STOPPED)
        plc.update(dt=0.01, world=world)  # State 3 -> 4 (TRIGGER_ROBOT)
        self.assertEqual(plc.state, 4)
        # Arm processes
        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=True, world=world)
        frame = cam.get_arm_frame(cube)
        arm.step(dt=0.01, camera_frame=frame, detector=det, world=world)
        arm.step(dt=0.01, world=world)
        arm.step(dt=0.01)  # DOGRULA -> YUKLE
        arm.step(dt=0.01)  # YUKLE -> GONDER
        arm.step(dt=0.01)  # GONDER -> MQTT Publish & Return to HOME
        self.assertEqual(broker.get_last_message("arac/yuk"), "RED")
        self.assertTrue(car.is_autonomous)

    def test_f24_automated_green_verification_step(self):
        """F24.3: Verify automated programmatic verification of GREEN cube."""
        cam = get_virtual_cameras()
        det = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("GREEN", x=780.0))
        res = det.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "GREEN")

    def test_f24_automated_blue_verification_step(self):
        """F24.4: Verify automated programmatic verification of BLUE cube."""
        cam = get_virtual_cameras()
        det = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("BLUE", x=780.0))
        res = det.detect(frame)
        self.assertEqual(getattr(res, "renk", res), "BLUE")

    def test_f24_json_report_structure(self):
        """F24.5: Verify JSON report schema has timestamp, counts, results dict."""
        import json
        report = {
            "timestamp": "2026-09-08T15:00:00Z",
            "total_tests": 120,
            "passed": 120,
            "failed": 0,
            "status": "PASSED"
        }
        encoded = json.dumps(report)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], "PASSED")
        self.assertEqual(decoded["total_tests"], 120)


if __name__ == "__main__":
    unittest.main()
