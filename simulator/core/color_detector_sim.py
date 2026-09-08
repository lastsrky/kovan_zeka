"""
TEKNOFEST 2026 Akıllı Fabrika SITL Digital Twin Simulator
Classical OpenCV HSV Color Detector (Strictly Classical Computer Vision - No AI)

Matches robotkol/renk_algila.py and robotkol/renk_kalibrasyon.json:
- Dual-band Red ([0, 10] U [170, 179] / [0, 8] U [168, 179])
- Single-band Green ([40, 85] / [73, 93])
- Single-band Blue ([95, 130] / [90, 110])
- ROI cropping with boundary protection
- Gaussian Blur (5x5, sigma=0)
- Morphological OPEN (3x3 kernel)
- Occupancy ratio threshold: doluluk >= 0.40
- Winner confidence margin: marj >= 0.12
- Multi-frame majority voting support (8 frames)
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

RENKLER = ("RED", "GREEN", "BLUE")
BILINMIYOR = "UNKNOWN"

# Standard default ranges from robotkol/renk_algila.py
VARSAYILAN_HSV: Dict[str, List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = {
    "RED": [
        ((0, 100, 70), (10, 255, 255)),
        ((170, 100, 70), (179, 255, 255)),
    ],
    "GREEN": [
        ((40, 70, 55), (85, 255, 255)),
    ],
    "BLUE": [
        ((95, 90, 55), (130, 255, 255)),
    ],
}

VARSAYILAN_ROI = (215, 120, 251, 240)
VARSAYILAN_DOLULUK_ESIGI = 0.40
VARSAYILAN_MARJ = 0.12


@dataclass
class ColorResult:
    """Detection result holding color classification, confidence and ratio metrics."""
    renk: str
    guven: float
    doluluk: float
    marj: float
    oranlar: Dict[str, float] = field(default_factory=dict)
    emin: bool = False

    @property
    def color(self) -> str:
        return self.renk

    @property
    def confidence(self) -> float:
        return self.guven

    @property
    def fill_ratio(self) -> float:
        return self.doluluk

    @property
    def margin(self) -> float:
        return self.marj

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.renk == other
        if isinstance(other, ColorResult):
            return (
                self.renk == other.renk
                and abs(self.doluluk - other.doluluk) < 1e-4
                and abs(self.marj - other.marj) < 1e-4
            )
        return False

    def __repr__(self) -> str:
        return (
            f"ColorResult(renk='{self.renk}', doluluk={self.doluluk:.3f}, "
            f"marj={self.marj:.3f}, emin={self.emin})"
        )


# Alias for compatibility with robotkol/renk_algila.py
RenkSonuc = ColorResult


class CalibrationConfig:
    """Holds calibration parameters for HSV ranges, ROI, and thresholds."""
    def __init__(
        self,
        hsv: Optional[Dict[str, List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]]] = None,
        roi: Tuple[int, int, int, int] = VARSAYILAN_ROI,
        doluluk_esigi: float = VARSAYILAN_DOLULUK_ESIGI,
        marj: float = VARSAYILAN_MARJ,
    ):
        self.hsv = hsv or VARSAYILAN_HSV
        self.roi = roi
        self.doluluk_esigi = doluluk_esigi
        self.marj = marj


class ColorDetectorSim:
    """
    Classical OpenCV HSV Color Detector Simulator.
    Strictly implements classical morphological color thresholding without AI / deep learning.
    """

    def __init__(
        self,
        hsv_ranges: Optional[Dict[str, List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]]] = None,
        roi: Optional[Union[Tuple[int, int, int, int], Dict[str, int]]] = None,
        doluluk_esigi: float = VARSAYILAN_DOLULUK_ESIGI,
        marj: float = VARSAYILAN_MARJ,
        calib_path: Optional[str] = None,
    ):
        self.doluluk_esigi = float(doluluk_esigi)
        self.marj = float(marj)

        # Set default or custom HSV ranges
        if hsv_ranges is not None:
            self.hsv_ranges = hsv_ranges
        else:
            self.hsv_ranges = {k: list(v) for k, v in VARSAYILAN_HSV.items()}

        # Set ROI
        if roi is not None:
            if isinstance(roi, dict):
                self.roi = (int(roi["x"]), int(roi["y"]), int(roi["w"]), int(roi["h"]))
            else:
                self.roi = tuple(int(x) for x in roi[:4])
        else:
            self.roi = VARSAYILAN_ROI

        # Optional load from calibration JSON file if specified
        if calib_path and os.path.exists(calib_path):
            self.load_calibration(calib_path)

        # Compatibility aliases
        self.araliklar = self.hsv_ranges
        self.kalib = CalibrationConfig(
            hsv=self.hsv_ranges,
            roi=self.roi,
            doluluk_esigi=self.doluluk_esigi,
            marj=self.marj,
        )

    def load_calibration(self, path: str) -> None:
        """Loads calibration settings from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "roi" in data:
                r = data["roi"]
                self.roi = (int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"]))
            if "doluluk_esigi" in data:
                self.doluluk_esigi = float(data["doluluk_esigi"])
            if "marj" in data:
                self.marj = float(data["marj"])
            if "hsv" in data:
                parsed_hsv = {}
                for k, v in data["hsv"].items():
                    parsed_hsv[k] = [
                        (tuple(int(x) for x in lower), tuple(int(x) for x in upper))
                        for lower, upper in v
                    ]
                self.hsv_ranges = parsed_hsv
                self.araliklar = self.hsv_ranges
            self.kalib = CalibrationConfig(
                hsv=self.hsv_ranges,
                roi=self.roi,
                doluluk_esigi=self.doluluk_esigi,
                marj=self.marj,
            )
        except Exception as e:
            print(f"[ColorDetectorSim] Warning: Could not load calibration: {e}")

    def _crop_roi(self, frame: np.ndarray) -> np.ndarray:
        """Crops ROI from frame with boundary clamping to prevent indexing errors."""
        h, w = frame.shape[:2]
        rx, ry, rw, rh = self.roi
        rx = max(0, min(rx, w - 1))
        ry = max(0, min(ry, h - 1))
        rw = max(1, min(rw, w - rx))
        rh = max(1, min(rh, h - ry))
        return frame[ry : ry + rh, rx : rx + rw]

    def detect(self, frame: Optional[np.ndarray]) -> ColorResult:
        """
        Analyzes frame using classical OpenCV HSV thresholding.
        Returns ColorResult containing detected color, occupancy fill ratio, confidence and margin.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return ColorResult(
                renk=BILINMIYOR,
                guven=0.0,
                doluluk=0.0,
                marj=0.0,
                oranlar={c: 0.0 for c in RENKLER},
                emin=False,
            )

        # 1. ROI Extraction with boundary safety
        roi = self._crop_roi(frame)
        rh, rw = roi.shape[:2]
        total_pixels = float(rw * rh)
        if total_pixels <= 0.0:
            return ColorResult(
                renk=BILINMIYOR,
                guven=0.0,
                doluluk=0.0,
                marj=0.0,
                oranlar={c: 0.0 for c in RENKLER},
                emin=False,
            )

        # 2. Gaussian Blur (5x5, sigma=0) to suppress sensor noise
        blurred = cv2.GaussianBlur(roi, (5, 5), 0)

        # 3. HSV Color Conversion
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # 4. Color Segmentation with Morphological Open (3x3)
        kernel = np.ones((3, 3), np.uint8)
        ratios: Dict[str, float] = {}

        for color in RENKLER:
            ranges = self.hsv_ranges.get(color, [])
            mask_total = np.zeros((rh, rw), dtype=np.uint8)
            for lower, upper in ranges:
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                m = cv2.inRange(hsv, lower_np, upper_np)
                mask_total = cv2.bitwise_or(mask_total, m)

            # Morphological Open removes isolated noise pixels
            mask_cleaned = cv2.morphologyEx(mask_total, cv2.MORPH_OPEN, kernel)
            cnt = cv2.countNonZero(mask_cleaned)
            ratios[color] = float(cnt) / total_pixels

        # 5. Determine Dominant Color and Margin
        sorted_colors = sorted(ratios.items(), key=lambda kv: kv[1], reverse=True)
        top_color, top_ratio = sorted_colors[0]
        second_ratio = sorted_colors[1][1] if len(sorted_colors) > 1 else 0.0
        margin = top_ratio - second_ratio

        # 6. Evaluate Confidence and Occupancy Thresholds
        emin = (top_ratio >= self.doluluk_esigi) and (margin >= self.marj)
        chosen_color = top_color if emin else BILINMIYOR

        return ColorResult(
            renk=chosen_color,
            guven=top_ratio,
            doluluk=top_ratio,
            marj=margin,
            oranlar=ratios,
            emin=emin,
        )

    def algila(self, frame: Optional[np.ndarray]) -> ColorResult:
        """Alias for detect() matching robotkol/renk_algila.py method name."""
        return self.detect(frame)

    def kutu_var_mi(self, frame: Optional[np.ndarray]) -> bool:
        """Checks if a workpiece cube is present resting in the inspection ROI."""
        res = self.detect(frame)
        return res.doluluk >= self.doluluk_esigi

    def read_color_voting(
        self,
        frames: List[np.ndarray],
        required_majority: Optional[int] = None,
    ) -> Optional[str]:
        """
        Majority vote across multiple frames (e.g. 8-frame vote) to avoid false positives.
        Returns winning color string or None if consensus is not reached.
        """
        if not frames:
            return None

        votes: Counter = Counter()
        for f in frames:
            res = self.detect(f)
            if res.emin and res.renk in RENKLER:
                votes[res.renk] += 1

        if not votes:
            return None

        winner, count = votes.most_common(1)[0]
        threshold = required_majority if required_majority is not None else max(2, len(frames) // 2)
        if count >= threshold:
            return winner
        return None

    def roi_ciz(
        self,
        frame: np.ndarray,
        sonuc: Optional[ColorResult] = None,
    ) -> np.ndarray:
        """Draws calibrated inspection bounding box and detection telemetry onto frame."""
        img = frame.copy()
        rx, ry, rw, rh = self.roi
        bgr_map = {
            "RED": (0, 0, 255),
            "GREEN": (0, 200, 0),
            "BLUE": (255, 0, 0),
            BILINMIYOR: (80, 80, 80),
        }
        label = sonuc.renk if sonuc else ""
        border_color = bgr_map.get(label, (0, 255, 255))
        cv2.rectangle(img, (rx, ry), (rx + rw, ry + rh), border_color, 2)
        if sonuc:
            txt = f"{sonuc.renk} ({sonuc.doluluk * 100:.0f}%, m:{sonuc.marj:.2f})"
            cv2.putText(
                img,
                txt,
                (rx, max(22, ry - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                border_color,
                2,
            )
        return img
