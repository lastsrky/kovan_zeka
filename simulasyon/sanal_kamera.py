import numpy as np
import cv2
from simulasyon.sanal_ortam import SanalOrtam

def apply_crop(img, crop_top_ratio):
    if img is None:
        return None
    r = float(crop_top_ratio or 0.0)
    if r <= 0.0:
        return img
    if r > 0.9:
        r = 0.9
    h = img.shape[0]
    y0 = int(h * r)
    return img[y0:, :]

class SanalKamera:
    def __init__(self, cam_cfg):
        self.cfg = cam_cfg
        self.width = int(cam_cfg.get("width", 640))
        self.height = int(cam_cfg.get("height", 480))
        self.crop_top_ratio = float(cam_cfg.get("crop_top_ratio", 0.0))
        self.enable_depth = bool(cam_cfg.get("enable_depth", False))
        
        self.depth_scale = 0.001
        self.last_depth = None
        self.last_raw_color = None
        self.last_raw_depth = None
        self._started = False
        self.ortam = SanalOrtam()

    def start(self):
        self._started = True
        print("[sanal_kamera] Baslatildi")

    def set_exposure(self, exposure_value, gain=None):
        pass

    def read(self):
        ok, img, _ = self.read_with_depth()
        return ok, img

    def read_with_depth(self):
        if not self._started:
            return False, None, None

        # Sanal ortamdan frame al
        frame = self.ortam.get_camera_view(self.width, self.height)
        self.last_raw_color = frame.copy()
        
        img = apply_crop(self.last_raw_color, self.crop_top_ratio)
        
        depth_img = None
        self.last_raw_depth = None
        if self.enable_depth:
            # Mock depth frame (Mesafe simulasyonu: alttan uste dogru artan degerler)
            self.last_raw_depth = np.zeros((self.height, self.width), dtype=np.uint16)
            for y in range(self.height):
                dist = int((self.height - y) * 10) # Basit bir mesafe hesabi
                self.last_raw_depth[y, :] = dist
            depth_img = apply_crop(self.last_raw_depth, self.crop_top_ratio)
            
        self.last_depth = depth_img
        return True, img, depth_img

    def stop(self):
        self._started = False
        print("[sanal_kamera] Durduruldu")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
