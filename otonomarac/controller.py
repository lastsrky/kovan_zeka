"""
PID kontrolcü: şerit sapmasını direksiyon komutuna çevirir.

Girdi normalize sapma (-1..+1), çıktı normalize direksiyon (-1..+1).
dt gerçek zamanla ölçülür, integral ve çıktı sınırlandırılır.
"""
import time


class PIDController(object):
    def __init__(self, ctrl_cfg):
        self.kp = float(ctrl_cfg.get("kp", 0.9))
        self.ki = float(ctrl_cfg.get("ki", 0.0))
        self.kd = float(ctrl_cfg.get("kd", 0.25))
        self.integral_limit = float(ctrl_cfg.get("integral_limit", 1.0))
        self.output_limit = float(ctrl_cfg.get("output_limit", 1.0))

        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None
        self.p_term = 0.0
        self.i_term = 0.0
        self.d_term = 0.0

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None
        self.p_term = self.i_term = self.d_term = 0.0

    def update(self, error, now=None):
        if now is None:
            now = time.time()

        if self._prev_time is None:
            dt = 0.0
        else:
            dt = now - self._prev_time
        self._prev_time = now

        self.p_term = self.kp * error

        if dt > 0.0:
            self._integral += error * dt
            lim = self.integral_limit
            if self._integral > lim:
                self._integral = lim
            elif self._integral < -lim:
                self._integral = -lim
        self.i_term = self.ki * self._integral

        if dt > 0.0:
            derivative = (error - self._prev_error) / dt
        else:
            derivative = 0.0
        self.d_term = self.kd * derivative
        self._prev_error = error

        output = self.p_term + self.i_term + self.d_term

        lim = self.output_limit
        if output > lim:
            output = lim
        elif output < -lim:
            output = -lim
        return output
