#!/usr/bin/env python3
"""
Otonom görev döngüsü: küpü görüp alır, araca yükler, rengini bildirir.

Akış: HOME -> GORME -> basla sinyali bekle -> renk oku -> AL -> YUKLE ->
araca renk gönder -> GORME (sonsuz tekrar).

Ayrı bir thread'de çalışır, paneli bloklamaz. Her hareket firmware'in MOVE
bitiş bildirimini bekler; körlemesine komut gönderilmez.
Bağımlılıklar dışarıdan verildiği için donanımsız test edilebilir.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


D_BOSTA      = "BOSTA"
D_HOME       = "HOME"
D_GORME      = "GORME'ye gidiyor"
D_BASLA_BEK  = "BASLA bekleniyor"
D_RENK       = "Renk okunuyor"
D_AL         = "Parca aliniyor (AL)"
D_DOGRULA    = "Kavrama dogrulaniyor"
D_YUKLE      = "Araca yukleniyor"
D_GONDER     = "Renk gonderiliyor"
D_HATA       = "HATA"
D_DURDU      = "Durduruldu"


@dataclass
class AyarOtonom:
    hiz: int = 1200
    ivme: int = 900
    grip_ac: int = 31
    grip_kapat: int = 110
    grip_bekle: float = 0.6
    dogrula: bool = True
    renk_deneme: int = 8
    kare_basi_bekle: float = 0.08
    hareket_zaman_asimi: float = 25.0
    oturma: float = 0.25
    home_baslangic: bool = True
    omuz_kaldir_aci: float = 12.5


class OtonomDongu:
    def __init__(self, robot, algilayici, kare_saglayici: Callable,
                 mqtt, konumlar, sim_basla_al: Optional[Callable] = None,
                 ayar: Optional[AyarOtonom] = None):
        self.robot = robot
        self.alg = algilayici
        self.kare_al = kare_saglayici
        self.mqtt = mqtt
        self.konumlar = konumlar
        self._sim_basla_al = sim_basla_al
        self.ayar = ayar or AyarOtonom()

        self._thread: Optional[threading.Thread] = None
        self._calisiyor = False
        self._dur_istendi = False
        self._durum = D_BOSTA
        self._cevrim = 0
        self._son_renk = "-"
        self._hata = ""
        self.log_queue: "queue.Queue[str]" = queue.Queue(maxsize=1000)

    def durum(self) -> dict:
        return {
            "durum": self._durum,
            "cevrim": self._cevrim,
            "son_renk": self._son_renk,
            "calisiyor": self._calisiyor,
            "hata": self._hata,
        }

    def _log(self, msg: str) -> None:
        try:
            self.log_queue.put_nowait(msg)
        except queue.Full:
            try:
                self.log_queue.get_nowait(); self.log_queue.put_nowait(msg)
            except Exception:
                pass

    def baslat(self) -> bool:
        if self._calisiyor:
            return False
        eksik = self.konumlar.eksik_zorunlular()
        if eksik:
            self._hata = "Eksik konum: " + ", ".join(eksik)
            self._log("HATA: " + self._hata + " (once Egitim sekmesinden kaydet)")
            return False
        if not self.robot.is_connected():
            self._hata = "Robot bagli degil"
            self._log("HATA: robot bagli degil")
            return False
        self._hata = ""
        self._dur_istendi = False
        self._calisiyor = True
        self._thread = threading.Thread(target=self._calis, daemon=True)
        self._thread.start()
        return True

    def durdur(self) -> None:
        if self._calisiyor:
            self._log("DUR istendi - guvenli sekilde durulacak.")
        self._dur_istendi = True
        self._calisiyor = False

    def acil(self) -> None:
        self._dur_istendi = True
        self._calisiyor = False
        try:
            self.robot.estop()
        except Exception:
            pass
        self._durum = D_DURDU
        self._log("!! ACIL DURDUR")

    def _hareket_bekle(self, timeout: float) -> bool:
        t0 = time.time()
        while time.time() - t0 < 1.0:
            if self.robot.snapshot().moving:
                break
            if not self._calisiyor:
                return False
            time.sleep(0.02)
        while time.time() - t0 < timeout:
            if not self.robot.snapshot().moving:
                time.sleep(self.ayar.oturma)
                return True
            if not self._calisiyor:
                return False
            time.sleep(0.02)
        self._log(f"UYARI: hareket zaman asimi ({timeout:.0f}s)")
        return False

    def _git(self, isim: str) -> bool:
        k = self.konumlar.al(isim)
        if k is None:
            self._log(f"HATA: '{isim}' konumu yok")
            return False
        self.robot.set_motion(self.ayar.hiz, self.ayar.ivme)
        self.robot.move_deg(k.angles)
        return self._hareket_bekle(self.ayar.hareket_zaman_asimi)

    def _git_istasyon(self, hedef: str) -> bool:
        if self.konumlar.var_mi("GECIS") and hedef != "GECIS":
            if not self._git("GECIS"):
                return False
        return self._git(hedef)

    def _renk_oku(self) -> Optional[str]:
        from collections import Counter
        oylar = Counter()
        for _ in range(self.ayar.renk_deneme):
            if not self._calisiyor:
                return None
            frame = self.kare_al()
            if frame is None:
                time.sleep(self.ayar.kare_basi_bekle)
                continue
            s = self.alg.algila(frame)
            if s.emin:
                oylar[s.renk] += 1
            time.sleep(self.ayar.kare_basi_bekle)
        if not oylar:
            return None
        renk, sayi = oylar.most_common(1)[0]
        if sayi >= max(2, self.ayar.renk_deneme // 2):
            return renk
        return None

    def _kutu_hala_var(self) -> bool:
        frame = self.kare_al()
        if frame is None:
            return False
        return self.alg.kutu_var_mi(frame)

    def _basla_var(self) -> bool:
        try:
            if self.robot.snapshot().basla == 1:
                return True
        except Exception:
            pass
        return bool(self._sim_basla_al and self._sim_basla_al())

    def _calis(self) -> None:
        try:
            if self.ayar.home_baslangic:
                self._durum = D_HOME
                self._log("HOME yapiliyor...")
                self.robot.home(None)
                if not self._hareket_bekle(self.ayar.hareket_zaman_asimi + 15):
                    self._log("UYARI: HOME bitisi dogrulanamadi, devam ediliyor")

            self._durum = D_GORME
            self.robot.grip(self.ayar.grip_ac)
            if not self._git_istasyon("GORME"):
                self._hata = "GORME'ye gidilemedi"; self._durum = D_HATA; return

            while self._calisiyor:
                self._durum = D_BASLA_BEK
                while self._calisiyor and not self._basla_var():
                    time.sleep(0.05)
                if not self._calisiyor:
                    break

                self._durum = D_RENK
                renk = self._renk_oku()
                if renk is None:
                    self._log("Renk cozulemedi (UNKNOWN) - tekrar bekleniyor")
                    time.sleep(0.3)
                    continue
                self._log(f"Renk: {renk}")
                if self.mqtt is not None and self.mqtt.renk_gonder(renk):
                    self._log(f"Renk gonderildi (robot/veri): {renk}")

                self._durum = D_AL
                self.robot.grip(self.ayar.grip_ac)
                if not self._git_istasyon("AL"):
                    self._hata = "AL'a gidilemedi"; self._durum = D_HATA; break
                al_k = self.konumlar.al("AL")
                kavra = al_k.gripper if al_k is not None else self.ayar.grip_kapat
                self.robot.grip(kavra)
                time.sleep(self.ayar.grip_bekle)

                if self.ayar.dogrula:
                    self._durum = D_DOGRULA
                    if not self._git_istasyon("GORME"):
                        self._hata = "Dogrulama hareketi basarisiz"; self._durum = D_HATA; break
                    if self._kutu_hala_var():
                        self._log("ISKALADI (kutu hala konveyorde) - tekrar denenecek")
                        self.robot.grip(self.ayar.grip_ac)
                        continue

                self._durum = D_YUKLE
                yk = self.konumlar.al("YUKLE")
                if yk is None:
                    self._hata = "YUKLE konumu yok"; self._durum = D_HATA; break
                omuz = self.ayar.omuz_kaldir_aci
                self.robot.set_motion(self.ayar.hiz, self.ayar.ivme)
                a1 = list(self.robot.snapshot().angles); a1[1] = omuz
                self._log(f"YUKLE 1/3: omuz {omuz} deg kaldir")
                self.robot.move_deg(a1)
                if not self._hareket_bekle(self.ayar.hareket_zaman_asimi):
                    self._hata = "Omuz kaldirma basarisiz"; self._durum = D_HATA; break
                a2 = list(a1); a2[0] = yk.angles[0]; a2[1] = omuz
                self._log("YUKLE 2/3: taban yukleme noktasina (omuz sabit)")
                self.robot.move_deg(a2)
                if not self._hareket_bekle(self.ayar.hareket_zaman_asimi):
                    self._hata = "Taban hareketi basarisiz"; self._durum = D_HATA; break
                self._log("YUKLE 3/3: tam yukleme pozu")
                self.robot.move_deg(list(yk.angles))
                if not self._hareket_bekle(self.ayar.hareket_zaman_asimi):
                    self._hata = "YUKLE'ye gidilemedi"; self._durum = D_HATA; break
                self.robot.grip(self.ayar.grip_ac)
                time.sleep(self.ayar.grip_bekle)

                self._durum = D_GONDER
                if self.mqtt is not None and self.mqtt.basla_gonder():
                    self._log("Araca BASLA gonderildi (robot/basla) -> arac baslasin")
                self._son_renk = renk
                self._cevrim += 1

                self._durum = D_GORME
                self.robot.grip(self.ayar.grip_ac)
                donus_lift = list(self.robot.snapshot().angles)
                donus_lift[1] = self.ayar.omuz_kaldir_aci
                self._log(f"Donus: omuz {self.ayar.omuz_kaldir_aci} deg kaldir")
                self.robot.set_motion(self.ayar.hiz, self.ayar.ivme)
                self.robot.move_deg(donus_lift)
                if not self._hareket_bekle(self.ayar.hareket_zaman_asimi):
                    self._hata = "Donus omuz kaldirma basarisiz"; self._durum = D_HATA; break
                if not self._git_istasyon("GORME"):
                    self._hata = "GORME'ye donulemedi"; self._durum = D_HATA; break

        except Exception as e:
            self._hata = str(e)
            self._durum = D_HATA
            self._log("HATA (dongu): " + str(e))
        finally:
            self._calisiyor = False
            if self._dur_istendi:
                self._durum = D_DURDU
                self._hata = ""
            elif self._durum != D_HATA:
                self._durum = D_DURDU
            self._log("Dongu durdu.")


class _SahteState:
    def __init__(self):
        self.moving = False
        self.angles = [0.0, 0.0, 0.0, 0.0]
        self.last_event = ""


class _SahteRobot:
    def __init__(self):
        self._st = _SahteState()
        self._bagli = True

    def is_connected(self): return self._bagli
    def set_motion(self, h, a): pass
    def grip(self, a): pass
    def estop(self): pass

    def home(self, j=None):
        self._hareket(0.2)

    def move_deg(self, angles):
        self._st.angles = list(angles)
        self._hareket(0.2)

    def _hareket(self, sure):
        self._st.moving = True
        def bitir():
            time.sleep(sure); self._st.moving = False; self._st.last_event = "MOVE_DONE"
        threading.Thread(target=bitir, daemon=True).start()

    def snapshot(self):
        import copy
        return copy.copy(self._st)


def _self_test() -> int:
    import numpy as np
    from renk_algila import RenkAlgilayici, RenkKalibrasyon
    from konum_yonetici import KonumYonetici
    import os, tempfile

    tf = os.path.join(tempfile.gettempdir(), "kt_konum.json")
    ky = KonumYonetici(tf)
    ky.kaydet("GORME", [0, -10, 20, -5], 90)
    ky.kaydet("AL",    [10, -30, 40, -10], 110)
    ky.kaydet("YUKLE", [-20, -20, 30, -8], 31)

    alg = RenkAlgilayici(RenkKalibrasyon())
    roi = alg.kalib.roi
    yesil = np.full((480, 640, 3), 30, np.uint8)
    import cv2
    cv2.rectangle(yesil, (roi["x"]-10, roi["y"]-10),
                  (roi["x"]+roi["w"]+10, roi["y"]+roi["h"]+10), (0, 200, 0), -1)
    bos = np.full((480, 640, 3), 30, np.uint8)

    hal = {"kutu": True}
    def kare():
        return yesil if hal["kutu"] else bos

    class _Mqtt:
        def yuk_gonder(self, renk):
            print("   [mqtt sahte] yuk:", renk); return True
        def renk_gonder(self, renk):
            print("   [mqtt sahte] renk:", renk); return True
        def basla_gonder(self):
            print("   [mqtt sahte] BASLA"); return True

    ayar = AyarOtonom(home_baslangic=True, renk_deneme=3, grip_bekle=0.05,
                      oturma=0.02, kare_basi_bekle=0.01)
    dongu = OtonomDongu(_SahteRobot(), alg, kare, _Mqtt(), ky, lambda: True, ayar)

    print("Otonom dongu sahte-robot testi basliyor...")
    dongu.baslat()

    import time as _t
    t0 = _t.time()
    while _t.time() - t0 < 8:
        d = dongu.durum()
        if d["durum"] == D_AL:
            hal["kutu"] = False
        if d["cevrim"] >= 1:
            break
        _t.sleep(0.05)
    _t.sleep(0.3)
    dongu.durdur(); _t.sleep(0.6)

    while not dongu.log_queue.empty():
        print("   log:", dongu.log_queue.get_nowait())
    d = dongu.durum()
    print(f"SONUC: cevrim={d['cevrim']} son_renk={d['son_renk']} durum={d['durum']}")
    os.remove(tf)
    return 0 if d["cevrim"] >= 1 and d["son_renk"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
