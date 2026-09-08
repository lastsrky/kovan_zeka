"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Adversarial Stress Testing Suite for Factory World Physics

Author: teamwork_preview_challenger_m1_1
Module: simulator.tests.test_adversarial_physics
"""

import math
import unittest
import numpy as np

from simulator.config import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    CONVEYOR_PHYSICAL_LENGTH_MM,
    CONVEYOR_SPEED_MM_S,
    EAST_CURVE_CENTER,
    VEHICLE_MAX_SPEED_PX_S,
    VEHICLE_STEER_MAX_RAD,
    VEHICLE_STEER_MIN_RAD,
    WEST_CURVE_CENTER,
)
from simulator.core.factory_world import (
    BeamSensor,
    Cube,
    CubeColor,
    CubeState,
    ConveyorBelt,
    FactoryWorld,
    ParkingBay,
    ProximitySensor,
    Track,
    Vehicle,
    VehicleDrivingState,
)


class TestDtStress(unittest.TestCase):
    """Stress tests temporal integration under high dt, zero dt, negative dt, and extremes."""

    def setUp(self):
        self.world = FactoryWorld()

    def test_zero_dt_stability(self):
        """Zero dt should not advance simulation time, crash, or divide by zero."""
        self.world.add_cube("RED")
        self.world.conveyor.is_running = True
        self.world.vehicle.set_controls(throttle=0.5, normalized_steer=0.5)

        initial_time = self.world.time
        initial_cube_x = self.world.conveyor.active_cube.x
        initial_vehicle_pose = self.world.vehicle.pose

        for _ in range(50):
            self.world.step(0.0)

        self.assertEqual(self.world.time, initial_time)
        self.assertEqual(self.world.conveyor.active_cube.x, initial_cube_x)
        self.assertEqual(self.world.vehicle.pose, initial_vehicle_pose)
        self.assertFalse(math.isnan(self.world.vehicle.x))
        self.assertFalse(math.isnan(self.world.vehicle.heading))

    def test_high_dt_one_second(self):
        """dt = 1.0s (60x nominal) must advance physics stably without explosion."""
        cube = self.world.add_cube("GREEN")
        self.world.conveyor.is_running = True
        self.world.vehicle.set_controls(throttle=1.0, normalized_steer=0.8)

        self.world.step(1.0)

        # Conveyor speed is 80 mm/s. In 1.0s, cube advances by 80 mm.
        self.assertAlmostEqual(cube.x, 80.0, places=3)
        self.assertAlmostEqual(self.world.time, 1.0, places=3)
        self.assertTrue(0.0 <= self.world.vehicle.speed <= VEHICLE_MAX_SPEED_PX_S)
        self.assertTrue(-math.pi <= self.world.vehicle.heading <= math.pi)

    def test_extreme_high_dt(self):
        """dt = 10.0s, 60.0s, 1000.0s should clamp at physical stops and keep heading normalized."""
        cube = self.world.add_cube("BLUE")
        self.world.conveyor.is_running = True
        self.world.vehicle.set_controls(throttle=1.0, normalized_steer=-1.0)

        # 10 second step - cube travels 800 mm, hits conveyor discharge clamp
        self.world.step(10.0)
        self.assertEqual(cube.x, CONVEYOR_PHYSICAL_LENGTH_MM)
        self.assertEqual(cube.state, CubeState.AT_EXIT)
        self.assertTrue(self.world.conveyor.has_cube_at_exit)

        # 1000 second step - vehicle heading must remain bounded in [-pi, pi]
        self.world.step(1000.0)
        self.assertTrue(-math.pi <= self.world.vehicle.heading <= math.pi)
        self.assertFalse(math.isnan(self.world.vehicle.x))
        self.assertFalse(math.isinf(self.world.vehicle.x))
        self.assertFalse(math.isnan(self.world.vehicle.heading))

    def test_negative_dt(self):
        """Negative dt should not raise unhandled exceptions."""
        cube = self.world.add_cube("RED")
        self.world.conveyor.is_running = True
        self.world.step(1.0)  # Move to 80 mm
        self.assertAlmostEqual(cube.x, 80.0, places=3)

        # Step backwards
        self.world.step(-0.5)
        self.assertAlmostEqual(cube.x, 40.0, places=3)

        # Step backwards past 0
        self.world.step(-2.0)
        # Position mapping in arena should clamp safely
        self.assertEqual(cube.position[0], 120.0)
        self.assertFalse(math.isnan(cube.position[0]))
        self.assertFalse(math.isnan(cube.position[1]))

    def test_micro_dt(self):
        """Microscopic dt (1e-12 s) should not produce subnormal numerical collapse."""
        cube = self.world.add_cube("RED")
        self.world.conveyor.is_running = True
        for _ in range(100):
            self.world.step(1e-12)
        self.assertFalse(math.isnan(cube.x))
        self.assertFalse(math.isnan(self.world.vehicle.x))


class TestConveyorBoundaryLimits(unittest.TestCase):
    """Stress tests conveyor belt, optical sensors, and cube coordinates under boundary conditions."""

    def setUp(self):
        self.belt = ConveyorBelt()

    def test_cube_exact_entry_boundary(self):
        """Cube at exact 0.0 mm and 40.0 mm boundaries."""
        cube = self.belt.add_cube("RED")
        cube.x = 0.0
        self.assertTrue(self.belt.has_cube_at_entry)
        self.assertFalse(self.belt.has_cube_at_exit)

        cube.x = 40.0
        self.assertTrue(self.belt.has_cube_at_entry)
        self.assertFalse(self.belt.has_cube_at_exit)

        cube.x = 40.0001
        self.assertFalse(self.belt.has_cube_at_entry)

    def test_cube_exact_exit_boundary(self):
        """Cube at exact 760.0 mm and 800.0 mm boundaries."""
        cube = self.belt.add_cube("GREEN")
        cube.x = 759.999
        self.assertFalse(self.belt.has_cube_at_exit)

        cube.x = 760.0
        self.assertTrue(self.belt.has_cube_at_exit)
        self.assertFalse(self.belt.has_cube_at_entry)

        cube.x = 800.0
        self.assertTrue(self.belt.has_cube_at_exit)

    def test_cube_spawning_beyond_boundary(self):
        """Directly setting cube beyond [0, 800] mm clamps 2D arena position and clamps x on update."""
        cube = self.belt.add_cube("BLUE")
        cube.x = 9999.0
        # Euclidean coordinate clamped to conveyor exit (120 + 240 = 360 px)
        self.assertAlmostEqual(cube.position[0], 360.0, places=2)

        # On next conveyor update, x is clamped to physical length 800.0 mm
        self.belt.is_running = True
        self.belt.update(0.016)
        self.assertEqual(cube.x, CONVEYOR_PHYSICAL_LENGTH_MM)
        self.assertEqual(cube.state, CubeState.AT_EXIT)

    def test_cube_spawning_negative_coordinate(self):
        """Directly setting negative x clamps 2D arena position to infeed anchor."""
        cube = self.belt.add_cube("RED")
        cube.x = -500.0
        # Euclidean coordinate clamped to conveyor entry (120 px)
        self.assertAlmostEqual(cube.position[0], 120.0, places=2)

    def test_multiple_cubes_queue(self):
        """Adding multiple cubes sequentially should track all cubes in belt list."""
        c1 = self.belt.add_cube("RED")
        c2 = self.belt.add_cube("GREEN")
        c3 = self.belt.add_cube("BLUE")

        self.assertEqual(len(self.belt.cubes), 3)
        self.assertEqual(self.belt.active_cube, c3)

        # Reset clears all
        self.belt.reset()
        self.assertEqual(len(self.belt.cubes), 0)
        self.assertIsNone(self.belt.active_cube)
        self.assertFalse(self.belt.has_cube_at_entry)
        self.assertFalse(self.belt.has_cube_at_exit)

    def test_conveyor_rapid_chattering(self):
        """Rapid toggling of conveyor motor at 100 Hz does not corrupt state."""
        cube = self.belt.add_cube("RED")
        dt = 0.01
        for i in range(200):
            self.belt.is_running = (i % 2 == 0)
            self.belt.update(dt)

        self.assertTrue(0.0 < cube.x < CONVEYOR_PHYSICAL_LENGTH_MM)
        self.assertFalse(math.isnan(cube.x))

    def test_remove_cube_at_exit_empty(self):
        """Calling remove_cube_at_exit when belt is empty returns None cleanly."""
        self.assertIsNone(self.belt.remove_cube_at_exit())


class TestVehicleKinematicStress(unittest.TestCase):
    """Stress tests vehicle kinematics, extreme steering angles, reverse throttle, and E-Stop."""

    def setUp(self):
        self.vehicle = Vehicle()

    def test_extreme_steering_inputs_normalized(self):
        """Normalized steering values outside [-1.0, 1.0] must clamp to [-VEHICLE_STEER_MAX_RAD, VEHICLE_STEER_MAX_RAD]."""
        # Excessive positive steer (+50.0)
        self.vehicle.set_controls(throttle=1.0, normalized_steer=50.0)
        self.assertAlmostEqual(self.vehicle.target_steer, VEHICLE_STEER_MAX_RAD, places=5)

        # Step vehicle to let steering slew rate settle
        for _ in range(50):
            self.vehicle.step(0.05)
        self.assertAlmostEqual(self.vehicle.steering_angle, VEHICLE_STEER_MAX_RAD, places=5)
        self.assertTrue(self.vehicle.steering_angle <= VEHICLE_STEER_MAX_RAD)

        # Excessive negative steer (-50.0)
        self.vehicle.set_controls(throttle=1.0, normalized_steer=-50.0)
        self.assertAlmostEqual(self.vehicle.target_steer, VEHICLE_STEER_MIN_RAD, places=5)
        for _ in range(50):
            self.vehicle.step(0.05)
        self.assertAlmostEqual(self.vehicle.steering_angle, VEHICLE_STEER_MIN_RAD, places=5)
        self.assertTrue(self.vehicle.steering_angle >= VEHICLE_STEER_MIN_RAD)

    def test_direct_extreme_steering_angle_clamping(self):
        """Directly injecting extreme steering angle (>45 deg, 90 deg) is clamped on step without tan(pi/2) singularity."""
        # Inject 90 degrees (pi/2) - tan(pi/2) would be infinity if not clamped before evaluation
        self.vehicle.steering_angle = math.pi / 2.0
        self.vehicle.target_steer = math.pi / 2.0
        self.vehicle.speed = 50.0

        # Step must clamp steering_angle to VEHICLE_STEER_MAX_RAD (35 deg)
        self.vehicle.step(0.016)

        self.assertAlmostEqual(self.vehicle.steering_angle, VEHICLE_STEER_MAX_RAD, places=5)
        self.assertFalse(math.isinf(self.vehicle.heading))
        self.assertFalse(math.isnan(self.vehicle.heading))

    def test_negative_reverse_throttle(self):
        """Throttle inputs below 0.0 must clamp to 0.0; target speed never negative via controls."""
        self.vehicle.set_controls(throttle=-2.0, normalized_steer=0.0)
        self.assertEqual(self.vehicle.target_speed, 0.0)

    def test_reverse_speed_kinematic_integration(self):
        """If vehicle speed is negative, kinematic integration steps backwards cleanly."""
        self.vehicle.speed = -40.0
        self.vehicle.target_speed = 0.0
        self.vehicle.heading = 0.0  # East
        init_x = self.vehicle.x

        self.vehicle.step(0.1)
        # Vehicle moved West (negative X direction)
        self.assertTrue(self.vehicle.x < init_x)
        self.assertFalse(math.isnan(self.vehicle.x))

    def test_estop_freeze_and_release(self):
        """E-Stop halts vehicle instantly, refuses throttle, and resumes upon release."""
        self.vehicle.set_controls(throttle=1.0, normalized_steer=0.0)
        for _ in range(20):
            self.vehicle.step(0.05)
        self.assertTrue(self.vehicle.speed > 0.0)

        # Trigger E-Stop
        self.vehicle.trigger_estop()
        self.assertEqual(self.vehicle.speed, 0.0)
        self.assertEqual(self.vehicle.driving_state, VehicleDrivingState.ESTOP_FROZEN)

        # Throttle command rejected while E-Stop active
        self.vehicle.set_controls(throttle=1.0, normalized_steer=0.5)
        self.assertEqual(self.vehicle.target_speed, 0.0)
        self.vehicle.step(0.1)
        self.assertEqual(self.vehicle.speed, 0.0)

        # Release E-Stop
        self.vehicle.release_estop()
        self.assertEqual(self.vehicle.driving_state, VehicleDrivingState.LANE_FOLLOW)
        self.vehicle.set_controls(throttle=0.5, normalized_steer=0.0)
        self.vehicle.step(0.1)
        self.assertTrue(self.vehicle.speed > 0.0)


class TestTrackBoundaryDepartures(unittest.TestCase):
    """Stress tests track projection when vehicle departs circuit boundary."""

    def setUp(self):
        self.track = Track()

    def test_vehicle_far_out_of_bounds_origin(self):
        """Querying position (0, 0) far outside track returns nearest valid centerline point."""
        proj_x, proj_y, heading, dist = self.track.get_closest_centerline_point((0.0, 0.0))
        self.assertTrue(0.0 <= proj_x <= ARENA_WIDTH)
        self.assertTrue(0.0 <= proj_y <= ARENA_HEIGHT)
        self.assertTrue(dist > 0.0)
        self.assertFalse(math.isnan(dist))
        self.assertFalse(math.isnan(heading))

    def test_vehicle_extreme_coordinates(self):
        """Extreme coordinates (+10000, -10000) project to finite track point."""
        px, py, h, d = self.track.get_closest_centerline_point((10000.0, -10000.0))
        self.assertFalse(math.isinf(px))
        self.assertFalse(math.isnan(px))
        self.assertFalse(math.isnan(h))
        self.assertTrue(-math.pi <= h <= math.pi + 1e-5)

    def test_arc_center_singularity(self):
        """Point at exact center of East and West arc curves (radius singularity where atan2 is evaluated)."""
        # East curve center
        px_e, py_e, h_e, d_e = self.track.get_closest_centerline_point(EAST_CURVE_CENTER)
        self.assertFalse(math.isnan(px_e))
        self.assertFalse(math.isnan(py_e))
        self.assertFalse(math.isnan(h_e))
        self.assertAlmostEqual(d_e, 150.0, places=2)

        # West curve center
        px_w, py_w, h_w, d_w = self.track.get_closest_centerline_point(WEST_CURVE_CENTER)
        self.assertFalse(math.isnan(px_w))
        self.assertFalse(math.isnan(py_w))
        self.assertFalse(math.isnan(h_w))
        self.assertAlmostEqual(d_w, 150.0, places=2)

    def test_lookahead_projection_extreme_distance(self):
        """Lookahead point projection with extreme lookahead distance (10000 px) remains on track."""
        tx, ty, th = self.track.get_lookahead_point((380.0, 270.0), lookahead_dist=10000.0)
        self.assertFalse(math.isnan(tx))
        self.assertFalse(math.isnan(ty))
        self.assertFalse(math.isnan(th))
        # Point must project onto track circuit
        _, _, _, dist_to_center = self.track.get_closest_centerline_point((tx, ty))
        self.assertAlmostEqual(dist_to_center, 0.0, places=2)


class TestParkingBayAndSensors(unittest.TestCase):
    """Stress tests ParkingBay tuple contract, BeamSensor, and ProximitySensor."""

    def test_parking_bay_tuple_contract(self):
        """ParkingBay must behave as 4-tuple while providing object attributes."""
        bay = ParkingBay("RED", CubeColor.RED, (350, 605, 60, 40), (380.0, 625.0), (220, 20, 25), (380, 625, 60, 40))
        # Tuple unpacking
        x, y, w, h = bay
        self.assertEqual((x, y, w, h), (380, 625, 60, 40))
        self.assertEqual(bay == (380, 625, 60, 40), True)
        self.assertEqual(bay[0], 380)
        self.assertEqual(bay[1], 625)
        self.assertEqual(bay[2], 60)
        self.assertEqual(bay[3], 40)

        # Point containment
        self.assertTrue(bay.contains_point((380.0, 625.0)))
        self.assertFalse(bay.contains_point((0.0, 0.0)))

    def test_beam_sensor_with_picked_and_loaded_cubes(self):
        """BeamSensor must ignore picked, loaded, or delivered cubes."""
        sensor = BeamSensor("S1", (140, 100), (140, 160))
        cube = Cube("RED", x=66.67, y=100.0)  # positioned directly over beam
        self.assertTrue(sensor.evaluate([cube]))

        # Picked cube should be ignored
        cube.is_picked = True
        self.assertFalse(sensor.evaluate([cube]))

        # Loaded cube should be ignored
        cube.is_picked = False
        cube.is_loaded = True
        self.assertFalse(sensor.evaluate([cube]))

        # Delivered cube should be ignored
        cube.is_loaded = False
        cube.state = CubeState.DELIVERED
        self.assertFalse(sensor.evaluate([cube]))

    def test_camera_world_elements_projection_format(self):
        """FactoryWorld.get_camera_world_elements() returns valid metric elements."""
        world = FactoryWorld()
        elems = world.get_camera_world_elements()
        self.assertIn("parking_bays", elems)
        self.assertIn("signs", elems)
        self.assertEqual(len(elems["parking_bays"]), 3)
        self.assertEqual(len(elems["signs"]), 2)
        for sign in elems["signs"]:
            self.assertIn("id", sign)
            self.assertIn("x", sign)
            self.assertIn("y", sign)
            self.assertIn("z", sign)


class TestFuzzStress(unittest.TestCase):
    """Monte Carlo generative fuzz test: 5,000 randomized steps under adversarial conditions."""

    def test_monte_carlo_random_fuzz(self):
        """Fuzz testing with non-negative dt, random control inputs, toggles, and E-Stop."""
        rng = np.random.default_rng(seed=42)
        world = FactoryWorld()
        world.add_cube("RED")
        world.conveyor.is_running = True

        for i in range(5000):
            # Adversarial non-negative dt: mixed zero, micro, normal, large
            dt_choice = float(rng.choice([0.0, 1e-6, 0.016, 0.033, 0.1, 1.0, 10.0]))
            
            # Adversarial vehicle controls
            throttle = float(rng.uniform(-2.0, 5.0))
            steer = float(rng.uniform(-10.0, 10.0))
            world.vehicle.set_controls(throttle, steer)

            # Randomly toggle conveyor running state
            if rng.random() < 0.05:
                world.conveyor.is_running = not world.conveyor.is_running

            # Randomly trigger/release E-stop
            if rng.random() < 0.02:
                if world.vehicle.estop_active:
                    world.reset_estop()
                else:
                    world.apply_estop()

            world.step(dt_choice)

            # Assert invariants: no NaNs, no Infs, finite values
            self.assertFalse(math.isnan(world.vehicle.x), f"Vehicle x is NaN at step {i}")
            self.assertFalse(math.isnan(world.vehicle.y), f"Vehicle y is NaN at step {i}")
            self.assertFalse(math.isnan(world.vehicle.heading), f"Vehicle heading is NaN at step {i}")
            self.assertFalse(math.isinf(world.vehicle.heading), f"Vehicle heading is Inf at step {i}")
            self.assertTrue(-math.pi - 1e-4 <= world.vehicle.heading <= math.pi + 1e-4, f"Heading {world.vehicle.heading} unbounded at step {i}")
            self.assertTrue(0.0 <= world.vehicle.speed <= VEHICLE_MAX_SPEED_PX_S + 1e-4, f"Speed {world.vehicle.speed} unbounded at step {i}")

            if world.conveyor.active_cube:
                self.assertFalse(math.isnan(world.conveyor.active_cube.x), f"Cube x is NaN at step {i}")
                self.assertFalse(math.isnan(world.conveyor.active_cube.position[0]), f"Cube px_x is NaN at step {i}")
                self.assertFalse(math.isnan(world.conveyor.active_cube.position[1]), f"Cube px_y is NaN at step {i}")

    def test_negative_dt_no_crash_execution(self):
        """Negative dt steps backwards without unhandled Python exception or crash."""
        world = FactoryWorld()
        world.add_cube("RED")
        world.conveyor.is_running = True
        world.vehicle.set_controls(throttle=0.5, normalized_steer=0.2)
        world.step(0.5)

        # Step backwards
        try:
            for _ in range(20):
                world.step(-0.016)
        except Exception as e:
            self.fail(f"Negative dt raised unexpected exception: {e}")

        self.assertFalse(math.isnan(world.vehicle.x))
        self.assertFalse(math.isnan(world.vehicle.y))
        self.assertFalse(math.isnan(world.vehicle.heading))

    def test_multiple_cubes_no_crash_handling(self):
        """Adding multiple cubes in rapid succession does not raise exception."""
        belt = ConveyorBelt()
        cubes = [belt.add_cube(c) for c in ["RED", "GREEN", "BLUE", "RED", "GREEN"]]
        self.assertEqual(len(belt.cubes), 5)
        belt.is_running = True
        try:
            for _ in range(50):
                belt.update(0.1)
        except Exception as e:
            self.fail(f"Multiple cubes update raised unexpected exception: {e}")

    def test_randomized_track_departures_fuzz(self):
        """Query 2,000 random coordinates across 100x arena space."""
        rng = np.random.default_rng(seed=123)
        track = Track()

        for _ in range(2000):
            query_x = float(rng.uniform(-10000.0, 10000.0))
            query_y = float(rng.uniform(-10000.0, 10000.0))
            lookahead_dist = float(rng.uniform(-1000.0, 5000.0))

            px, py, h, d = track.get_closest_centerline_point((query_x, query_y))
            self.assertFalse(math.isnan(px))
            self.assertFalse(math.isnan(py))
            self.assertFalse(math.isnan(h))
            self.assertFalse(math.isnan(d))
            self.assertTrue(d >= 0.0)

            tx, ty, th = track.get_lookahead_point((query_x, query_y), lookahead_dist=lookahead_dist)
            self.assertFalse(math.isnan(tx))
            self.assertFalse(math.isnan(ty))
            self.assertFalse(math.isnan(th))


if __name__ == "__main__":
    unittest.main()
