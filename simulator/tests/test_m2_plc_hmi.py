"""
Unit and Integration Tests for Milestone 2:
- S7-1200 PLC Engine (simulator.core.plc_engine)
- Industrial HMI Panel (simulator.gui.hmi_panel)
"""

import unittest
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
pygame.init()

from simulator.core.factory_world import FactoryWorld
from simulator.core.plc_engine import (
    PLCEngine,
    STATE_OFF,
    STATE_READY,
    STATE_FEEDING,
    STATE_EXIT_STOPPED,
    STATE_TRIGGER_ROBOT,
    STATE_CYCLE_COMPLETE,
    STATE_ESTOP_FREEZE,
)
from simulator.gui.hmi_panel import HMIPanel


class TestM2PLCEngineAndHMI(unittest.TestCase):
    def setUp(self):
        self.world = FactoryWorld()
        self.plc = PLCEngine()
        self.hmi = HMIPanel(self.plc)

    # -------------------------------------------------------------------------
    # PLC Engine Tests
    # -------------------------------------------------------------------------
    def test_plc_initial_state_is_off_and_dark(self):
        """Verify that newly initialized PLC is in State 0 with all outputs dark."""
        self.assertEqual(self.plc.state, STATE_OFF)
        self.assertEqual(self.plc.state_name, "OFF")
        self.assertFalse(self.plc.is_running)
        self.assertFalse(self.plc.green_lamp)
        self.assertFalse(self.plc.red_lamp)
        self.assertFalse(self.plc.yellow_lamp)
        self.assertFalse(self.plc.robot_trigger)

    def test_plc_full_cycle_state_progression(self):
        """Verify ladder logic cycle: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 1."""
        # 0 -> 1 on START
        self.plc.press_start()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_READY)
        self.assertTrue(self.plc.red_lamp)
        self.assertFalse(self.plc.is_running)

        # Add cube -> S1 triggers -> 1 -> 2
        cube = self.world.add_cube("RED")
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_FEEDING)
        self.assertTrue(self.plc.is_running)
        self.assertTrue(self.plc.green_lamp)
        self.assertFalse(self.plc.red_lamp)

        # Cube reaches exit -> S2 triggers -> 2 -> 3
        cube.x = 770.0
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_EXIT_STOPPED)
        self.assertFalse(self.plc.is_running)
        self.assertTrue(self.plc.red_lamp)

        # Vehicle docked -> 3 -> 4
        self.plc.I_VEHICLE_READY = True
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_TRIGGER_ROBOT)
        self.assertTrue(self.plc.robot_trigger)

        # Arm picks cube -> S2 clears -> 4 -> 5 (CYCLE_COMPLETE)
        cube.is_picked = True
        self.world.conveyor.active_cube = None
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_CYCLE_COMPLETE)

        # Next scan cycle: 5 -> 1 (READY) and increment cycle_count
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.cycle_count, 1)
        self.assertEqual(self.plc.state, STATE_READY)

    def test_plc_estop_immediate_cutoff_and_latching(self):
        """Verify E-Stop immediately cuts conveyor motor, sets state 99, and latches."""
        self.world.add_cube("GREEN")
        self.plc.state = STATE_FEEDING
        self.plc.update(dt=0.016, world=self.world)
        self.assertTrue(self.world.conveyor.is_running)

        # Trigger E-Stop
        self.plc.press_estop()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_ESTOP_FREEZE)
        self.assertFalse(self.world.conveyor.is_running)
        self.assertTrue(self.plc.estop_active)
        self.assertTrue(self.plc.yellow_lamp)

        # Releasing E-Stop alone does not clear latch
        self.plc.release_estop()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_ESTOP_FREEZE)
        self.assertTrue(self.plc.estop_active)

        # Pressing START during latch is rejected
        self.plc.press_start()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_ESTOP_FREEZE)

        # Pressing RESET clears latch and returns to State 0
        self.plc.press_reset()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_OFF)
        self.assertFalse(self.plc.estop_active)
        self.assertFalse(self.plc.yellow_lamp)

    def test_plc_normal_stop_returns_to_state_off(self):
        """Verify normal STOP pushbutton halts belt and returns to State 0."""
        self.plc.state = STATE_FEEDING
        self.plc.press_stop()
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_OFF)
        self.assertFalse(self.plc.is_running)

    def test_plc_telemetry_dictionary(self):
        """Verify get_telemetry returns complete dictionary with inputs, outputs, and state."""
        telem = self.plc.get_telemetry()
        self.assertIn("state", telem)
        self.assertIn("inputs", telem)
        self.assertIn("outputs", telem)
        self.assertEqual(telem["state_name"], "OFF")

    # -------------------------------------------------------------------------
    # HMI Panel Tests
    # -------------------------------------------------------------------------
    def test_hmi_tactile_mouse_clicks(self):
        """Verify mouse clicks on HMI button rects trigger corresponding PLC actions."""
        # Click START
        ev_start = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (1100, 480), "button": 1})
        self.assertTrue(self.hmi.handle_event(ev_start, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_READY)

        # Click ADD GREEN CUBE
        ev_add_g = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (1250, 530), "button": 1})
        self.assertTrue(self.hmi.handle_event(ev_add_g, self.world))
        self.assertEqual(self.world.conveyor.active_cube.color, "GREEN")
        self.assertEqual(self.hmi.counters["GREEN"], 1)

        # Click E-STOP
        ev_estop = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (1320, 485), "button": 1})
        self.assertTrue(self.hmi.handle_event(ev_estop, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_ESTOP_FREEZE)

        # Release and Click RESET
        self.hmi.release_estop()
        ev_reset = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (1450, 480), "button": 1})
        self.assertTrue(self.hmi.handle_event(ev_reset, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_OFF)

    def test_hmi_keyboard_shortcuts(self):
        """Verify keyboard shortcuts [Space], [X], [E], [R], [1], [2], [3]."""
        # [Space] -> START
        ev_space = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
        self.assertTrue(self.hmi.handle_event(ev_space, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_READY)

        # [2] -> ADD GREEN
        ev_key_2 = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_2})
        self.assertTrue(self.hmi.handle_event(ev_key_2, self.world))
        self.assertEqual(self.world.conveyor.active_cube.color, "GREEN")

        # [E] -> E-STOP
        ev_key_e = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_e})
        self.assertTrue(self.hmi.handle_event(ev_key_e, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_ESTOP_FREEZE)

        # [R] -> RESET
        self.hmi.release_estop()
        ev_key_r = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_r})
        self.assertTrue(self.hmi.handle_event(ev_key_r, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_OFF)

        # [X] -> STOP
        self.plc.state = STATE_FEEDING
        ev_key_x = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_x})
        self.assertTrue(self.hmi.handle_event(ev_key_x, self.world))
        self.plc.update(dt=0.016, world=self.world)
        self.assertEqual(self.plc.state, STATE_OFF)

    def test_hmi_counters_and_color_validation(self):
        """Verify cube counting by color and ValueError on invalid color string."""
        self.hmi.add_cube(self.world, "RED")
        self.hmi.add_cube(self.world, "BLUE")
        self.assertEqual(self.hmi.counters["total"], 2)
        self.assertEqual(self.hmi.counters["RED"], 1)
        self.assertEqual(self.hmi.counters["BLUE"], 1)
        self.assertEqual(self.hmi.counters["GREEN"], 0)

        with self.assertRaises(ValueError):
            self.hmi.add_cube(self.world, "YELLOW")

    def test_hmi_mqtt_log_formatting(self):
        """Verify MQTT message logging with topic and payload."""
        self.hmi.log_mqtt("arac/yuk", "RED")
        self.assertEqual(len(self.hmi.mqtt_log), 1)
        self.assertEqual(self.hmi.mqtt_log[0], "[arac/yuk] RED")

    def test_hmi_rendering_to_surface(self):
        """Verify full GUI rendering without crashes and non-zero pixels in HMI region."""
        surface = pygame.Surface((1600, 900))
        self.hmi.log_mqtt("arac/yuk", "BLUE")
        self.hmi.render(surface, self.world, dt=0.016)

        buf = pygame.surfarray.array3d(surface)
        hmi_sub = buf[1040:1600, 420:900]
        self.assertGreater(hmi_sub.sum(), 0)


if __name__ == "__main__":
    unittest.main()
