#!/usr/bin/env python3
"""
Küpün rengini bulur: HSV ve ROI ile kırmızı / mavi / yeşil ayrımı.

Model yoktur. Konveyörde duran küpün üstündeki sabit bir dikdörtgenin içinde
baskın rengi arar, kararı maskedeki piksel oranından verir. Emin değilse
UNKNOWN döner ve kol hareket etmez.

ROI ve eşik değerleri renk_kalibrasyon.json dosyasında tutulur.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


HERE = os.path.dirname(os.path.abspath(__file__))
CALIB_PATH = os.path.join(HERE, "renk_kalibrasyon.json")

RENKLER = ("RED", "GREEN", "BLUE")
BILINMIYOR = "UNKNOWN"

VARSAYILAN_HSV: Dict[str, List[List[List[int]]]] = {
    "RED":   [[[0, 100, 70], [10, 255, 255]],
              [[170, 100, 70], [179, 255, 255]]],
    "GREEN": [[[40, 70, 55], [85, 255, 255]]],
    "BLUE":  [[[95, 90, 55], [130, 255, 255]]],
}

VARSAYILAN_ROI = {"x": 240, "y": 160, "w": 160, "h": 160}

VARSAYILAN_DOLULUK = 0.40
VARSAYILAN_MARJ     = 0.12


@dataclass
class RenkKalibrasyon:
    roi: Dict[str, int] = field(default_factory=lambda: dict(VARSAYILAN_ROI))
    hsv: Dict[str, List[List[List[int]]]] = field(
        default_factory=lambda: {k: [[list(a), list(b)] for a, b in v]
                                 for k, v in VARSAYILAN_HSV.items()})
    doluluk_esigi: float = VARSAYILAN_DOLULUK
    marj: float = VARSAYILAN_MARJ

    @classmethod
    def yukle(cls, path: str = CALIB_PATH) -> "RenkKalibrasyon":
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r") as f:
                d = json.load(f)
            return cls(
                roi=d.get("roi", dict(VARSAYILAN_ROI)),
                hsv=d.get("hsv", {k: [[list(a), list(b)] for a, b in v]
                                  for k, v in VARSAYILAN_HSV.items()}),
                doluluk_esigi=float(d.get("doluluk_esigi", VARSAYILAN_DOLULUK)),
                marj=float(d.get("marj", VARSAYILAN_MARJ)),
            )
        except Exception as e:
            print(f"[renk] Kalibrasyon okunamadi ({e}), varsayilan kullaniliyor.")
            return cls()

    def kaydet(self, path: str = CALIB_PATH) -> None:
        with open(path, "w") as f:
            json.dump({
                "roi": self.roi,
                "hsv": self.hsv,
                "doluluk_esigi": self.doluluk_esigi,
                "marj": self.marj,
            }, f, indent=2)


def hsv_araligi_ogren(roi_bgr: np.ndarray, h_pad: int = 10,
                      s_min: int = 70, v_min: int = 55) -> List[List[List[int]]]:
    hsv = cv2.cvtColor(cv2.GaussianBlur(roi_bgr, (5, 5), 0), cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0].astype(np.float32)
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]
    mask = (S > s_min) & (V > v_min)
    hs = H[mask]
    if hs.size < 50:
        hs = H.flatten()
    ang = hs * (2.0 * np.pi / 180.0)
    med = np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())
    med_h = int(round((med % (2 * np.pi)) * 180.0 / (2 * np.pi))) % 180

    lo = med_h - h_pad
    hi = med_h + h_pad
    smin = int(max(50, np.percentile(S[mask], 15) - 25)) if hs.size >= 50 else s_min
    vmin = int(max(45, np.percentile(V[mask], 15) - 25)) if hs.size >= 50 else v_min

    def R(a, b):
        return [[int(a), smin, vmin], [int(b), 255, 255]]

    if lo < 0:
        return [R(0, hi), R(180 + lo, 179)]
    if hi > 179:
        return [R(lo, 179), R(0, hi - 180)]
    return [R(lo, hi)]


@dataclass
class RenkSonuc:
    renk: str
    oranlar: Dict[str, float]
    doluluk: float
    emin: bool


def _roi_kirp(frame: np.ndarray, roi: Dict[str, int]) -> np.ndarray:
    h, w = frame.shape[:2]
    x = max(0, min(int(roi["x"]), w - 1))
    y = max(0, min(int(roi["y"]), h - 1))
    rw = max(1, min(int(roi["w"]), w - x))
    rh = max(1, min(int(roi["h"]), h - y))
    return frame[y:y + rh, x:x + rw]


def _renk_maskesi(hsv_img: np.ndarray, araliklar: List[List[List[int]]]) -> np.ndarray:
    toplam = None
    for alt, ust in araliklar:
        m = cv2.inRange(hsv_img, np.array(alt, np.uint8), np.array(ust, np.uint8))
        toplam = m if toplam is None else cv2.bitwise_or(toplam, m)
    return toplam


class RenkAlgilayici:
    def __init__(self, kalib: Optional[RenkKalibrasyon] = None):
        self.kalib = kalib or RenkKalibrasyon.yukle()

    def algila(self, frame_bgr: np.ndarray) -> RenkSonuc:
        roi = _roi_kirp(frame_bgr, self.kalib.roi)
        roi = cv2.GaussianBlur(roi, (5, 5), 0)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        toplam_px = roi.shape[0] * roi.shape[1]

        oranlar: Dict[str, float] = {}
        for renk in RENKLER:
            araliklar = self.kalib.hsv.get(renk, VARSAYILAN_HSV[renk])
            mask = _renk_maskesi(hsv, araliklar)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                    np.ones((3, 3), np.uint8))
            oranlar[renk] = float(cv2.countNonZero(mask)) / float(toplam_px)

        sirali = sorted(oranlar.items(), key=lambda kv: kv[1], reverse=True)
        kazanan, k_oran = sirali[0]
        ikinci_oran = sirali[1][1] if len(sirali) > 1 else 0.0

        emin = (k_oran >= self.kalib.doluluk_esigi
                and (k_oran - ikinci_oran) >= self.kalib.marj)
        return RenkSonuc(
            renk=kazanan if emin else BILINMIYOR,
            oranlar=oranlar,
            doluluk=k_oran,
            emin=emin,
        )

    def kutu_var_mi(self, frame_bgr: np.ndarray) -> bool:
        s = self.algila(frame_bgr)
        return s.doluluk >= self.kalib.doluluk_esigi

    def roi_ciz(self, frame_bgr: np.ndarray, sonuc: Optional[RenkSonuc] = None) -> np.ndarray:
        img = frame_bgr.copy()
        r = self.kalib.roi
        renk_bgr = {"RED": (0, 0, 255), "GREEN": (0, 200, 0),
                    "BLUE": (255, 0, 0), BILINMIYOR: (60, 60, 60)}
        etiket = sonuc.renk if sonuc else ""
        cizgi = renk_bgr.get(etiket, (0, 255, 255))
        cv2.rectangle(img, (r["x"], r["y"]),
                      (r["x"] + r["w"], r["y"] + r["h"]), cizgi, 2)
        if sonuc:
            txt = f"{sonuc.renk} ({sonuc.doluluk*100:.0f}%)"
            cv2.putText(img, txt, (r["x"], max(20, r["y"] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, cizgi, 2)
        return img


ISLEM_BOYUT = (640, 480)


def _csi_pipeline(sensor_id: int, gw: int = 1280, gh: int = 720, fps: int = 30) -> str:
    flip = int(os.environ.get("KAMERA_FLIP", "2"))
    return (f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={gw},height={gh},framerate={fps}/1 ! "
            f"nvvidconv flip-method={flip} ! video/x-raw,format=BGRx ! videoconvert ! "
            f"video/x-raw,format=BGR ! appsink drop=1 max-buffers=1")


def _kare_gelir_mi(cap) -> bool:
    if cap is None or not cap.isOpened():
        return False
    import time as _t
    _t.sleep(0.3)
    for _ in range(5):
        ok, f = cap.read()
        if ok and f is not None:
            return True
        _t.sleep(0.05)
    return False


def kamera_ac(index: int = 0, genislik: int = 1280, yukseklik: int = 720):
    tip = os.environ.get("KAMERA_TIP", "").lower()

    if tip in ("", "csi"):
        try:
            cap = cv2.VideoCapture(_csi_pipeline(index, genislik, yukseklik),
                                   cv2.CAP_GSTREAMER)
            if _kare_gelir_mi(cap):
                print(f"[kamera] CSI (nvargus) acildi: sensor-id={index} "
                      f"{genislik}x{yukseklik}")
                return cap
            if cap is not None:
                cap.release()
        except Exception as e:
            print(f"[kamera] CSI denemesi basarisiz: {e}")

    if tip in ("", "usb"):
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
            try:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            except Exception:
                pass
            if _kare_gelir_mi(cap):
                print(f"[kamera] USB/V4L2 acildi: index={index}")
                return cap
            if cap is not None:
                cap.release()
        except Exception as e:
            print(f"[kamera] USB denemesi basarisiz: {e}")

    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        print(f"[kamera] Duz VideoCapture({index}) ile acildi (yedek).")
    else:
        print(f"[kamera] ACILAMADI (index={index}). Kamera takili/bos mu?")
    return cap


def kare_oku(cap):
    ok, f = cap.read()
    if not ok or f is None:
        return False, None
    if (f.shape[1], f.shape[0]) != ISLEM_BOYUT:
        f = cv2.resize(f, ISLEM_BOYUT, interpolation=cv2.INTER_AREA)
    return True, f


def hareket_orani(onceki_gri: np.ndarray, simdi_gri: np.ndarray) -> float:
    fark = cv2.absdiff(onceki_gri, simdi_gri)
    return float(cv2.countNonZero(cv2.threshold(fark, 25, 255,
                 cv2.THRESH_BINARY)[1])) / float(fark.size)


def _sentetik_kutu(renk_bgr: Tuple[int, int, int],
                   roi: Dict[str, int], boyut: int = 640) -> np.ndarray:
    img = np.full((480, boyut, 3), 30, np.uint8)
    x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
    cv2.rectangle(img, (x - 10, y - 10), (x + w + 10, y + h + 10), renk_bgr, -1)
    return img


def _self_test() -> int:
    kalib = RenkKalibrasyon()
    alg = RenkAlgilayici(kalib)
    testler = {"RED": (0, 0, 255), "GREEN": (0, 200, 0), "BLUE": (255, 0, 0)}
    print("Sentetik kutu testi (donanimsiz):")
    hata = 0
    for beklenen, bgr in testler.items():
        frame = _sentetik_kutu(bgr, kalib.roi)
        s = alg.algila(frame)
        ok = (s.renk == beklenen)
        hata += 0 if ok else 1
        print(f"  {beklenen:6s} -> {s.renk:8s} doluluk={s.doluluk*100:5.1f}%  "
              f"{'OK' if ok else 'HATA'}")
    bos = np.full((480, 640, 3), 30, np.uint8)
    s = alg.algila(bos)
    ok = (s.renk == BILINMIYOR)
    hata += 0 if ok else 1
    print(f"  {'BOS':6s} -> {s.renk:8s} doluluk={s.doluluk*100:5.1f}%  "
          f"{'OK' if ok else 'HATA'}")
    print("SONUC:", "TUM TESTLER GECTI" if hata == 0 else f"{hata} HATA")
    return 1 if hata else 0


def _canli() -> int:
    alg = RenkAlgilayici()
    cap = kamera_ac(int(os.environ.get("KAMERA", "0")))
    if not cap.isOpened():
        print("Kamera acilamadi. 'python3 renk_algila.py test' ile mantik testi yapabilirsin.")
        return 1
    print("Canli renk tespiti. Cikis: q")
    goster = True
    while True:
        ok, frame = kare_oku(cap)
        if not ok:
            print("Kare alinamadi.")
            break
        s = alg.algila(frame)
        print(f"\r{s.renk:8s} doluluk={s.doluluk*100:5.1f}%  "
              f"R={s.oranlar['RED']*100:4.0f} G={s.oranlar['GREEN']*100:4.0f} "
              f"B={s.oranlar['BLUE']*100:4.0f}", end="", flush=True)
        if goster:
            try:
                cv2.imshow("renk", alg.roi_ciz(frame, s))
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break
            except cv2.error:
                goster = False
    cap.release()
    cv2.destroyAllWindows()
    print()
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(_self_test())
    sys.exit(_canli())
