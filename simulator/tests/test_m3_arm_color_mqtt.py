"""
Unit Tests for Milestone 3 (M3):
Classical OpenCV HSV Color Detector, 4-DOF Robot Arm Sim, and Embedded MQTT Broker.
"""

from __future__ import annotations

import json
import math
import threading
import time
import unittest
from typing import List

import cv2
import numpy as np

from simulator.core.color_detector_sim import (
    ColorDetectorSim,
    ColorResult,
    RenkSonuc,
    VARSAYILAN_HSV,
)
from simulator.core.factory_world import Cube, FactoryWorld
from simulator.core.mqtt_broker import (
    MQTTBroker,
    TOPIC_ARAC_YUK,
    TOPIC_ROBOT_BASLA,
    TOPIC_ROBOT_DURUM,
    TOPIC_ROBOT_VERI,
)
from simulator.core.robot_arm_sim import (
    D_AL,
    D_BASLA_BEK,
    D_DOGRULA,
    D_GONDER,
    D_GORME,
    D_HOME,
    D_RENK,
    D_YUKLE,
    GRIPPER_CLOSED_DEG,
    GRIPPER_OPEN_DEG,
    JOINT_LIMITS_DEG,
    WAYPOINTS,
    RobotArmSim,
)
from simulator.core.virtual_cameras import VirtualArmCamera


