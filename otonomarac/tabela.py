"""
Trafik tabelası tespiti (TensorRT).

tabelaguncel.engine modelini yükler ve kareden tabela kutularını döndürür:
yaya geçidi, hemzemin, tümsek, çıkmaz sokak, sollama yasağı sonu, park.
NMS modelin içindedir, ayrıca gerekmez.

Koordinatlar verilen karenin çözünürlüğünde döner.
"""
import os

import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tabelaguncel.engine")
INPUT_SIZE = 640
CONF_THRESH = 0.5

YAYA_ID = 0
HEMZEMIN_ID = 1
TUMSEK_ID = 2
CIKMAZ_ID = 3
SOLLAMA_SONU_ID = 4
PARK_ID = 5

TABELA_ISIM = {
    YAYA_ID: "yaya_gecidi",
    HEMZEMIN_ID: "hemzemin",
    TUMSEK_ID: "tumsek",
    CIKMAZ_ID: "cikmaz_sokak",
    SOLLAMA_SONU_ID: "sollama_yasagi_sonu",
    PARK_ID: "park",
}

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)


def load_engine(engine_path=ENGINE_PATH):
    if not os.path.exists(engine_path):
        raise RuntimeError(
            "tabela engine bulunamadý: {}\n"
            "tabelaguncel.engine dosyasýnýn proje klasöründe olduðundan "
            "emin olun.".format(engine_path))
    with open(engine_path, "rb") as f:
        runtime = trt.Runtime(TRT_LOGGER)
        engine = runtime.deserialize_cuda_engine(f.read())
    if engine is None:
        raise RuntimeError(
            "engine deserialize edilemedi: {}\n"
            "TensorRT sürümü engine'i üretenle uyuþmuyor olabilir "
            "(mevcut: {}).".format(engine_path, trt.__version__))
    return engine


class TabelaDetector(object):
    def __init__(self, engine_path=ENGINE_PATH, conf_thresh=CONF_THRESH):
        self.conf_thresh = float(conf_thresh)
        self.engine = load_engine(engine_path)
        self.context = self.engine.create_execution_context()
        self.stream = cuda.Stream()

        self.input_name = None
        self.output_name = None
        self.input_shape = None
        self.output_shape = None
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            shape = tuple(self.engine.get_tensor_shape(name))
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.input_name = name
                self.input_shape = shape
            else:
                self.output_name = name
                self.output_shape = shape

        self.d_input = cuda.mem_alloc(int(np.prod(self.input_shape)) * 4)
        self.d_output = cuda.mem_alloc(int(np.prod(self.output_shape)) * 4)
        self.h_output = np.empty(self.output_shape, dtype=np.float32)

        self.context.set_tensor_address(self.input_name, int(self.d_input))
        self.context.set_tensor_address(self.output_name, int(self.d_output))

    def infer(self, frame):
        h, w = frame.shape[:2]
        img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = (img / 255.0).astype(np.float32)
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        img = np.ascontiguousarray(img)

        cuda.memcpy_htod_async(self.d_input, img, self.stream)
        self.context.execute_async_v3(stream_handle=self.stream.handle)
        cuda.memcpy_dtoh_async(self.h_output, self.d_output, self.stream)
        self.stream.synchronize()

        dets_raw = self.h_output[0]
        sx = w / float(INPUT_SIZE)
        sy = h / float(INPUT_SIZE)
        results = []
        for det in dets_raw:
            x1, y1, x2, y2, conf, cls_id = det
            if conf < self.conf_thresh:
                continue
            results.append((
                int(x1 * sx), int(y1 * sy),
                int(x2 * sx), int(y2 * sy),
                float(conf), int(cls_id),
            ))
        return results


def draw_tabela(vis, dets, depth=None, depth_scale=None):
    for (x1, y1, x2, y2, conf, cid) in dets:
        isim = TABELA_ISIM.get(cid, "id%d" % cid)
        etiket = "%s %.2f" % (isim, conf)
        if depth is not None and depth_scale:
            roi = depth[max(0, y1):max(1, y2), max(0, x1):max(1, x2)]
            gecerli = roi[roi > 0] if roi.size else roi
            if gecerli.size:
                cm = float(np.median(gecerli)) * depth_scale * 100.0
                etiket += "  %.0fcm" % cm
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(vis, etiket, (x1, max(15, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, etiket, (x1, max(15, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1,
                    cv2.LINE_AA)
    return vis


def main():
    import argparse
    import time

    ap = argparse.ArgumentParser(
        description="Tabela modelini canlý kamerada test et")
    ap.add_argument("--conf", type=float, default=CONF_THRESH,
                    help="güven eþiði (varsayýlan %.2f)" % CONF_THRESH)
    ap.add_argument("--no-depth", action="store_true",
                    help="depth kapat (mesafe gösterilmez)")
    args = ap.parse_args()

    from config_loader import load_config
    from camera import RealSenseCamera

    cfg = load_config()
    cam_cfg = dict(cfg["camera"])
    cam_cfg["crop_top_ratio"] = 0.0
    if args.no_depth:
        cam_cfg["enable_depth"] = False

    print("[tabela] engine yükleniyor: %s" % ENGINE_PATH)
    det = TabelaDetector(conf_thresh=args.conf)
    print("[tabela] hazýr. giriþ=%s çýkýþ=%s" % (det.input_shape,
                                                 det.output_shape))
    print("[tabela] siniflar: %s" % ", ".join(
        "%d=%s" % (k, v) for k, v in sorted(TABELA_ISIM.items())))
    print("[tabela] [q] çýkýþ")

    cam = RealSenseCamera(cam_cfg)
    cam.start()
    fps, t0, n = 0.0, time.time(), 0
    try:
        while True:
            ok, frame, depth = cam.read_with_depth()
            if not ok:
                continue
            dets = det.infer(frame)
            vis = draw_tabela(frame.copy(), dets, depth, cam.depth_scale)

            n += 1
            now = time.time()
            if now - t0 >= 0.5:
                fps = n / (now - t0)
                n, t0 = 0, now
            cv2.putText(vis, "fps %.1f   tespit %d" % (fps, len(dets)),
                        (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3,
                        cv2.LINE_AA)
            cv2.putText(vis, "fps %.1f   tespit %d" % (fps, len(dets)),
                        (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 1, cv2.LINE_AA)
            cv2.imshow("tabela", vis)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()
        print("[tabela] bitti.")


if __name__ == "__main__":
    main()
