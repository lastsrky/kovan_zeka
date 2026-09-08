#!/usr/bin/env python3
"""
Öğretilen robot pozlarını saklar ve okur.

Konumlar: GORME (konveyöre bakış), AL (küpü kavrama), YUKLE (araca bırakma),
GECIS (opsiyonel, çarpışmayı önleyen ara poz).
Her konum dört eklem açısı ve bir gripper açısından oluşur.

Dosya: konumlar.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
KONUM_PATH = os.path.join(HERE, "konumlar.json")

ZORUNLU = ("GORME", "AL", "YUKLE")
OPSIYONEL = ("GECIS",)
TUM_ISIMLER = ZORUNLU + OPSIYONEL


@dataclass
class Konum:
    angles: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    gripper: int = 90

    def to_dict(self) -> dict:
        return {"angles": [round(float(a), 3) for a in self.angles],
                "gripper": int(self.gripper)}

    @classmethod
    def from_dict(cls, d: dict) -> "Konum":
        a = list(d.get("angles", [0.0, 0.0, 0.0, 0.0]))
        a = (a + [0.0, 0.0, 0.0, 0.0])[:4]
        return cls(angles=[float(x) for x in a], gripper=int(d.get("gripper", 90)))


class KonumYonetici:
    def __init__(self, path: str = KONUM_PATH):
        self.path = path
        self.konumlar: Dict[str, Konum] = {}
        self.yukle()

    def yukle(self) -> None:
        self.konumlar = {}
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r") as f:
                d = json.load(f)
            for isim, v in d.items():
                self.konumlar[isim] = Konum.from_dict(v)
        except Exception as e:
            print(f"[konum] Okuma hatasi ({e}); bos basliyor.")
            self.konumlar = {}

    def kaydet_dosya(self) -> None:
        with open(self.path, "w") as f:
            json.dump({k: v.to_dict() for k, v in self.konumlar.items()},
                      f, indent=2)

    def kaydet(self, isim: str, angles: List[float], gripper: int) -> None:
        self.konumlar[isim] = Konum(angles=[float(a) for a in angles[:4]],
                                    gripper=int(gripper))
        self.kaydet_dosya()

    def sil(self, isim: str) -> None:
        if isim in self.konumlar:
            del self.konumlar[isim]
            self.kaydet_dosya()

    def al(self, isim: str) -> Optional[Konum]:
        return self.konumlar.get(isim)

    def var_mi(self, isim: str) -> bool:
        return isim in self.konumlar

    def eksik_zorunlular(self) -> List[str]:
        return [i for i in ZORUNLU if i not in self.konumlar]

    def hazir_mi(self) -> bool:
        return not self.eksik_zorunlular()


if __name__ == "__main__":
    import tempfile
    tf = os.path.join(tempfile.gettempdir(), "konumlar_test.json")
    ky = KonumYonetici(tf)
    print("Baslangic eksik:", ky.eksik_zorunlular())
    ky.kaydet("GORME", [0, -20, 30, -10], 90)
    ky.kaydet("AL", [15, -40, 50, -20], 110)
    ky.kaydet("YUKLE", [-30, -30, 40, -15], 31)
    print("Kayit sonrasi eksik:", ky.eksik_zorunlular(), "hazir:", ky.hazir_mi())
    ky2 = KonumYonetici(tf)
    print("Diskten GORME:", ky2.al("GORME"))
    os.remove(tf)
    print("OK")
