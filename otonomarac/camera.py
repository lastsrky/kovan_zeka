"""
RealSense D455 kamerasından kare sağlar.

Her kareyi iki biçimde sunar: şerit takibi için üstten kırpılmış kare,
tabela / trafik ışığı / park için kırpılmamış ham kare. Bunlar kadrajın
üstünde kaldığı için kırpılmış karede görünmezler.

Depth açıkken renge hizalanır; tüm mesafe ölçümleri buna dayanır.
Hizalama başarısız olursa hizasız depth yerine hiç depth verilmez.
"""
import numpy as np

try:
    import pyrealsense2 as rs
except ImportError:
    rs = None


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


class RealSenseCamera(object):

    def __init__(self, cam_cfg):
        if rs is None:
            raise RuntimeError(
                "pyrealsense2 bulunamadý. Kurulum: "
                "pip3 install pyrealsense2")
        self.cfg = cam_cfg
        self.width = int(cam_cfg.get("width", 640))
        self.height = int(cam_cfg.get("height", 480))
        self.fps = int(cam_cfg.get("fps", 30))
        self.crop_top_ratio = float(cam_cfg.get("crop_top_ratio", 0.0))
        self.enable_depth = bool(cam_cfg.get("enable_depth", False))
        self.depth_scale = None
        self.last_depth = None
        self.last_raw_color = None
        self.last_raw_depth = None
        self._align = None
        self._align_hata = 0
        self.pipeline = None
        self.profile = None
        self._started = False

    def start(self):
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, self.width, self.height,
                             rs.format.bgr8, self.fps)
        if self.enable_depth:
            config.enable_stream(rs.stream.depth, self.width, self.height,
                                 rs.format.z16, self.fps)
        self.profile = self.pipeline.start(config)
        if self.enable_depth:
            self._align = rs.align(rs.stream.color)
            try:
                dsensor = self.profile.get_device().first_depth_sensor()
                self.depth_scale = float(dsensor.get_depth_scale())
                print("[camera] depth: ON (scale={:.6f})".format(
                    self.depth_scale))
            except Exception as e:
                print("[camera] depth_scale okunamadý:", e)
        self._apply_exposure()
        self._started = True

    def _apply_exposure(self):
        try:
            color_sensor = self.profile.get_device().first_color_sensor()
        except Exception as e:
            print("[camera] color sensor bulunamadý:", e)
            return

        auto = bool(self.cfg.get("auto_exposure", True))
        if auto:
            if color_sensor.supports(rs.option.enable_auto_exposure):
                color_sensor.set_option(rs.option.enable_auto_exposure, 1)
                print("[camera] auto exposure: ON")
        else:
            if color_sensor.supports(rs.option.enable_auto_exposure):
                color_sensor.set_option(rs.option.enable_auto_exposure, 0)
            exp = float(self.cfg.get("exposure_value", 300))
            gain = float(self.cfg.get("gain", 16))
            if color_sensor.supports(rs.option.exposure):
                color_sensor.set_option(rs.option.exposure, exp)
            if color_sensor.supports(rs.option.gain):
                color_sensor.set_option(rs.option.gain, gain)
            print("[camera] manuel exposure: {}, gain: {}".format(exp, gain))

    def set_exposure(self, exposure_value, gain=None):
        try:
            color_sensor = self.profile.get_device().first_color_sensor()
            if color_sensor.supports(rs.option.enable_auto_exposure):
                color_sensor.set_option(rs.option.enable_auto_exposure, 0)
            if color_sensor.supports(rs.option.exposure):
                color_sensor.set_option(rs.option.exposure,
                                        float(exposure_value))
            if gain is not None and color_sensor.supports(rs.option.gain):
                color_sensor.set_option(rs.option.gain, float(gain))
        except Exception as e:
            print("[camera] set_exposure hatasý:", e)

    def read(self):
        ok, img, _ = self.read_with_depth()
        return ok, img

    def read_with_depth(self):
        if not self._started:
            return False, None, None
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=5000)
        except Exception as e:
            print("[camera] wait_for_frames hatasý:", e)
            return False, None, None
        hizalandi = True
        if self._align is not None:
            try:
                frames = self._align.process(frames)
            except Exception as e:
                hizalandi = False
                self._align_hata += 1
                if self._align_hata <= 3 or self._align_hata % 100 == 0:
                    print("[camera] align hatasý (#{}), bu karede depth "
                          "atlanýyor: {}".format(self._align_hata, e))
        color = frames.get_color_frame()
        if not color:
            return False, None, None
        raw_color = np.asanyarray(color.get_data())
        self.last_raw_color = raw_color
        img = apply_crop(raw_color, self.crop_top_ratio)

        depth_img = None
        self.last_raw_depth = None
        if self.enable_depth and hizalandi:
            depth = frames.get_depth_frame()
            if depth:
                raw_depth = np.asanyarray(depth.get_data())
                self.last_raw_depth = raw_depth
                depth_img = apply_crop(raw_depth, self.crop_top_ratio)
        self.last_depth = depth_img
        return True, img, depth_img

    def stop(self):
        if self.pipeline is not None and self._started:
            try:
                self.pipeline.stop()
            except Exception:
                pass
        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
