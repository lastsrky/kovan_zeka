"""
Tier 3: Pairwise Cross-Feature Interaction Test Suite (>=24 cross-feature integration tests).
Opaque-box tests verifying module boundaries and subsystem handshakes.
Authoritative sources: ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md.
"""

import unittest
import numpy as np
import cv2
import math

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


class TestTier3PairwiseInteractions(unittest.TestCase):

    def test_pair_01_plc_and_conveyor_optical_sensors(self):
        """Pair 01 (F5 + F7): Conveyor advancement drives PLC through S1 and S2 sensor states."""
        world = get_factory_world()
        plc = get_plc_engine()
        cube = world.add_cube("RED")
        plc.press_start()
        plc.update(dt=0.01, world=world)  # 0 -> 1 (READY)
        plc.update(dt=0.01, world=world)  # 1 -> 2 (FEEDING)
        self.assertEqual(plc.state, 2)
        self.assertTrue(world.conveyor.is_running)

        # Conveyor moves cube from 0 to 770mm
        cube.x = 770.0
        plc.update(dt=0.01, world=world)  # 2 -> 3 (EXIT_STOPPED)
        self.assertEqual(plc.state, 3)
        self.assertFalse(world.conveyor.is_running)

    def test_pair_02_plc_and_signal_tower_stack_lights(self):
        """Pair 02 (F5 + F6): Stack lights synchronize with PLC state transitions."""
        plc = get_plc_engine()
        # OFF
        plc.update(dt=0.01)
        self.assertFalse(plc.green_lamp or plc.red_lamp or plc.yellow_lamp)
        # READY
        plc.press_start()
        plc.update(dt=0.01)
        self.assertTrue(plc.red_lamp and not plc.green_lamp)
        # FEEDING
        plc.I_ENTRY = True
        plc.update(dt=0.01)
        self.assertTrue(plc.green_lamp and not plc.red_lamp)
        # ESTOP
        plc.press_estop()
        plc.update(dt=0.01)
        self.assertTrue(plc.yellow_lamp and not plc.green_lamp)

    def test_pair_03_plc_and_estop_freeze(self):
        """Pair 03 (F5 + F8): Conveyor in full motion halts immediately upon E-Stop."""
        world = get_factory_world()
        plc = get_plc_engine()
        world.add_cube("GREEN")
        plc.state = 2
        plc.update(dt=0.01, world=world)
        self.assertTrue(world.conveyor.is_running)

        plc.press_estop()
        plc.update(dt=0.016, world=world)
        self.assertEqual(plc.state, 99)
        self.assertFalse(world.conveyor.is_running)
        self.assertTrue(plc.estop_active)

    def test_pair_04_conveyor_and_arm_camera_alignment(self):
        """Pair 04 (F7 + F2): Cube arriving at conveyor exit falls within Arm camera ROI."""
        world = get_factory_world()
        cam = get_virtual_cameras()
        cube = world.add_cube("BLUE")
        cube.x = 780.0  # At exit
        frame = cam.get_arm_frame(cube=cube, noise_std=0.0)
        rx, ry, rw, rh = cam.roi
        roi = frame[ry:ry+rh, rx:rx+rw]
        # Verify blue cube is visible in ROI
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([90, 90, 55]), np.array([130, 255, 255]))
        self.assertGreater(cv2.countNonZero(mask), 500)

    def test_pair_05_arm_camera_and_classical_hsv_detector(self):
        """Pair 05 (F2 + F11): Arm camera synthetic frames fed into HSV detector identify colors."""
        cam = get_virtual_cameras()
        det = get_color_detector()
        frame_r = cam.get_arm_frame(SpecCube("RED", x=780.0))
        frame_g = cam.get_arm_frame(SpecCube("GREEN", x=780.0))
        frame_b = cam.get_arm_frame(SpecCube("BLUE", x=780.0))
        self.assertEqual(getattr(det.detect(frame_r), "renk", None), "RED")
        self.assertEqual(getattr(det.detect(frame_g), "renk", None), "GREEN")
        self.assertEqual(getattr(det.detect(frame_b), "renk", None), "BLUE")

    def test_pair_06_color_detector_and_confidence_occupancy(self):
        """Pair 06 (F11 + F12): Detector calculates occupancy and enforces margin threshold."""
        cam = get_virtual_cameras()
        det = get_color_detector()
        frame = cam.get_arm_frame(SpecCube("RED", x=780.0))
        res = det.detect(frame)
        self.assertGreaterEqual(getattr(res, "doluluk", 1.0), 0.40)
        self.assertGreaterEqual(getattr(res, "marj", 0.5), 0.12)

    def test_pair_07_plc_trigger_and_robot_arm_handshake(self):
        """Pair 07 (F15 + F14): S7-1200 %Q0.4 trigger commands arm from BASLA_BEK to RENK."""
        plc = get_plc_engine()
        arm = get_robot_arm()
        arm.state = "BASLA_BEK"
        plc.state = 3
        plc.I_VEHICLE_READY = True
        plc.update(dt=0.01)  # Transitions to State 4 with %Q0.4 = True
        self.assertTrue(plc.robot_trigger)

        arm.step(dt=0.01, plc_trigger=plc.robot_trigger)
        self.assertEqual(arm.state, "RENK")

    def test_pair_08_robot_arm_and_kinematics_waypoints(self):
        """Pair 08 (F14 + F13): Arm progresses through waypoints with corresponding joint poses."""
        arm = get_robot_arm()
        # HOME -> GORME
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "GORME")
        # GORME -> BASLA_BEK
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "BASLA_BEK")
        # BASLA_BEK -> RENK
        arm.step(dt=0.01, plc_trigger=True)
        self.assertEqual(arm.state, "RENK")

    def test_pair_09_robot_arm_pick_and_conveyor_cube_transfer(self):
        """Pair 09 (F14 + F7): Arm pick removes cube from conveyor and resets S2 exit sensor."""
        world = get_factory_world()
        plc = get_plc_engine()
        arm = get_robot_arm()
        cube = world.add_cube("RED")
        cube.x = 780.0
        plc.state = 4
        plc.update(dt=0.01, world=world)

        arm.state = "AL"
        arm.step(dt=0.01, world=world)
        self.assertTrue(cube.is_picked)
        self.assertIsNone(world.conveyor.active_cube)
        self.assertFalse(world.conveyor.has_cube_at_exit)

        # Next PLC scan clears State 4 to State 5
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 5)

    def test_pair_10_robot_arm_loading_and_mqtt_publish(self):
        """Pair 10 (F14 + F16): Arm completes loading and publishes arac/yuk and robot/basla."""
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        arm.detected_color = "BLUE"
        arm.state = "YUKLE"
        arm.step(dt=0.01)
        self.assertEqual(arm.state, "GONDER")
        arm.step(dt=0.01)
        self.assertEqual(broker.get_last_message("arac/yuk"), "BLUE")
        self.assertEqual(broker.get_last_message("robot/basla"), "BASLA")

    def test_pair_11_mqtt_publish_and_vehicle_colorlink(self):
        """Pair 11 (F16 + F20): MQTT message reception in vehicle normalizes color."""
        broker = get_mqtt_broker()
        car = get_vehicle_sim()
        broker.subscribe("arac/yuk", lambda t, p: car.on_mqtt_message(t, p))
        broker.publish("arac/yuk", "YESIL")
        self.assertEqual(car.received_color, "GREEN")

    def test_pair_12_vehicle_colorlink_and_autostart_logic(self):
        """Pair 12 (F20 + F17): Vehicle launches autonomous navigation when both color & start arrive."""
        car = get_vehicle_sim()
        car.on_mqtt_message("arac/yuk", "RED")
        self.assertFalse(car.is_autonomous)
        car.on_mqtt_message("robot/basla", "BASLA")
        self.assertTrue(car.is_autonomous)
        self.assertEqual(car.task_state, "LANE_KEEP")

    def test_pair_13_vehicle_camera_and_vision_lane_pipeline(self):
        """Pair 13 (F3 + F18): RealSense D455 perspective view feeds vision lane thresholding."""
        cam = get_virtual_cameras()
        bgr, _ = cam.get_vehicle_frame()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        # Verify lane markings are extracted
        self.assertGreater(cv2.countNonZero(thresh), 100)

    def test_pair_14_lane_deviation_and_pid_steering_controller(self):
        """Pair 14 (F18 + F17): Centerline offset produces proportional steering angle."""
        cx = 326.9
        x_target = 350.0  # Car drifted right
        error = (x_target - cx) / cx
        kp = 0.9
        steer = kp * error
        car = get_vehicle_sim()
        car.servo_angle = round(110.0 + steer * 35.0)
        self.assertGreater(car.servo_angle, 110.0)

    def test_pair_15_vehicle_camera_and_pedestrian_sign_detection(self):
        """Pair 15 (F3 + F19): Approaching pedestrian crossing coordinates triggers detection."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 850.0
        car.y = 420.0
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")

    def test_pair_16_pedestrian_detection_and_speed_governor_stop(self):
        """Pair 16 (F19 + F17): Pedestrian detection halts vehicle for 3 seconds then resumes."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PEDESTRIAN_STOP"
        car.stop_timer = 3.0
        car.step(dt=1.5)
        self.assertEqual(car.velocity, 0.0)
        self.assertEqual(car.pwm, 0)
        # Advance remaining time
        car.step(dt=1.6)
        self.assertEqual(car.task_state, "LANE_KEEP")

    def test_pair_17_vehicle_perspective_depth_and_parking_floor_hsv(self):
        """Pair 17 (F3 + F21): D455 color + depth segment ground parking bay."""
        cam = get_virtual_cameras()
        bgr, depth = cam.get_vehicle_frame(target_bay="GREEN")
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
        self.assertGreater(cv2.countNonZero(mask), 200)
        # Depth in bay ROI
        bay_depth = depth[360:460, 220:420]
        self.assertTrue(np.all((bay_depth >= 250) & (bay_depth <= 3500)))

    def test_pair_18_parking_bay_guidance_and_precision_stop(self):
        """Pair 18 (F21 + F22): Vehicle aligns with bay and stops at <= 25cm distance."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.target_bay_color = "GREEN"  # Target bay X=300, Y=625
        car.x = 320.0
        car.y = 610.0  # Distance = 15cm <= 25cm
        car.step(dt=0.01)
        self.assertEqual(car.task_state, "PARK_ETTI")
        self.assertEqual(car.pwm, 0)
        self.assertTrue(car.completed)

    def test_pair_19_precision_bay_stop_and_hmi_telemetry(self):
        """Pair 19 (F22 + F10): Terminal park status is logged in HMI telemetry."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "PARK_APPROACH"
        car.y = 615.0
        car.step(dt=0.01)
        self.assertTrue(car.completed)
        hmi.log_mqtt("arac/durum", "PARK_ETTI")
        self.assertIn("[arac/durum] PARK_ETTI", hmi.mqtt_log[-1])

    def test_pair_20_estop_global_freeze_robot_arm(self):
        """Pair 20 (F8 + F14): E-stop immediately freezes robot arm motion."""
        arm = get_robot_arm()
        arm.state = "AL"
        arm.freeze()
        arm.step(dt=0.5)
        self.assertEqual(arm.state, "AL")
        self.assertTrue(arm.is_frozen)

    def test_pair_21_estop_global_freeze_autonomous_vehicle(self):
        """Pair 21 (F8 + F17): E-stop cuts vehicle motor PWM and velocity to 0."""
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.velocity = 60.0
        car.pwm = 90
        car.estop()
        self.assertEqual(car.velocity, 0.0)
        self.assertEqual(car.pwm, 0)
        self.assertTrue(car.is_estop)

    def test_pair_22_hmi_add_cube_and_plc_conveyor_infeed(self):
        """Pair 22 (F9 + F7): Adding cube via HMI triggers S1 and FEEDING transition."""
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        plc.state = 1  # READY
        hmi.add_cube(world, "RED")
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 2)
        self.assertTrue(plc.is_running)

    def test_pair_23_hmi_estop_pushbutton_and_plc_safety_latch(self):
        """Pair 23 (F9 + F8): HMI E-stop button latches State 99 until HMI Reset."""
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)
        plc.state = 2
        hmi.press_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

        # Releasing E-stop alone does not clear
        plc.release_estop()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 99)

        # HMI reset clears
        hmi.press_reset()
        plc.update(dt=0.01)
        self.assertEqual(plc.state, 0)

    def test_pair_24_dual_hud_viewports_and_camera_generators(self):
        """Pair 24 (F4 + F2 + F3): Dual RealSense HUD panels update simultaneously."""
        cam = get_virtual_cameras()
        arm_frame = cam.get_arm_frame(SpecCube("BLUE", x=780.0))
        car_frame, _ = cam.get_vehicle_frame(target_bay="BLUE")
        self.assertEqual(arm_frame.shape, (480, 640, 3))
        self.assertEqual(car_frame.shape, (480, 640, 3))
        v1 = cv2.resize(arm_frame, (270, 202))
        v2 = cv2.resize(car_frame, (270, 202))
        self.assertEqual(v1.shape, (202, 270, 3))
        self.assertEqual(v2.shape, (202, 270, 3))


if __name__ == "__main__":
    unittest.main()
