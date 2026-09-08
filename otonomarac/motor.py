"""
ESP8266 motor sürücüsü: aracı fiziksel olarak hareket ettiren katman.

Direksiyon ve gaz komutlarını USB seri üzerinden ESP8266'ya yollar
(S açı / F pwm / B pwm / X dur). Servo açısı mutlak güvenlik sınırlarının
dışına çıkamaz, komutlar hız sınırlamalı gönderilir ve program nasıl
kapanırsa kapansın motor durdurulur.

DummyMotor donanım yokken test içindir.
"""
import atexit
import time

try:
    import serial
except ImportError:
    serial = None


class MotorInterface(object):
    def set_steering(self, deviation, max_delta=None):
        raise NotImplementedError

    def set_throttle(self, speed):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def close(self):
        pass


class DummyMotor(MotorInterface):
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.last_angle = None
        self.last_pwm = None

    def set_steering(self, deviation, max_delta=None):
        if self.verbose:
            print("[dummy] steering dev={:+.2f} md={}".format(
                deviation, max_delta))

    def set_throttle(self, speed):
        if self.verbose:
            print("[dummy] throttle={:.2f}".format(speed))

    def stop(self):
        if self.verbose:
            print("[dummy] STOP")


class SerialMotor(MotorInterface):
    def __init__(self, motor_cfg):
        if serial is None:
            raise RuntimeError(
                "pyserial bulunamadý. Kurulum: pip3 install pyserial")

        self.cfg = motor_cfg
        self.port = motor_cfg.get("port", "/dev/ttyUSB0")
        self.baud = int(motor_cfg.get("baud", 115200))

        self.center = int(motor_cfg.get("steering_center", 110))
        self.max_delta = int(motor_cfg.get("steering_max_delta", 35))
        self.invert = bool(motor_cfg.get("steering_invert", False))
        self.angle_min = self.center - self.max_delta
        self.angle_max = self.center + self.max_delta
        self.hard_min = int(motor_cfg.get(
            "servo_hard_min", self.center - self.max_delta))
        self.hard_max = int(motor_cfg.get(
            "servo_hard_max", self.center + self.max_delta))

        self.throttle_max_pwm = int(motor_cfg.get("throttle_max_pwm", 300))

        self.min_interval = float(
            motor_cfg.get("min_send_interval_ms", 50)) / 1000.0
        self.connect_timeout = float(motor_cfg.get("connect_timeout_s", 2.0))

        self._last_angle = None
        self._last_angle_t = 0.0
        self._last_throttle_cmd = None
        self._last_throttle_t = 0.0

        self.ser = None
        self._closed = False
        self._rx_buffer = ""

        self._connect()
        atexit.register(self._safe_shutdown)

    def _connect(self):
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            timeout=0,
            write_timeout=0.2,
        )
        time.sleep(2.0)
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        if not self._handshake():
            raise RuntimeError(
                "ESP8266 el sýkýþma baþarýsýz: '{}' üzerinden PONG "
                "alýnamadý. Port/baud/kablo kontrol edin.".format(self.port))
        print("[motor] ESP8266 baðlandý: {} @ {}".format(
            self.port, self.baud))

    def _handshake(self):
        self._write_line("PING")
        deadline = time.time() + self.connect_timeout
        while time.time() < deadline:
            line = self._read_line_nonblocking()
            if line is not None:
                if "PONG" in line.upper():
                    return True
            else:
                time.sleep(0.02)
        return False

    def _write_line(self, text):
        if self.ser is None:
            return
        data = (text + "\n").encode("ascii", "ignore")
        try:
            self.ser.write(data)
        except Exception as e:
            print("[motor] yazma hatasý:", e)

    def _read_line_nonblocking(self):
        if self.ser is None:
            return None
        try:
            waiting = self.ser.in_waiting
        except Exception:
            return None
        if waiting:
            try:
                chunk = self.ser.read(waiting)
            except Exception:
                return None
            if chunk:
                self._rx_buffer += chunk.decode("ascii", "ignore")
        if "\n" in self._rx_buffer:
            line, self._rx_buffer = self._rx_buffer.split("\n", 1)
            return line.strip()
        return None

    def drain_responses(self):
        last = None
        for _ in range(10):
            line = self._read_line_nonblocking()
            if line is None:
                break
            if line:
                last = line
        return last

    @staticmethod
    def _clamp(v, lo, hi):
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v

    def deviation_to_angle(self, deviation, max_delta=None):
        md = self.max_delta if max_delta is None else int(max_delta)
        deviation = self._clamp(deviation, -1.0, 1.0)
        if self.invert:
            deviation = -deviation
        angle = self.center + deviation * md
        angle = int(round(angle))
        angle = self._clamp(angle, self.center - md, self.center + md)
        return int(self._clamp(angle, self.hard_min, self.hard_max))

    def set_steering(self, deviation, max_delta=None):
        angle = self.deviation_to_angle(deviation, max_delta)
        now = time.time()
        changed = (angle != self._last_angle)
        due = (now - self._last_angle_t) >= self.min_interval
        if changed or due:
            self._write_line("S {}".format(angle))
            self._last_angle = angle
            self._last_angle_t = now
            self.drain_responses()

    def set_throttle(self, speed):
        speed = self._clamp(speed, 0.0, 1.0)
        if speed <= 0.0:
            self.stop()
            return
        pwm = int(round(speed * self.throttle_max_pwm))
        pwm = int(self._clamp(pwm, 0, 1023))
        cmd = ("F", pwm)
        now = time.time()
        changed = (cmd != self._last_throttle_cmd)
        due = (now - self._last_throttle_t) >= self.min_interval
        if changed or due:
            self._write_line("F {}".format(pwm))
            self._last_throttle_cmd = cmd
            self._last_throttle_t = now
            self.drain_responses()

    def set_reverse(self, speed):
        speed = self._clamp(speed, 0.0, 1.0)
        pwm = int(self._clamp(int(round(speed * self.throttle_max_pwm)),
                              0, 1023))
        cmd = ("B", pwm)
        now = time.time()
        changed = (cmd != self._last_throttle_cmd)
        due = (now - self._last_throttle_t) >= self.min_interval
        if changed or due:
            self._write_line("B {}".format(pwm))
            self._last_throttle_cmd = cmd
            self._last_throttle_t = now
            self.drain_responses()

    def ping(self):
        return self._handshake()

    def stop(self):
        self._write_line("X")
        self._last_throttle_cmd = ("X", 0)
        self._last_throttle_t = time.time()
        self.drain_responses()

    def _safe_shutdown(self):
        if self._closed:
            return
        try:
            if self.ser is not None and self.ser.is_open:
                self._write_line("X")
                time.sleep(0.05)
        except Exception:
            pass
        self._closed = True

    def close(self):
        self._safe_shutdown()
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass


def create_motor(motor_cfg, use_dummy=False):
    if use_dummy:
        return DummyMotor(verbose=False)
    return SerialMotor(motor_cfg)