class TestColorDetectorSim(unittest.TestCase):
    """Unit tests for classical OpenCV HSV Color Detector."""

    def setUp(self):
        self.detector = ColorDetectorSim()
        self.cam = VirtualArmCamera()

    def test_classical_architecture_no_deep_learning(self):
        """Verifies detector relies on classical HSV dictionaries without AI model weights."""
        self.assertTrue(hasattr(self.detector, "hsv_ranges"))
        self.assertIn("RED", self.detector.hsv_ranges)
        self.assertIn("GREEN", self.detector.hsv_ranges)
        self.assertIn("BLUE", self.detector.hsv_ranges)
        self.assertFalse(hasattr(self.detector, "model"))
        self.assertFalse(hasattr(self.detector, "net"))

    def test_red_dual_band_detection(self):
        """Verifies RED detection across both low-Hue (0-10) and high-Hue (170-179) bands."""
        # Low Hue Red
        frame_low = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame_low[120:360, 215:466] = (20, 20, 220)  # BGR
        res_low = self.detector.detect(frame_low)
        self.assertEqual(res_low.renk, "RED")
        self.assertTrue(res_low.emin)

        # High Hue Red
        frame_high = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame_high[120:360, 215:466] = (47, 13, 220)  # BGR
        res_high = self.detector.detect(frame_high)
        self.assertEqual(res_high.renk, "RED")
        self.assertTrue(res_high.emin)

    def test_green_single_band_detection(self):
        """Verifies GREEN detection in [40, 85] range."""
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (157, 210, 12)  # BGR
        res = self.detector.detect(frame)
        self.assertEqual(res.renk, "GREEN")
        self.assertTrue(res.emin)

    def test_blue_single_band_detection(self):
        """Verifies BLUE detection in [95, 130] range."""
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        frame[120:360, 215:466] = (220, 137, 13)  # BGR
        res = self.detector.detect(frame)
        self.assertEqual(res.renk, "BLUE")
        self.assertTrue(res.emin)

    def test_occupancy_below_threshold_yields_unknown(self):
        """Verifies occupancy below 0.40 returns UNKNOWN."""
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        # Small patch: 20x20 pixels is << 40% of 251x240 ROI
        frame[120:140, 215:235] = (20, 20, 220)
        res = self.detector.detect(frame)
        self.assertEqual(res.renk, "UNKNOWN")
        self.assertFalse(res.emin)

    def test_margin_conflict_yields_unknown(self):
        """Verifies competing colors with margin < 0.12 return UNKNOWN."""
        frame = np.full((480, 640, 3), fill_value=45, dtype=np.uint8)
        rx, ry, rw, rh = self.detector.roi
        # Split ROI exactly 50/50 between RED and GREEN
        frame[ry : ry + rh, rx : rx + rw // 2] = (47, 13, 220)
        frame[ry : ry + rh, rx + rw // 2 : rx + rw] = (157, 210, 12)
        res = self.detector.detect(frame)
        self.assertEqual(res.renk, "UNKNOWN")
        self.assertLess(res.marj, 0.12)
        self.assertFalse(res.emin)

    def test_kutu_var_mi_presence(self):
        """Verifies kutu_var_mi returns True only when solid cube occupies ROI."""
        frame_empty = self.cam.render(has_cube=False)
        frame_cube = self.cam.render(has_cube=True, cube_color="BLUE")
        self.assertFalse(self.detector.kutu_var_mi(frame_empty))
        self.assertTrue(self.detector.kutu_var_mi(frame_cube))

    def test_roi_crop_boundary_safety(self):
        """Verifies small or out-of-bounds frames do not raise indexing exceptions."""
        small_frame = np.zeros((50, 50, 3), dtype=np.uint8)
        res = self.detector.detect(small_frame)
        self.assertEqual(res.renk, "UNKNOWN")

        empty_frame = np.zeros((0, 0, 3), dtype=np.uint8)
        res_empty = self.detector.detect(empty_frame)
        self.assertEqual(res_empty.renk, "UNKNOWN")

    def test_multi_frame_voting(self):
        """Verifies multi-frame majority voting over 8 frames."""
        f_green = self.cam.render(has_cube=True, cube_color="GREEN")
        f_noisy = self.cam.render(has_cube=True, cube_color="GREEN", noise_std=10.0)
        f_empty = self.cam.render(has_cube=False)

        # 6 green frames, 2 empty frames -> majority vote should be GREEN
        frames = [f_green] * 4 + [f_noisy] * 2 + [f_empty] * 2
        winner = self.detector.read_color_voting(frames)
        self.assertEqual(winner, "GREEN")

        # 8 empty frames -> majority vote should be None
        winner_none = self.detector.read_color_voting([f_empty] * 8)
        self.assertIsNone(winner_none)

    def test_roi_ciz_visualization(self):
        """Verifies roi_ciz overlays inspection rectangle without modifying original frame."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res = ColorResult("RED", 0.85, 0.85, 0.45, {"RED": 0.85}, True)
        drawn = self.detector.roi_ciz(frame, res)
        self.assertEqual(frame.sum(), 0)  # Original unchanged
        self.assertGreater(drawn.sum(), 0)  # Contains overlay lines


class TestRobotArmSim(unittest.TestCase):
    """Unit tests for 4-DOF Robot Arm Kinematics & State Machine."""

    def setUp(self):
        self.broker = MQTTBroker()
        self.arm = RobotArmSim(mqtt_client=self.broker)
        self.world = FactoryWorld()

    def test_joint_configuration_and_limits(self):
        """Verifies 4 articulated joints, degrees, and soft limit adherence."""
        self.assertEqual(len(self.arm.joint_angles), 4)
        for i, (min_a, max_a) in enumerate(JOINT_LIMITS_DEG):
            self.assertGreaterEqual(self.arm.joint_angles[i], min_a)
            self.assertLessEqual(self.arm.joint_angles[i], max_a)

    def test_gripper_clamping(self):
        """Verifies gripper angle is clamped between 50 and 140 deg."""
        self.arm.gripper_angle = 200.0
        self.assertEqual(self.arm.gripper_angle, GRIPPER_OPEN_DEG)
        self.arm.gripper_angle = 10.0
        self.assertEqual(self.arm.gripper_angle, GRIPPER_CLOSED_DEG)

    def test_waypoints_accuracy(self):
        """Verifies standard waypoint poses match engineering parameters."""
        for wp in ("HOME", "GORME", "AL", "YUKLE", "GECIS"):
            self.assertIn(wp, WAYPOINTS)
            self.assertEqual(len(WAYPOINTS[wp]), 4)
        self.assertEqual(WAYPOINTS["YUKLE"][0], 90.0)  # Base azimuth for dock

    def test_full_8_state_sequence(self):
        """Verifies sequential state progression through all 8 states."""
        arm = self.arm
        cube = self.world.add_cube("GREEN")

        # 1. HOME -> GORME
        self.assertEqual(arm.state, D_HOME)
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_GORME)

        # 2. GORME -> BASLA_BEK
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_BASLA_BEK)

        # 3. BASLA_BEK holds when plc_trigger is False
        arm.step(dt=0.01, plc_trigger=False)
        self.assertEqual(arm.state, D_BASLA_BEK)

        # 4. BASLA_BEK -> RENK on plc_trigger=True
        arm.step(dt=0.01, plc_trigger=True)
        self.assertEqual(arm.state, D_RENK)

        # 5. RENK -> AL
        arm.step(dt=0.01, world=self.world)
        self.assertEqual(arm.detected_color, "GREEN")
        self.assertEqual(arm.state, D_AL)

        # 6. AL -> DOGRULA (picks active cube)
        arm.step(dt=0.01, world=self.world)
        self.assertEqual(arm.state, D_DOGRULA)
        self.assertTrue(cube.is_picked)
        self.assertEqual(arm.gripper_angle, GRIPPER_CLOSED_DEG)

        # 7. DOGRULA -> YUKLE
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_YUKLE)

        # 8. YUKLE -> GONDER (releases cube to vehicle)
        arm.step(dt=0.01, world=self.world)
        self.assertEqual(arm.state, D_GONDER)
        self.assertTrue(cube.is_loaded)
        self.assertEqual(arm.gripper_angle, GRIPPER_OPEN_DEG)

        # 9. GONDER -> HOME (MQTT publication and cycle increment)
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_HOME)
        self.assertEqual(arm.cycles_completed, 1)
        self.assertEqual(self.broker.get_last_message(TOPIC_ARAC_YUK), "GREEN")
        self.assertEqual(self.broker.get_last_message(TOPIC_ROBOT_BASLA), "BASLA")

    def test_missed_pick_recovery(self):
        """Verifies failure to pick cube in DOGRULA safely returns to HOME."""
        arm = self.arm
        arm.state = D_DOGRULA
        arm.carried_cube = None
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_HOME)
        self.assertEqual(arm.gripper_angle, GRIPPER_OPEN_DEG)

    def test_e_stop_freeze_and_unfreeze(self):
        """Verifies arm freezes immediately on E-Stop and recovers after unfreeze."""
        arm = self.arm
        arm.state = D_AL
        arm.freeze()
        self.assertTrue(arm.is_frozen)

        # Step while frozen should not change state or angles
        angles_frozen = list(arm.joint_angles)
        arm.step(dt=0.05, plc_trigger=True)
        self.assertEqual(arm.state, D_AL)
        self.assertEqual(arm.joint_angles, angles_frozen)

        # Unfreeze resumes execution
        arm.unfreeze()
        self.assertFalse(arm.is_frozen)
        arm.step(dt=0.01)
        self.assertEqual(arm.state, D_DOGRULA)

    def test_forward_kinematics_and_world_projections(self):
        """Verifies forward kinematics 3D calculations and 2D visual projection points."""
        fk_x, fk_y, fk_z = self.arm.get_forward_kinematics()
        self.assertIsInstance(fk_x, float)
        self.assertIsInstance(fk_y, float)
        self.assertIsInstance(fk_z, float)
        self.assertGreater(fk_z, 0.0)  # Above base

        joint_points = self.arm.get_joint_world_positions()
        self.assertEqual(len(joint_points), 4)
        # First point should be shoulder base position
        self.assertEqual(joint_points[0], (380.0, 200.0))


class TestMQTTBroker(unittest.TestCase):
    """Unit tests for Embedded MQTT Message Broker."""

    def setUp(self):
        self.broker = MQTTBroker()

    def test_publish_and_subscribe(self):
        """Verifies topic subscription and payload callback dispatch."""
        received: List[str] = []
        self.broker.subscribe("robot/status", lambda t, p: received.append(p))
        self.broker.publish("robot/status", "ONLINE")
        self.assertEqual(received, ["ONLINE"])
        self.assertEqual(self.broker.get_last_message("robot/status"), "ONLINE")

    def test_wildcard_multi_level_topic(self):
        """Verifies multi-level wildcard (#) subscription."""
        events: List[Tuple[str, str]] = []
        self.broker.subscribe("robot/#", lambda t, p: events.append((t, p)))

        self.broker.publish("robot/basla", "BASLA")
        self.broker.publish("robot/veri", "RED")
        self.broker.publish("arac/yuk", "IGNORE_ME")

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0], ("robot/basla", "BASLA"))
        self.assertEqual(events[1], ("robot/veri", "RED"))

    def test_wildcard_single_level_topic(self):
        """Verifies single-level wildcard (+) subscription."""
        events: List[str] = []
        self.broker.subscribe("device/+/state", lambda t, p: events.append(t))

        self.broker.publish("device/conveyor/state", "RUNNING")
        self.broker.publish("device/arm/state", "IDLE")
        self.broker.publish("device/arm/joint/state", "SKIP")

        self.assertEqual(events, ["device/conveyor/state", "device/arm/state"])

    def test_retained_message_delivery(self):
        """Verifies retained message is delivered to newly subscribing clients."""
        self.broker.publish(TOPIC_ARAC_YUK, "BLUE", retain=True)

        new_sub_received: List[str] = []
        self.broker.subscribe(TOPIC_ARAC_YUK, lambda t, p: new_sub_received.append(p))
        self.assertEqual(new_sub_received, ["BLUE"])

    def test_client_helper_methods(self):
        """Verifies MqttIstemci drop-in helper methods."""
        self.assertTrue(self.broker.yuk_gonder("RED"))
        self.assertEqual(self.broker.get_last_message(TOPIC_ARAC_YUK), "RED")

        self.assertTrue(self.broker.basla_gonder())
        self.assertEqual(self.broker.get_last_message(TOPIC_ROBOT_BASLA), "BASLA")

        self.assertTrue(self.broker.durum_gonder("IDLE_OK"))
        self.assertEqual(self.broker.get_last_message(TOPIC_ROBOT_DURUM), "IDLE_OK")

        self.assertTrue(self.broker.renk_gonder("GREEN"))
        payload = json.loads(self.broker.get_last_message(TOPIC_ROBOT_VERI))
        self.assertEqual(payload["renk"], "GREEN")

    def test_clear_messages(self):
        """Verifies clear() empties history log and retained store."""
        self.broker.publish("test/topic", "DATA", retain=True)
        self.assertGreater(len(self.broker.messages), 0)
        self.broker.clear()
        self.assertEqual(len(self.broker.messages), 0)
        self.assertIsNone(self.broker.get_last_message("test/topic"))

    def test_concurrent_thread_safety(self):
        """Verifies thread safety during rapid concurrent publications."""
        threads = []
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(25):
                    self.broker.publish(f"worker/{worker_id}", f"MSG_{i}")
            except Exception as e:
                errors.append(e)

        for w in range(4):
            t = threading.Thread(target=worker, args=(w,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(self.broker.messages), 100)


class TestM3IntegratedCellHandshake(unittest.TestCase):
    """Integrated tests coupling OpenCV HSV Detection, 4-DOF Robot Arm, and MQTT Broker."""

    def test_integrated_pick_and_dispatch_cycle(self):
        """
        Executes a full digital-twin pick cycle:
        Conveyor settled -> Arm triggers -> Classical HSV detects RED ->
        Arm picks -> Loads vehicle -> Emits arac/yuk & robot/basla.
        """
        world = FactoryWorld()
        cube = world.add_cube("RED")
        world.conveyor.is_running = False
        cube.x = 780.0  # At exit sensor

        broker = MQTTBroker()
        arm = RobotArmSim(mqtt_client=broker)
        detector = ColorDetectorSim()
        cam = VirtualArmCamera()

        received_yuk = []
        received_basla = []
        broker.subscribe(TOPIC_ARAC_YUK, lambda t, p: received_yuk.append(p))
        broker.subscribe(TOPIC_ROBOT_BASLA, lambda t, p: received_basla.append(p))

        # 1. Cycle begins
        arm.step(dt=0.01)  # HOME -> GORME
        arm.step(dt=0.01)  # GORME -> BASLA_BEK

        # 2. PLC trigger asserted (%Q0.4)
        arm.step(dt=0.01, plc_trigger=True)  # BASLA_BEK -> RENK
        self.assertEqual(arm.state, D_RENK)

        # 3. Arm captures overhead frame and runs classical HSV
        frame = cam.get_frame(has_cube=True, cube_color="RED")
        arm.step(dt=0.01, camera_frame=frame, detector=detector, world=world)  # RENK -> AL
        self.assertEqual(arm.detected_color, "RED")
        self.assertEqual(arm.state, D_AL)

        # 4. Gripper closes and picks cube
        arm.step(dt=0.01, world=world)  # AL -> DOGRULA
        self.assertTrue(cube.is_picked)
        self.assertIsNone(world.conveyor.active_cube)
        self.assertEqual(arm.state, D_DOGRULA)

        # 5. Verification -> 3-stage loading trajectory
        arm.step(dt=0.01)  # DOGRULA -> YUKLE
        self.assertEqual(arm.state, D_YUKLE)

        # 6. Cube dropped into vehicle bay -> GONDER
        arm.step(dt=0.01, world=world)  # YUKLE -> GONDER
        self.assertTrue(cube.is_loaded)
        self.assertEqual(arm.state, D_GONDER)

        # 7. MQTT message broadcast -> returns HOME
        arm.step(dt=0.01)  # GONDER -> HOME
        self.assertEqual(arm.state, D_HOME)
        self.assertEqual(arm.cycles_completed, 1)

        self.assertIn("RED", received_yuk)
        self.assertIn("BASLA", received_basla)


if __name__ == "__main__":
    unittest.main()
