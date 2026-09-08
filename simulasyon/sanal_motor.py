from simulasyon.sanal_ortam import SanalOrtam

class SanalMotor:
    def __init__(self, cfg=None):
        self.ortam = SanalOrtam()
        self.current_throttle = 0.0
        self.current_steer = 0.0
        print("[sanal_motor] Baslatildi")

    def set_steering(self, val):
        self.current_steer = val
        # Val genelde -1.0 ile 1.0 arasi bir error degeri (sapma)
        # PWM = 300 icin hiz 300, steer etkisini guncelle
        self.ortam.update_motor(self.current_throttle * 300, self.current_steer)

    def set_throttle(self, val):
        self.current_throttle = val
        self.ortam.update_motor(self.current_throttle * 300, self.current_steer)

    def stop(self):
        self.current_throttle = 0.0
        self.current_steer = 0.0
        self.ortam.update_motor(0.0, 0.0)

    def close(self):
        self.stop()
        self.ortam.stop()
        print("[sanal_motor] Kapandi")
