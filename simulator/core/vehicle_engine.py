from __future__ import annotations
import math
import time
from typing import Optional, Tuple

from simulator.config import (
    BAY_RED_CENTER, BAY_GREEN_CENTER, BAY_BLUE_CENTER,
    VEHICLE_DOCK_CENTER, TRACK_WAYPOINTS,
    SIGN_PEDESTRIAN_POS, SIGN_PARK_POS,
    VEHICLE_START_SPEED_PX_S, VEHICLE_PARK_SPEED_PX_S,
    VEHICLE_ACCEL_MAX, VEHICLE_DECEL_MAX,
    VEHICLE_STEER_MIN_RAD, VEHICLE_STEER_MAX_RAD,
    VEHICLE_WHEELBASE_PX, VEHICLE_INITIAL_HEADING,
    TOPIC_ARAC_YUK,
)
from simulator.core.factory_world import VehicleDrivingState, CubeState

PEDESTRIAN_STOP_DURATION_S = 2.0
PARK_TOLERANCE_PX = 18.0
WAYPOINT_REACH_PX = 22.0
SIGN_TRIGGER_DIST_PX = 60.0
LANE_P_GAIN = 0.045


def _wrap_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def _angle_diff(target, current):
    return _wrap_angle(target - current)


class VehicleEngine:
    def __init__(self, broker, world=None):
        self.broker = broker
        self.world = world
        self.pos_x = float(VEHICLE_DOCK_CENTER[0])
        self.pos_y = float(VEHICLE_DOCK_CENTER[1])
        self.heading = VEHICLE_INITIAL_HEADING
        self.speed = 0.0
        self.steer = 0.0
        self.state = VehicleDrivingState.DOCKED
        self.payload_color = None
        self.mission_complete = False
        self._waypoints = list(TRACK_WAYPOINTS)
        self._wp_idx = 0
        self._ped_stop_start = 0.0
        self._ped_elapsed = 0.0
        self._ped_stop_done = False
        self._park_sign_triggered = False
        self._park_target = None
        self._estop = False
        self.log = []
        self.broker.subscribe(TOPIC_ARAC_YUK, self._on_mqtt_yuk)

    def _on_mqtt_yuk(self, topic, payload):
        color = payload.strip().upper()
        if color in ('RED', 'GREEN', 'BLUE'):
            self.payload_color = color
            self._log('MQTT arac/yuk -> renk alindi: ' + color)
            if self.state == VehicleDrivingState.DOCKED and not self._estop:
                self._start_mission()

    def _start_mission(self):
        self._wp_idx = 1
        self.speed = VEHICLE_START_SPEED_PX_S
        self.state = VehicleDrivingState.LANE_FOLLOW
        self._log('Gorev basladi - LANE_FOLLOW moduna gecildi.')

    def update(self, dt):
        if self._estop or self.mission_complete:
            self.speed = 0.0
            return
        if self.state == VehicleDrivingState.DOCKED:
            self.speed = 0.0
            return
        if self.state == VehicleDrivingState.LANE_FOLLOW:
            self._update_lane_follow(dt)
        elif self.state == VehicleDrivingState.PEDESTRIAN_STOP:
            self._update_pedestrian_stop(dt)
        elif self.state == VehicleDrivingState.PARK_APPROACH:
            self._update_park_approach(dt)
        elif self.state == VehicleDrivingState.PARKED_FINISHED:
            self.speed = 0.0
            self.mission_complete = True
            return
        self._integrate(dt)

    def _update_lane_follow(self, dt):
        if self._wp_idx >= len(self._waypoints):
            self._wp_idx = len(self._waypoints) - 1
            return
        target = self._waypoints[self._wp_idx]
        dx = target[0] - self.pos_x
        dy = target[1] - self.pos_y
        dist = math.hypot(dx, dy)
        if dist < WAYPOINT_REACH_PX:
            self._log('Waypoint ' + str(self._wp_idx) + ' gecildi.')
            self._wp_idx += 1
            if self._wp_idx >= len(self._waypoints):
                return
        target = self._waypoints[self._wp_idx]
        dx = target[0] - self.pos_x
        dy = target[1] - self.pos_y
        desired_heading = math.atan2(dy, dx)
        heading_err = _angle_diff(desired_heading, self.heading)
        self.steer = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, LANE_P_GAIN * heading_err * 20.0))
        self.speed = min(self.speed + VEHICLE_ACCEL_MAX * dt, VEHICLE_START_SPEED_PX_S)
        self._check_signs()

    def _update_pedestrian_stop(self, dt):
        self.speed = max(0.0, self.speed - VEHICLE_DECEL_MAX * dt)
        self._ped_elapsed += dt
        if self._ped_elapsed >= PEDESTRIAN_STOP_DURATION_S:
            self._log('Yaya beklendi, devam ediliyor.')
            self.state = VehicleDrivingState.LANE_FOLLOW

    def _update_park_approach(self, dt):
        if self._park_target is None:
            self._resolve_park_target()
        if self._park_target is None:
            self.speed = 0.0
            return
        tx, ty = self._park_target
        dx = tx - self.pos_x
        dy = ty - self.pos_y
        dist = math.hypot(dx, dy)
        if dist < PARK_TOLERANCE_PX:
            self.pos_x = tx
            self.pos_y = ty
            self.speed = 0.0
            self.state = VehicleDrivingState.PARKED_FINISHED
            self._log('Park tamamlandi - ' + str(self.payload_color) + ' bay.')
            if self.world is not None:
                self._deliver_cube()
            return
        desired_heading = math.atan2(dy, dx)
        heading_err = _angle_diff(desired_heading, self.heading)
        self.steer = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, LANE_P_GAIN * heading_err * 25.0))
        target_speed = VEHICLE_PARK_SPEED_PX_S * min(1.0, dist / 80.0)
        if self.speed > target_speed:
            self.speed = max(target_speed, self.speed - VEHICLE_DECEL_MAX * dt)
        else:
            self.speed = min(target_speed, self.speed + VEHICLE_ACCEL_MAX * dt)

    def _resolve_park_target(self):
        bay_map = {
            'RED':   (float(BAY_RED_CENTER[0]),   float(BAY_RED_CENTER[1])),
            'GREEN': (float(BAY_GREEN_CENTER[0]), float(BAY_GREEN_CENTER[1])),
            'BLUE':  (float(BAY_BLUE_CENTER[0]),  float(BAY_BLUE_CENTER[1])),
        }
        color = self.payload_color or 'RED'
        self._park_target = bay_map.get(color, bay_map['RED'])
        self._log('Park hedefi: ' + color + ' -> ' + str(self._park_target))

    def _deliver_cube(self):
        try:
            for cube in self.world.cubes_on_vehicle:
                cube.state = CubeState.DELIVERED
                cube.is_loaded = False
                self._log('Kup teslim edildi: ' + cube.color)
        except Exception:
            pass

    def _check_signs(self):
        if not self._ped_stop_done:
            ped_dist = math.hypot(self.pos_x - SIGN_PEDESTRIAN_POS[0], self.pos_y - SIGN_PEDESTRIAN_POS[1])
            if ped_dist < SIGN_TRIGGER_DIST_PX:
                self._log('Yaya gecidi tabelasi algilandi.')
                self.state = VehicleDrivingState.PEDESTRIAN_STOP
                self._ped_stop_start = 0.0
                self._ped_elapsed = 0.0
                self._ped_stop_done = True
                return
        if not self._park_sign_triggered:
            park_dist = math.hypot(self.pos_x - SIGN_PARK_POS[0], self.pos_y - SIGN_PARK_POS[1])
            if park_dist < SIGN_TRIGGER_DIST_PX:
                self._log('Park tabelasi algilandi.')
                self._park_sign_triggered = True
                self.state = VehicleDrivingState.PARK_APPROACH

    def _integrate(self, dt):
        if abs(self.steer) < 1e-6:
            self.pos_x += self.speed * math.cos(self.heading) * dt
            self.pos_y += self.speed * math.sin(self.heading) * dt
        else:
            turn_radius = VEHICLE_WHEELBASE_PX / math.tan(self.steer)
            angular_velocity = self.speed / turn_radius
            self.heading = _wrap_angle(self.heading + angular_velocity * dt)
            self.pos_x += self.speed * math.cos(self.heading) * dt
            self.pos_y += self.speed * math.sin(self.heading) * dt
        self.pos_x = max(50.0, min(self.pos_x, 990.0))
        self.pos_y = max(50.0, min(self.pos_y, 850.0))

        # Synchronize with FactoryWorld.vehicle so renderer displays motion
        if self.world and hasattr(self.world, "vehicle") and self.world.vehicle:
            wveh = self.world.vehicle
            wveh.x = self.pos_x
            wveh.y = self.pos_y
            wveh.heading = self.heading
            wveh.speed = self.speed
            wveh.steering_angle = self.steer
            wveh.driving_state = self.state
            if wveh.loaded_cube:
                wveh.loaded_cube.update_carried((self.pos_x, self.pos_y, self.heading), offset=wveh.bed_offset)

    def emergency_stop(self):
        self._estop = True
        self.speed = 0.0
        self.state = VehicleDrivingState.ESTOP_FROZEN
        self._log('E-STOP: arac donduruldu.')

    def reset_estop(self):
        self._estop = False
        self.state = VehicleDrivingState.DOCKED
        self.pos_x = float(VEHICLE_DOCK_CENTER[0])
        self.pos_y = float(VEHICLE_DOCK_CENTER[1])
        self.heading = VEHICLE_INITIAL_HEADING
        self.speed = 0.0
        self.steer = 0.0
        self.payload_color = None
        self.mission_complete = False
        self._park_sign_triggered = False
        self._park_target = None
        self._ped_stop_done = False
        self._ped_elapsed = 0.0
        self._wp_idx = 0
        self._log('E-Stop kaldirildi - DOCKED konumuna dondu.')

    def full_reset(self):
        self._estop = False
        self.reset_estop()
        self.log.clear()

    @property
    def pose(self):
        return (self.pos_x, self.pos_y, self.heading)

    @property
    def is_docked(self):
        return self.state == VehicleDrivingState.DOCKED

    @property
    def is_parked(self):
        return self.state == VehicleDrivingState.PARKED_FINISHED

    @property
    def is_estop(self):
        return self._estop

    def get_telemetry(self):
        return {
            'state': self.state.value,
            'pos_x': round(self.pos_x, 1),
            'pos_y': round(self.pos_y, 1),
            'heading_deg': round(math.degrees(self.heading), 1),
            'speed_px_s': round(self.speed, 1),
            'steer_deg': round(math.degrees(self.steer), 1),
            'payload_color': self.payload_color,
            'park_sign_triggered': self._park_sign_triggered,
            'mission_complete': self.mission_complete,
            'estop': self._estop,
        }

    def _log(self, msg):
        entry = '[' + time.strftime('%H:%M:%S') + '] [VehicleEngine] ' + msg
        self.log.append(entry)
        print(entry)
