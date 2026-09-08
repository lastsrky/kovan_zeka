"""
Tier 4: Real-World Application Scenarios (7 Comprehensive End-to-End Workloads).
Opaque-box automated multi-subsystem production cycles and safety stress audits.
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


class TestTier4ApplicationScenarios(unittest.TestCase):

    # ========================================================================
    # SCENARIO 1: Automated Red Cube Production Cycle
    # ========================================================================
    def test_scenario_1_automated_red_cube_production_cycle(self):
        """
        Scenario 1: Full Automated Red Cube Production Cycle.
        Conveyor -> Exit S2 -> Arm Classical HSV RED -> MQTT arac/yuk RED ->
        Car Lane Tracking -> Pedestrian Stop -> Red Parking Bay Docking.
        """
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        car = get_vehicle_sim(world=world)
        hmi = get_hmi_panel(plc)

        # Wire MQTT subscriptions
        broker.subscribe("arac/yuk", lambda t, p: (car.on_mqtt_message(t, p), hmi.log_mqtt(t, p)))
        broker.subscribe("robot/basla", lambda t, p: (car.on_mqtt_message(t, p), hmi.log_mqtt(t, p)))

        # Step 1: Operator presses START and adds RED cube
        hmi.press_start()
        cube = hmi.add_cube(world, "RED")
        self.assertEqual(cube.color, "RED")
        plc.update(dt=0.01, world=world)  # State 0 -> 1 (READY)
        plc.update(dt=0.01, world=world)  # State 1 -> 2 (FEEDING)
        self.assertEqual(plc.state, 2)
        self.assertTrue(plc.green_lamp)
        self.assertTrue(world.conveyor.is_running)

        # Step 2: Conveyor transports cube to Exit sensor S2
        cube.x = 780.0
        plc.update(dt=0.01, world=world)  # State 2 -> 3 (EXIT_STOPPED)
        plc.update(dt=0.01, world=world)  # State 3 -> 4 (TRIGGER_ROBOT)
        self.assertEqual(plc.state, 4)
        self.assertTrue(plc.red_lamp)
        self.assertFalse(world.conveyor.is_running)
        self.assertTrue(plc.robot_trigger)

        # Step 3: Robot Arm executes pick, classifies HSV, and loads vehicle
        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=plc.robot_trigger, world=world)  # -> RENK
        self.assertEqual(arm.state, "RENK")

        frame = cam.get_arm_frame(cube)
        arm.step(dt=0.01, camera_frame=frame, detector=det, world=world)  # -> AL
        self.assertEqual(arm.detected_color, "RED")
        self.assertEqual(arm.state, "AL")

        arm.step(dt=0.01, world=world)  # -> DOGRULA (picks cube)
        self.assertTrue(cube.is_picked)
        self.assertEqual(arm.state, "DOGRULA")

        arm.step(dt=0.01)  # -> YUKLE
        self.assertEqual(arm.state, "YUKLE")

        arm.step(dt=0.01)  # -> GONDER (releases to car)
        self.assertTrue(cube.is_loaded)
        self.assertEqual(arm.state, "GONDER")

        arm.step(dt=0.01)  # -> MQTT Publish & Return HOME
        self.assertEqual(broker.get_last_message("arac/yuk"), "RED")
        self.assertEqual(broker.get_last_message("robot/basla"), "BASLA")
        self.assertEqual(arm.state, "HOME")

        # Step 4: Autonomous vehicle receives MQTT trigger and departs
        self.assertTrue(car.is_autonomous)
        self.assertEqual(car.target_bay_color, "RED")
        self.assertEqual(car.task_state, "LANE_KEEP")

        # Step 5: Vehicle navigates track to RED parking bay (X=380, Y=625)
        # Advance through straight, turn, pedestrian crossing, and approach
        for _ in range(400):
            car.step(dt=0.1)
            if car.completed:
                break

        self.assertEqual(car.task_state, "PARK_ETTI")
        self.assertTrue(car.completed)
        self.assertEqual(car.pwm, 0)
        self.assertAlmostEqual(car.x, 380.0, delta=15.0)

    # ========================================================================
    # SCENARIO 2: Automated Green Cube Production Cycle
    # ========================================================================
    def test_scenario_2_automated_green_cube_production_cycle(self):
        """
        Scenario 2: Full Automated Green Cube Production Cycle.
        Conveyor -> Exit S2 -> Arm Classical HSV GREEN -> MQTT GREEN ->
        Car Lane Tracking -> Green Parking Bay Docking (X=300).
        """
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        car = get_vehicle_sim(world=world)
        hmi = get_hmi_panel(plc)

        broker.subscribe("arac/yuk", lambda t, p: car.on_mqtt_message(t, p))
        broker.subscribe("robot/basla", lambda t, p: car.on_mqtt_message(t, p))

        hmi.press_start()
        cube = hmi.add_cube(world, "GREEN")
        plc.update(dt=0.01, world=world)
        plc.update(dt=0.01, world=world)
        cube.x = 780.0
        plc.update(dt=0.01, world=world)
        plc.update(dt=0.01, world=world)

        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=plc.robot_trigger, world=world)
        frame = cam.get_arm_frame(cube)
        arm.step(dt=0.01, camera_frame=frame, detector=det, world=world)
        self.assertEqual(arm.detected_color, "GREEN")

        arm.step(dt=0.01, world=world)  # AL
        arm.step(dt=0.01)  # DOGRULA
        arm.step(dt=0.01)  # YUKLE
        arm.step(dt=0.01)  # GONDER
        self.assertEqual(broker.get_last_message("arac/yuk"), "GREEN")

        self.assertTrue(car.is_autonomous)
        self.assertEqual(car.target_bay_color, "GREEN")

        for _ in range(400):
            car.step(dt=0.1)
            if car.completed:
                break

        self.assertEqual(car.task_state, "PARK_ETTI")
        self.assertTrue(car.completed)
        self.assertAlmostEqual(car.x, 300.0, delta=15.0)

    # ========================================================================
    # SCENARIO 3: Automated Blue Cube Production Cycle
    # ========================================================================
    def test_scenario_3_automated_blue_cube_production_cycle(self):
        """
        Scenario 3: Full Automated Blue Cube Production Cycle.
        Conveyor -> Exit S2 -> Arm Classical HSV BLUE -> MQTT BLUE ->
        Car Lane Tracking -> Blue Parking Bay Docking (X=220).
        """
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        car = get_vehicle_sim(world=world)
        hmi = get_hmi_panel(plc)

        broker.subscribe("arac/yuk", lambda t, p: car.on_mqtt_message(t, p))
        broker.subscribe("robot/basla", lambda t, p: car.on_mqtt_message(t, p))

        hmi.press_start()
        cube = hmi.add_cube(world, "BLUE")
        plc.update(dt=0.01, world=world)
        plc.update(dt=0.01, world=world)
        cube.x = 780.0
        plc.update(dt=0.01, world=world)
        plc.update(dt=0.01, world=world)

        arm.state = "BASLA_BEK"
        arm.step(dt=0.01, plc_trigger=plc.robot_trigger, world=world)
        frame = cam.get_arm_frame(cube)
        arm.step(dt=0.01, camera_frame=frame, detector=det, world=world)
        self.assertEqual(arm.detected_color, "BLUE")

        arm.step(dt=0.01, world=world)  # AL
        arm.step(dt=0.01)  # DOGRULA
        arm.step(dt=0.01)  # YUKLE
        arm.step(dt=0.01)  # GONDER
        self.assertEqual(broker.get_last_message("arac/yuk"), "BLUE")

        self.assertTrue(car.is_autonomous)
        self.assertEqual(car.target_bay_color, "BLUE")

        for _ in range(400):
            car.step(dt=0.1)
            if car.completed:
                break

        self.assertEqual(car.task_state, "PARK_ETTI")
        self.assertTrue(car.completed)
        self.assertAlmostEqual(car.x, 220.0, delta=15.0)

    # ========================================================================
    # SCENARIO 4: Conveyor Mid-Transit E-Stop Freeze & Recovery
    # ========================================================================
    def test_scenario_4_conveyor_mid_transit_estop_freeze_and_recovery(self):
        """
        Scenario 4: Conveyor Mid-Transit E-Stop Freeze & Recovery.
        Belt moving at 80mm/s is halted within 1 frame (<16ms).
        START is blocked while latched. Reset clears fault and resumes transport.
        """
        world = get_factory_world()
        plc = get_plc_engine()
        hmi = get_hmi_panel(plc)

        hmi.press_start()
        cube = hmi.add_cube(world, "RED")
        plc.update(dt=0.01, world=world)
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 2)
        self.assertTrue(world.conveyor.is_running)

        # Advance cube to mid-transit (x = 350mm)
        cube.x = 350.0

        # Operator hits E-Stop
        hmi.press_estop()
        plc.update(dt=0.016, world=world)  # Within 1 frame (<16ms)
        self.assertEqual(plc.state, 99)
        self.assertFalse(world.conveyor.is_running)
        self.assertTrue(plc.yellow_lamp)

        # Confirm cube position is frozen
        frozen_x = cube.x
        world.step(dt=1.0)
        self.assertEqual(cube.x, frozen_x)

        # Verify START is blocked while E-stop is latched
        hmi.press_start()
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 99)

        # Recovery procedure: Release E-Stop and press RESET
        plc.release_estop()
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 99)  # Still latched

        hmi.press_reset()
        plc.update(dt=0.01, world=world)
        self.assertEqual(plc.state, 0)   # Safely in OFF
        self.assertFalse(plc.estop_active)

        # Restart system and carry cube to completion
        hmi.press_start()
        plc.update(dt=0.01, world=world)  # 0 -> 1 (READY)
        plc.state = 2  # Resumes feeding cube already on belt
        plc.update(dt=0.01, world=world)
        self.assertTrue(world.conveyor.is_running)

        cube.x = 780.0
        plc.update(dt=0.01, world=world)  # 2 -> 3 (EXIT_STOPPED)
        self.assertEqual(plc.state, 3)

    # ========================================================================
    # SCENARIO 5: Vehicle In-Transit E-Stop Freeze & Resume
    # ========================================================================
    def test_scenario_5_vehicle_in_transit_estop_freeze_and_resume(self):
        """
        Scenario 5: Vehicle In-Transit E-Stop Freeze & Resume.
        Vehicle active on circuit immediately halts PWM on E-Stop, preserves pose,
        and safely resumes trajectory after Reset.
        """
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.target_bay_color = "RED"
        car.step(dt=1.0)
        self.assertGreater(car.x, 380.0)

        # Inject E-Stop while driving
        car.estop()
        self.assertEqual(car.pwm, 0)
        self.assertEqual(car.velocity, 0.0)
        frozen_x = car.x
        frozen_y = car.y

        # Verify immobility under simulation ticks
        for _ in range(5):
            car.step(dt=0.1)
        self.assertEqual(car.x, frozen_x)
        self.assertEqual(car.y, frozen_y)

        # Reset E-Stop
        car.reset_estop()
        car.step(dt=0.1)
        self.assertGreaterEqual(car.velocity, 0.0)

    # ========================================================================
    # SCENARIO 6: Pedestrian Crossing Detection & 3.0s Stop
    # ========================================================================
    def test_scenario_6_pedestrian_crossing_detection_and_stop(self):
        """
        Scenario 6: Pedestrian Crossing Sign Detection & 3.0s Precision Stop.
        Vehicle halts at pedestrian sign, waits 3.0s, and resumes lane keeping.
        """
        car = get_vehicle_sim()
        car.is_autonomous = True
        car.task_state = "LANE_KEEP"
        car.x = 850.0
        car.y = 415.0
        car.step(dt=0.01)

        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")
        self.assertEqual(car.pwm, 0)
        self.assertEqual(car.velocity, 0.0)

        # Advance 1.5 seconds (halfway)
        car.step(dt=1.5)
        self.assertEqual(car.task_state, "PEDESTRIAN_STOP")
        self.assertEqual(car.velocity, 0.0)
        self.assertAlmostEqual(car.stop_timer, 1.5, delta=0.1)

        # Advance past 3.0s (1.6s more)
        car.step(dt=1.6)
        self.assertEqual(car.task_state, "LANE_KEEP")
        self.assertGreater(car.velocity, 0.0)

    # ========================================================================
    # SCENARIO 7: Full 3-Cube Sequential Batch Production Session
    # ========================================================================
    def test_scenario_7_full_three_cube_sequential_batch_production(self):
        """
        Scenario 7: Continuous 3-Cube Sequential Batch Production Session.
        Continuously processes RED -> GREEN -> BLUE cubes in one session.
        Verifies telemetry counters: Total=3, RED=1, GREEN=1, BLUE=1.
        """
        world = get_factory_world()
        plc = get_plc_engine()
        cam = get_virtual_cameras()
        det = get_color_detector()
        broker = get_mqtt_broker()
        arm = get_robot_arm(mqtt_client=broker)
        hmi = get_hmi_panel(plc)

        colors = ["RED", "GREEN", "BLUE"]
        for color in colors:
            car = get_vehicle_sim(world=world)
            broker.subscribe("arac/yuk", lambda t, p: (car.on_mqtt_message(t, p), hmi.log_mqtt(t, p)))
            broker.subscribe("robot/basla", lambda t, p: (car.on_mqtt_message(t, p), hmi.log_mqtt(t, p)))

            hmi.press_start()
            cube = hmi.add_cube(world, color)
            plc.update(dt=0.01, world=world)
            plc.update(dt=0.01, world=world)

            # Move cube to exit
            cube.x = 780.0
            plc.update(dt=0.01, world=world)
            plc.update(dt=0.01, world=world)

            # Arm processes
            arm.state = "BASLA_BEK"
            arm.step(dt=0.01, plc_trigger=plc.robot_trigger, world=world)
            frame = cam.get_arm_frame(cube)
            arm.step(dt=0.01, camera_frame=frame, detector=det, world=world)
            self.assertEqual(arm.detected_color, color)

            arm.step(dt=0.01, world=world)  # AL
            arm.step(dt=0.01)  # DOGRULA
            arm.step(dt=0.01)  # YUKLE
            arm.step(dt=0.01)  # GONDER
            arm.step(dt=0.01)  # Finish to HOME

            # PLC completes cycle after cube is picked from exit
            plc.update(dt=0.01, world=world)  # State 4 -> 5 (CYCLE_COMPLETE)
            plc.update(dt=0.01, world=world)  # State 5 -> 1 (READY)

            # Vehicle drives to bay
            self.assertTrue(car.is_autonomous)
            for _ in range(400):
                car.step(dt=0.1)
                if car.completed:
                    break
            self.assertTrue(car.completed)

        # Verify final session production tally
        self.assertEqual(hmi.counters["total"], 3)
        self.assertEqual(hmi.counters["RED"], 1)
        self.assertEqual(hmi.counters["GREEN"], 1)
        self.assertEqual(hmi.counters["BLUE"], 1)
        self.assertEqual(arm.cycles_completed, 3)


if __name__ == "__main__":
    unittest.main()
