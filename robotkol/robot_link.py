"""
Arduino ile seri haberleşme: kolu fiziksel olarak hareket ettiren katman.

Komutlar adım (step) cinsinden gider, açı-adım dönüşümü burada yapılır.
Arduino yaklaşık 50 ms'de bir durum satırı yollar; hareket bitişi, homing
sonucu ve acil dur olayları buradan okunur.

Eklem sırası: 0=Taban 1=Omuz 2=Dirsek 3=Bilek
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

import serial
import serial.tools.list_ports


DEFAULT_PORT = "/dev/ttyCH341USB0"
DEFAULT_BAUD = 115200

JOINT_NAMES = ("Taban", "Omuz", "Dirsek", "Bilek")

MICROSTEP   = 800
REDUCTION   = (28.4, 28.4, 28.4, 19.0)
STEPS_PER_DEG = tuple(MICROSTEP * r / 360.0 for r in REDUCTION)

HOMING_DIRS = (-1, -1, -1, +1)

LIMITS_DEG = ((-170.0, 170.0),
              (-148.0, 120.0),
              (-150.0, 147.0),
              (-90.0,   50.0))

DEFAULT_SPEED_STEPS = 1000
DEFAULT_ACCEL_STEPS = 800

JOG_STEP_DEG   = 2.0
GRIP_OPEN      = 0
GRIP_CLOSE     = 74
GRIP_DEFAULT   = 0
GRIP_MAX       = 74


def deg_to_steps(joint: int, deg: float) -> int:
    return int(round(deg * STEPS_PER_DEG[joint]))


def steps_to_deg(joint: int, steps: float) -> float:
    return steps / STEPS_PER_DEG[joint]


@dataclass
class RobotState:
    steps:       List[int]   = field(default_factory=lambda: [0, 0, 0, 0])
    angles:      List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    gripper:     int  = GRIP_DEFAULT
    moving:      bool = False
    homed_mask:  int  = 0
    limits_mask: int  = 0
    basla:       int  = 0
    estop:       bool = False
    connected:   bool = False
    last_event:  str  = ""


class RobotLink:
    def __init__(self, port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self.ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self.state = RobotState()
        self.log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue(maxsize=2000)

    @staticmethod
    def list_ports() -> List[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.2)
            time.sleep(2.0)
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            with self._lock:
                self.state.connected = True
                self.state.estop = False
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            self._log("INFO", f"Baglandi: {self.port} @ {self.baud}")
            self.send_raw("PING")
            self.set_motion(DEFAULT_SPEED_STEPS, DEFAULT_ACCEL_STEPS)
            self.set_homing_dirs(HOMING_DIRS)
            return True
        except Exception as e:
            self._log("ERR", f"Baglanti hatasi: {e}")
            return False

    def disconnect(self) -> None:
        self._running = False
        try:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        with self._lock:
            self.state.connected = False
        self._log("INFO", "Baglanti kapatildi")

    def is_connected(self) -> bool:
        with self._lock:
            return self.state.connected

    def send_raw(self, cmd: str) -> bool:
        if not self.is_connected() or not self.ser:
            self._log("ERR", "Baglanti yok: " + cmd)
            return False
        if not cmd.endswith("\n"):
            cmd += "\n"
        try:
            self.ser.write(cmd.encode("ascii", errors="replace"))
            self._log("TX", cmd.strip())
            return True
        except Exception as e:
            self._log("ERR", f"Yazim hatasi: {e}")
            return False

    def _read_loop(self) -> None:
        buf = b""
        while self._running:
            try:
                if not self.ser:
                    break
                data = self.ser.read(128)
                if data:
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode("ascii", errors="replace").strip()
                        if text:
                            self._parse(text)
                else:
                    time.sleep(0.002)
            except Exception as e:
                self._log("ERR", f"Okuma hatasi: {e}")
                self._running = False
                with self._lock:
                    self.state.connected = False
                break

    def _parse(self, line: str) -> None:
        if line.startswith("STA "):
            parts = line.split()
            try:
                steps = [int(parts[1 + i]) for i in range(4)]
                grip  = int(parts[5])
                moving = bool(int(parts[6]))
                homed = int(parts[7])
                limits = int(parts[8]) if len(parts) > 8 else 0
                basla = int(parts[9]) if len(parts) > 9 else 0
                with self._lock:
                    self.state.steps = steps
                    self.state.angles = [steps_to_deg(i, steps[i]) for i in range(4)]
                    self.state.gripper = grip
                    self.state.moving = moving
                    self.state.homed_mask = homed
                    self.state.limits_mask = limits
                    self.state.basla = basla
            except Exception:
                pass
            return

        self._log("RX", line)
        if line.startswith("EVT "):
            evt = line[4:]
            with self._lock:
                self.state.last_event = evt
                if evt == "ESTOP":
                    self.state.estop = True
                elif evt == "MOVE_DONE":
                    self.state.moving = False
        elif line == "READY":
            with self._lock:
                self.state.last_event = "READY"
                self.state.estop = False

    def _log(self, kind: str, text: str) -> None:
        try:
            self.log_queue.put_nowait((kind, text))
        except queue.Full:
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait((kind, text))
            except Exception:
                pass

    def set_motion(self, speed_steps: float, accel_steps: float) -> bool:
        return self.send_raw(f"S {int(speed_steps)} {int(accel_steps)}")

    def set_homing_dirs(self, dirs=HOMING_DIRS) -> bool:
        mask = 0
        for i, d in enumerate(dirs):
            if d > 0:
                mask |= (1 << i)
        return self.send_raw(f"D {mask}")

    def home(self, joint: Optional[int] = None) -> bool:
        if joint is None:
            mask = 0x0F
        else:
            mask = (1 << joint)
        return self.send_raw(f"H {mask}")

    SWITCH_MARJ_DEG = 0.0

    def _switch_sinirla(self, angles: List[float]) -> List[float]:
        out = list(angles)
        kirpildi = []
        for j in range(4):
            if HOMING_DIRS[j] < 0:
                if out[j] < self.SWITCH_MARJ_DEG:
                    out[j] = self.SWITCH_MARJ_DEG
                    kirpildi.append(j)
            else:
                if out[j] > -self.SWITCH_MARJ_DEG:
                    out[j] = -self.SWITCH_MARJ_DEG
                    kirpildi.append(j)
        if kirpildi:
            isimler = ", ".join(JOINT_NAMES[j] for j in kirpildi)
            self._log("ERR", f"Switch siniri: {isimler} home switch'ini gecemez (kirpildi)")
        return out

    def move_deg(self, angles: List[float]) -> bool:
        angles = self._switch_sinirla(angles)
        steps = [deg_to_steps(i, angles[i]) for i in range(4)]
        return self.send_raw("M " + " ".join(str(s) for s in steps))

    def move_steps(self, steps: List[int]) -> bool:
        return self.send_raw("M " + " ".join(str(int(s)) for s in steps))

    def jog_deg(self, joint: int, delta_deg: float) -> bool:
        delta = deg_to_steps(joint, delta_deg)
        return self.send_raw(f"J {joint + 1} {delta}")

    def calibrate_here(self, steps=(0, 0, 0, 0)) -> bool:
        return self.send_raw("C " + " ".join(str(int(s)) for s in steps))

    def grip(self, angle: int) -> bool:
        a = max(0, min(int(angle), GRIP_MAX))
        return self.send_raw(f"G {a}")

    def pause(self) -> bool:
        return self.send_raw("P")

    def resume(self) -> bool:
        with self._lock:
            self.state.estop = False
        return self.send_raw("R")

    def estop(self) -> bool:
        with self._lock:
            self.state.estop = True
        return self.send_raw("X")

    def snapshot(self) -> RobotState:
        with self._lock:
            s = self.state
            return RobotState(
                steps=list(s.steps),
                angles=list(s.angles),
                gripper=s.gripper,
                moving=s.moving,
                homed_mask=s.homed_mask,
                limits_mask=s.limits_mask,
                basla=s.basla,
                estop=s.estop,
                connected=s.connected,
                last_event=s.last_event,
            )
