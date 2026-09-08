"""
TEKNOFEST 2026 Akıllı Fabrika SITL (Software-in-the-Loop) Vehicle Bridge
Modül: simulator/core/sitl_vehicle_driver.py

Bu sürücü TEKNOFEST'in size gönderdiği orijinal otonomarac/ yazılımlarını
(LineDetector, PIDController, TabelaGorevleri, ColorLink) simülatöre bağlar.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Optional, Tuple, Dict, Any
import numpy as np

from simulator.config import (
    BAY_RED_CENTER, BAY_GREEN_CENTER, BAY_BLUE_CENTER,
    VEHICLE_DOCK_CENTER, TRACK_WAYPOINTS,
    SIGN_PEDESTRIAN_POS, SIGN_PARK_POS,
    VEHICLE_START_SPEED_PX_S, VEHICLE_PARK_SPEED_PX_S,
    VEHICLE_ACCEL_MAX, VEHICLE_DECEL_MAX,
    VEHICLE_STEER_MIN_RAD, VEHICLE_STEER_MAX_RAD,
    VEHICLE_WHEELBASE_PX, VEHICLE_INITIAL_HEADING,
    TOPIC_ARAC_YUK, TOPIC_ROBOT_BASLA,
)
from simulator.core.factory_world import VehicleDrivingState, CubeState
from simulator.core.virtual_cameras import VirtualVehicleCamera


class SITLVehicleDriver:
    """
    TEKNOFEST Otonom Araç yazılımı ile simülatör fiziği arasındaki SITL adaptörü.
    """

    def __init__(self, broker, world=None, use_teknofest_vision: bool = True):
        self.broker = broker
        self.world = world
        self.use_teknofest_vision = use_teknofest_vision

        self.cam = VirtualVehicleCamera(width=640, height=480)

        self.pos_x: float = float(VEHICLE_DOCK_CENTER[0])
        self.pos_y: float = float(VEHICLE_DOCK_CENTER[1])
        self.heading: float = VEHICLE_INITIAL_HEADING
        self.speed: float = 0.0
        self.steer: float = 0.0
        self.state: VehicleDrivingState = VehicleDrivingState.DOCKED
        self.payload_color: Optional[str] = None
        self.mission_complete: bool = False

        self._waypoints = list(TRACK_WAYPOINTS)
        self._wp_idx: int = 0
        self._ped_elapsed: float = 0.0
        self._ped_stop_done: bool = False
        self._park_sign_triggered: bool = False
        self._park_target: Optional[Tuple[float, float]] = None
        self._estop: bool = False
        self.log: list = []

        self.line_detector = None
        self.pid_controller = None
        self._init_teknofest_modules()

        self.broker.subscribe(TOPIC_ARAC_YUK, self._on_mqtt_yuk)
        self.broker.subscribe(TOPIC_ROBOT_BASLA, self._on_mqtt_basla)

    def _init_teknofest_modules(self):
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            otonom_path = os.path.join(repo_root, "otonomarac")
            if otonom_path not in sys.path:
                sys.path.insert(0, otonom_path)

            from config_loader import load_config
            from vision import LineDetector
            from controller import PIDController

            cfg = load_config(os.path.join(otonom_path, "config.yaml"))
            self.line_detector = LineDetector(cfg.get("vision", {}))
            self.pid_controller = PIDController(cfg.get("pid", {}))
            self._log("TEKNOFEST otonomarac modulleri (vision, PID) SITL modunda baglandi.")
        except Exception as e:
            self._log(f"Otonomarac modulleri dahili geometri ile calisacak: {e}")
            self.use_teknofest_vision = False

    def _on_mqtt_yuk(self, topic: str, payload: str):
        color = payload.strip().upper()
        if color in ("RED", "GREEN", "BLUE"):
            self.payload_color = color
            self._log(f"MQTT '{topic}' -> Yuk rengi alindi: {color}")
            if self.state == VehicleDrivingState.DOCKED and not self._estop:
                self._start_mission()

    def _on_mqtt_basla(self, topic: str, payload: str):
        if self.state == VehicleDrivingState.DOCKED and not self._estop:
            self._start_mission()

    def _start_mission(self):
        self._wp_idx = 1
        self.speed = VEHICLE_START_SPEED_PX_S
        self.state = VehicleDrivingState.LANE_FOLLOW
        self._log("Gorev basladi - Arac piste cikti.")

    def update(self, dt: float):
        if self._estop or self.mission_complete:
            self.speed = 0.0
            return

        if self.state == VehicleDrivingState.DOCKED:
            self.speed = 0.0
            return

        target_sign = "pedestrian" if (not self._ped_stop_done) else ("parking" if not self._park_sign_triggered else None)
        raw_bgr, raw_depth = self.cam.render(
            pose=(self.pos_x, self.pos_y, self.heading),
            target_sign=target_sign,
            target_bay=self.payload_color,
        )

        if self.state == VehicleDrivingState.LANE_FOLLOW:
            self._update_lane_follow(dt, raw_bgr)
        elif self.state == VehicleDrivingState.PEDESTRIAN_STOP:
            self._update_pedestrian_stop(dt)
        elif self.state == VehicleDrivingState.PARK_APPROACH:
            self._update_park_approach(dt)
        elif self.state == VehicleDrivingState.PARKED_FINISHED:
            self.speed = 0.0
            self.mission_complete = True
            return

        self._integrate(dt)

    def _update_lane_follow(self, dt: float, raw_bgr: np.ndarray):
        used_vision = False
        if self.use_teknofest_vision and self.line_detector and self.pid_controller:
            try:
                cropped = raw_bgr[140:, :]
                det = self.line_detector.detect(cropped)
                if det and hasattr(det, "deviation") and det.deviation is not None:
                    steer_cmd = self.pid_controller.update(det.deviation, dt)
                    self.steer = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, math.radians(steer_cmd)))
                    used_vision = True
            except Exception:
                pass

        if not used_vision:
            if self._wp_idx < len(self._waypoints):
                target = self._waypoints[self._wp_idx]
                dx = target[0] - self.pos_x
                dy = target[1] - self.pos_y
                if math.hypot(dx, dy) < 22.0:
                    self._wp_idx += 1
                if self._wp_idx < len(self._waypoints):
                    target = self._waypoints[self._wp_idx]
                    desired_h = math.atan2(target[1] - self.pos_y, target[0] - self.pos_x)
                    diff = self._wrap_angle(desired_h - self.heading)
                    self.steer = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, 0.045 * diff * 20.0))

        self.speed = min(self.speed + VEHICLE_ACCEL_MAX * dt, VEHICLE_START_SPEED_PX_S)
        self._check_signs()

    def _update_pedestrian_stop(self, dt: float):
        self.speed = max(0.0, self.speed - VEHICLE_DECEL_MAX * dt)
        self._ped_elapsed += dt
        if self._ped_elapsed >= 2.0:
            self._log("Yaya gecidinde beklendi, yola devam ediliyor.")
            self.state = VehicleDrivingState.LANE_FOLLOW

    def _update_park_approach(self, dt: float):
        if self._park_target is None:
            bay_map = {
                "RED": (float(BAY_RED_CENTER[0]), float(BAY_RED_CENTER[1])),
                "GREEN": (float(BAY_GREEN_CENTER[0]), float(BAY_GREEN_CENTER[1])),
                "BLUE": (float(BAY_BLUE_CENTER[0]), float(BAY_BLUE_CENTER[1])),
            }
            color = self.payload_color or "RED"
            self._park_target = bay_map.get(color, bay_map["RED"])

        tx, ty = self._park_target
        dx = tx - self.pos_x
        dy = ty - self.pos_y
        dist = math.hypot(dx, dy)

        if dist < 18.0:
            self.pos_x, self.pos_y = tx, ty
            self.speed = 0.0
            self.state = VehicleDrivingState.PARKED_FINISHED
            self._log(f"Park Basarili: {self.payload_color} cebine tam yanasildi.")
            return

        desired_h = math.atan2(dy, dx)
        diff = self._wrap_angle(desired_h - self.heading)
        self.steer = max(VEHICLE_STEER_MIN_RAD, min(VEHICLE_STEER_MAX_RAD, 0.045 * diff * 25.0))
        target_spd = VEHICLE_PARK_SPEED_PX_S * min(1.0, dist / 80.0)
        if self.speed > target_spd:
            self.speed = max(target_spd, self.speed - VEHICLE_DECEL_MAX * dt)
        else:
            self.speed = min(target_spd, self.speed + VEHICLE_ACCEL_MAX * dt)

    def _check_signs(self):
        if not self._ped_stop_done:
            if math.hypot(self.pos_x - SIGN_PEDESTRIAN_POS[0], self.pos_y - SIGN_PEDESTRIAN_POS[1]) < 60.0:
                self._log("Yaya gecidi tabelasi algilandi -> Duruluyor.")
                self.state = VehicleDrivingState.PEDESTRIAN_STOP
                self._ped_elapsed = 0.0
                self._ped_stop_done = True
                return

        if not self._park_sign_triggered:
            if math.hypot(self.pos_x - SIGN_PARK_POS[0], self.pos_y - SIGN_PARK_POS[1]) < 60.0:
                self._log("Park tabelasi algilandi -> Park yaklasimina gecildi.")
                self._park_sign_triggered = True
                self.state = VehicleDrivingState.PARK_APPROACH

    def _integrate(self, dt: float):
        if abs(self.steer) < 1e-6:
            self.pos_x += self.speed * math.cos(self.heading) * dt
            self.pos_y += self.speed * math.sin(self.heading) * dt
        else:
            r = VEHICLE_WHEELBASE_PX / math.tan(self.steer)
            w = self.speed / r
            self.heading = self._wrap_angle(self.heading + w * dt)
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

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def emergency_stop(self):
        self._estop = True
        self.speed = 0.0
        self.state = VehicleDrivingState.ESTOP_FROZEN

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

    @property
    def is_docked(self) -> bool:
        return self.state == VehicleDrivingState.DOCKED

    @property
    def is_parked(self) -> bool:
        return self.state == VehicleDrivingState.PARKED_FINISHED

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "pos_x": round(self.pos_x, 1),
            "pos_y": round(self.pos_y, 1),
            "heading_deg": round(math.degrees(self.heading), 1),
            "speed_px_s": round(self.speed, 1),
            "steer_deg": round(math.degrees(self.steer), 1),
            "payload_color": self.payload_color,
            "park_sign_triggered": self._park_sign_triggered,
            "mission_complete": self.mission_complete,
            "estop": self._estop,
        }

    def _log(self, msg: str):
        self.log.append(msg)
        print(f"[SITL-Vehicle] {msg}")
