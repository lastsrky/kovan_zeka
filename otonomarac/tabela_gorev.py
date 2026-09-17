"""
Tabela tetiklemeli görevler: yaya geçidi ve park.

Aynı tespiti paylaşan iki durum makinesi.

Yaya geçidi tabelası yaklaşınca araç durur, sonra şerit takibini kapatıp
geçitten kör düz geçer (zebra çizgileri beyaz olduğu için şerit tespitini
bozar).

Park tabelası yaklaşınca zemindeki hedef renkli alana yönelir ve üzerinde
kalıcı olarak durur. Hedef rengi colorlink.py'den gelir.
"""
import time

import numpy as np

from tabela import TabelaDetector, TABELA_ISIM, YAYA_ID, PARK_ID
from park_zemin_renk import detect_park_floor, PARK_RENK_BANTLARI


def bbox_mesafe_cm(depth, x1, y1, x2, y2, depth_scale, crop_ratio=0.8):
    if depth is None:
        return None, 0
    dh, dw = depth.shape[:2]
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    bw = int((x2 - x1) * crop_ratio) // 2
    bh = int((y2 - y1) * crop_ratio) // 2
    rx1 = max(0, cx - bw)
    ry1 = max(0, cy - bh)
    rx2 = min(dw, cx + bw)
    ry2 = min(dh, cy + bh)
    if rx2 <= rx1 or ry2 <= ry1:
        return None, 0
    roi = depth[ry1:ry2, rx1:rx2].astype(np.float32)
    gecerli = roi[roi > 0]
    if gecerli.size < 3:
        return None, int(gecerli.size)
    return (float(np.percentile(gecerli, 25)) * depth_scale * 100.0,
            int(gecerli.size))


class GorevSonuc(object):
    def __init__(self):
        self.state = "BEKLIYOR"
        self.dur = False
        self.duz_git = False
        self.throttle = None
        self.steer = None
        self.dets = []
        self.dist_cm = None
        self.tabela = None
        self.park_state = "NORMAL"
        self.park_cm = None
        self.red_bbox = None
        self.red_cm = None
        self.hedef_renk = None
        self.bitti = False


class TabelaGorevleri(object):
    def __init__(self, tabela_cfg=None, yaya_cfg=None, park_cfg=None,
                 max_pwm=300, max_delta=35):
        t = tabela_cfg or {}
        y = yaya_cfg or {}
        p = park_cfg or {}

        # ==============================================================================
        # TABELA TESPİTİ GENEL AYARLARI (YOLO / TensorRT)
        # ==============================================================================
        # [AÇIKLAMA]: Tabela tespit sistemini açar/kapatır (False olursa yaya ve park devre dışı kalır).
        # [NASIL DEĞİŞTİRİLİR]: config.yaml -> tabela -> enable değerini true veya false yapın. Kodda True/False (büyük harfle).
        self.enabled = bool(t.get("enable", True))

        # [AÇIKLAMA]: Modelin minimum güven (confidence) skoru. %50 altındaki tahminler elenir.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.5 yerine 0.6 yazın).
        self.conf_thresh = float(t.get("conf_thresh", 0.5))

        # [AÇIKLAMA]: Modelin kaç karede bir koşturulacağı (GPU yükünü azaltır).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 6 yerine 12 yazın).
        self.period = max(1, int(t.get("period", 6)))

        # [AÇIKLAMA]: Tabela kutusu minimum piksel alanı (uzaktaki parazitleri eler).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 400 yerine 300 yazın).
        self.min_area_px = int(t.get("min_area_px", 400))

        # ==============================================================================
        # YAYA GEÇİDİ GÖREVİ AYARLARI (YAYA_ID = 0)
        # ==============================================================================
        # [AÇIKLAMA]: Yaya geçidi görevini açar/kapatır.
        # [NASIL DEĞİŞTİRİLİR]: config.yaml -> yaya -> enable değerini true/false yapın.
        self.yaya_enabled = bool(y.get("enable", True))

        # [AÇIKLAMA]: Yaya tabelasına kaç cm mesafe kaldığında durma sürecinin başlayacağı sınır.
        #             Hakem "Tabelaya 70 cm kala durun" derse bu sayıyı 70.0 yapın.
        # [NASIL DEĞİŞTİRİLİR]: Sadece ondalıklı sayıyı değiştirin (örn: 60.0 yerine 100.0 yazın). Noktayı koruyun.
        self.dur_mesafe_cm = float(y.get("dur_mesafe_cm", 60.0))

        # [AÇIKLAMA]: Yaya tabelasının durmayı tetiklemesi için üst üste görülmesi gereken kare sayısı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 4 yerine 3 yazın).
        self.trigger_frames = int(y.get("trigger_frames", 4))

        # [AÇIKLAMA]: Tabela onaylandıktan sonra durmadan önce normal hızda gidilecek yaklaşma süresi (saniye).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 1.0 yerine 0.0 yazın).
        self.gecikme_s = float(y.get("gecikme_s", 1.0))

        # [AÇIKLAMA]: Yaya geçidinde sıfır gazla hareketsiz beklenilecek süre (saniye).
        #             Hakem "Yaya geçidinde 5 saniye bekleyin" derse bu sayıyı 5.0 yapın.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 3.0 yerine 5.0 yazın). Noktayı silmeyin.
        self.dur_s = float(y.get("dur_s", 3.0))

        # [AÇIKLAMA]: Durma bittikten sonra şerit takibi kapatılarak direksiyon düz kör gidilecek süre (saniye).
        #             Zebra çizgilerini şerit sanıp yoldan çıkmaması için kullanılır.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 3.0 yerine 4.0 yazın).
        self.gec_s = float(y.get("gec_s", 3.0))

        # [AÇIKLAMA]: Kör düz geçiş sırasında motora verilecek PWM gaz gücü.
        #             Hakem "Yaya geçidinden daha hızlı geçin" derse bu sayıyı artırın.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 78.0 yerine 85.0 yazın).
        self.gec_pwm = float(y.get("gec_pwm", 78.0))

        self.max_pwm = float(max_pwm) if max_pwm else 300.0
        self.max_delta = float(max_delta) if max_delta else 35.0

        # [AÇIKLAMA]: Yaya görevinin parkurda sadece 1 kez yapılmasını sağlar.
        # [NASIL DEĞİŞTİRİLİR]: True veya False yazın.
        self.once = bool(y.get("once", True))

        # ==============================================================================
        # OTOMATİK PARK GÖREVİ AYARLARI (PARK_ID = 5)
        # ==============================================================================
        # [AÇIKLAMA]: Otomatik park görevini açar/kapatır.
        # [NASIL DEĞİŞTİRİLİR]: config.yaml -> park -> enable değerini true/false yapın.
        self.park_enabled = bool(p.get("enable", True))

        # [AÇIKLAMA]: Park tabelasına kaç cm mesafe kaldığında park hazırlık moduna (AKTIF) geçileceği sınır.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 110.0 yerine 90.0 yazın).
        self.park_tabela_cm = float(p.get("tabela_mesafe_cm", 110.0))

        # [AÇIKLAMA]: Park tabelası için minimum piksel alanı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 400).
        self.park_min_area_px = int(p.get("tabela_min_area_px", 400))

        # [AÇIKLAMA]: Park hazırlığına geçmek için tabelanın üst üste görülmesi gereken kare sayısı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 3).
        self.park_trigger_frames = int(p.get("trigger_frames", 3))

        # [AÇIKLAMA]: Zemindeki renkli alana olan derinlik mesafesi bu değerin (cm) altına indiğinde araç kalıcı olarak durur.
        #             Hakem "Park alanına daha çok yanaş" derse bu sayıyı düşürün (örn: 15.0).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 25.0 yerine 15.0 yazın).
        self.park_dur_cm = float(p.get("dur_mesafe_cm", 25.0))

        # [AÇIKLAMA]: Park alanına yaklaşırken ve yönelirken kullanılan hassas seyir PWM gücü.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 65.0 yerine 80.0 yazın).
        self.park_pwm = float(p.get("park_pwm", 65.0))

        # [AÇIKLAMA]: Renkli park alanına yönelme oransal direksiyon kazancı (park_k).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.25 yerine 0.125 yazın).
        self.park_k = float(p.get("park_k", 0.25))

        # [AÇIKLAMA]: Renk lekesi aracın burnunun altına girip kameradan kaybolunca, kaç kare sonra parkın bittiği kabul edileceği.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 5 yerine 8 yazın).
        self.red_kayip_frames = int(p.get("red_kayip_frames", 5))

        # [AÇIKLAMA]: Zemin aramasında görüntünün üstten kırpılma oranı (%25). Duvardaki renkli afişleri eler.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.25).
        self.ust_kirp = float(p.get("ust_kirp", 0.25))

        # [AÇIKLAMA]: Zemindeki hedef renk lekesi için minimum piksel alanı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 300).
        self.red_area_min = int(p.get("red_area_min", 300))

        # [AÇIKLAMA]: Zemin lekesi için kabul edilen minimum derinlik mesafesi (cm).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 25.0).
        self.zemin_min_cm = float(p.get("zemin_min_cm", 25.0))

        # [AÇIKLAMA]: Zemin lekesi için kabul edilen maksimum derinlik mesafesi (cm).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 350.0).
        self.zemin_max_cm = float(p.get("zemin_max_cm", 350.0))

        # [AÇIKLAMA]: Robot koldan MQTT mesajı gelmezse yöneleceği acil durum yedek park rengi ("RED", "GREEN" veya "BLUE").
        # [NASIL DEĞİŞTİRİLİR]: Sadece tırnak içindeki kelimeyi değiştirin (örn: "RED" yerine "GREEN" yazın).
        self.varsayilan_renk = str(p.get("varsayilan_renk", "RED")).upper()
        self.hedef_renk = self.varsayilan_renk
        self._renk_geldi = False
        self._uyarildi_renk = False

        self.det = None
        self.state = "BEKLIYOR"
        self._streak = 0
        self._t0 = 0.0
        self._son_dets = []
        self._frame_i = 0
        self._uyarildi_depth = False
        self._no_depth_streak = 0
        self.park_state = "NORMAL"
        self._park_streak = 0
        self._red_gorulduy = False
        self._red_kayip = 0
        self._son_steer = 0.0

    def start(self):
        if not self.enabled:
            print("[tabela] KAPALI (config tabela.enable: false)")
            return False
        try:
            self.det = TabelaDetector(conf_thresh=self.conf_thresh)
        except Exception as e:
            print("[tabela] engine yüklenemedi -> tabela görevleri "
                  "devre dýþý:", e)
            self.det = None
            return False
        print("[tabela] hazýr (conf>={:.2f}, her {} karede infer)".format(
            self.conf_thresh, self.period))
        print("[tabela]   yaya: <{:.0f} cm -> {:.1f} sn dur".format(
            self.dur_mesafe_cm, self.dur_s))
        print("[tabela]   park: <{:.0f} cm -> hedef renkli alana yönel, "
              "<{:.0f} cm'de dur  (hedef: {}, MQTT bekleniyor)".format(
                  self.park_tabela_cm, self.park_dur_cm, self.hedef_renk))
        return True

    @property
    def gec_throttle(self):
        return max(0.0, min(1.0, self.gec_pwm / self.max_pwm))

    @property
    def park_throttle(self):
        return max(0.0, min(1.0, self.park_pwm / self.max_pwm))

    def set_hedef_renk(self, renk):
        if not renk:
            return
        r = str(renk).strip().upper()
        ters_harita = {"RED": "RED", "BLUE": "BLUE", "GREEN": "GREEN"}
        r = ters_harita.get(r, r)

        if r not in PARK_RENK_BANTLARI:
            if not self._uyarildi_renk:
                print("[park] UYARI: '{}' park rengi tanýnmýyor, {} "
                      "kullanýlacak".format(renk, self.varsayilan_renk))
                self._uyarildi_renk = True
            return
        if r != self.hedef_renk or not self._renk_geldi:
            self.hedef_renk = r
            self._renk_geldi = True
            print("[park] hedef park alaný: {}".format(r))

    def reset(self):
        self.state = "BEKLIYOR"
        self._streak = 0
        self._son_dets = []
        self.park_state = "NORMAL"
        self._park_streak = 0
        self._red_gorulduy = False
        self._red_kayip = 0
        self._son_steer = 0.0
        print("[tabela] yaya + park görevleri sýfýrlandý")

    def idle(self):
        self._streak = 0
        self._park_streak = 0
        out = GorevSonuc()
        out.state = self.state
        out.park_state = self.park_state
        out.dets = self._son_dets
        return out

    def update(self, raw_color, raw_depth, depth_scale, now=None):
        out = GorevSonuc()
        if now is None:
            now = time.time()
        if self.det is None or not self.enabled:
            out.state = "KAPALI"
            return out

        self._frame_i += 1
        if raw_color is not None and self._frame_i % self.period == 0:
            try:
                self._son_dets = self.det.infer(raw_color)
            except Exception as e:
                print("[tabela] infer hatasý:", e)
                self._son_dets = []
        out.dets = self._son_dets

        # ==============================================================================
        # YAYA GEÇİDİ DURUM MAKİNESİ (STATE MACHINE)
        # Durumlar: BEKLIYOR -> YAKLASMA -> DUR -> GEC -> BITTI
        # ==============================================================================
        yakin = False
        if self.yaya_enabled and self.state not in ("BITTI",):
            if raw_depth is None or not depth_scale:
                self._no_depth_streak += 1
                if not self._uyarildi_depth and self._no_depth_streak >= 30:
                    print("[tabela] UYARI: depth yok -> yaya görevi mesafe "
                          "ölçemez. config camera.enable_depth: true mu?")
                    self._uyarildi_depth = True
            else:
                self._no_depth_streak = 0
                for (x1, y1, x2, y2, conf, cid) in self._son_dets:
                    # YAYA_ID (0) tabelası aranır ve alan filtresi uygulanır
                    if cid != YAYA_ID:
                        continue
                    if (x2 - x1) * (y2 - y1) < self.min_area_px:
                        continue
                    d, _n = bbox_mesafe_cm(raw_depth, x1, y1, x2, y2,
                                           depth_scale)
                    if d is None:
                        continue
                    if out.dist_cm is None or d < out.dist_cm:
                        out.dist_cm = d
                        out.tabela = TABELA_ISIM.get(cid, "id%d" % cid)
                    # [TETİKLEME EŞİĞİ]: Tabela mesafesi dur_mesafe_cm (örn: 100 cm) altındaysa yakın sayılır
                    if d < self.dur_mesafe_cm:
                        yakin = True

        # DURUM 1: BEKLIYOR (Tabelayı algılama ve doğrulama aşaması)
        # [AÇIKLAMA]: Tabela ardışık trigger_frames (örn: 3 kare) boyunca görülürse YAKLASMA durumuna geçilir.
        if self.state == "BEKLIYOR":
            self._streak = (self._streak + 1) if yakin else 0
            if self._streak >= self.trigger_frames:
                self.state = "YAKLASMA"
                self._t0 = now
                self._streak = 0
                print("[yaya] tabela {:.0f} cm -> YAKLASMA ({:.1f} sn normal "
                      "sür, sonra DUR)".format(out.dist_cm or -1,
                                               self.gecikme_s))

        # DURUM 2: YAKLASMA (Durmadan önceki son yaklaşma sürüşü)
        # [AÇIKLAMA]: gecikme_s süresi boyunca normal şerit takibiyle sürüş yapılır; süre dolunca araç DUR durumuna geçer.
        elif self.state == "YAKLASMA":
            if now - self._t0 >= self.gecikme_s:
                self.state = "DUR"
                self._t0 = now
                print("[yaya] DUR ({:.1f} sn motor 0)".format(self.dur_s))

        # DURUM 3: DUR (Yaya geçidinde tam duruş)
        # [AÇIKLAMA]: out.dur = True döner, main.py motoru tamamen durdurur. dur_s (örn: 3.0 sn) beklenir.
        elif self.state == "DUR":
            if now - self._t0 >= self.dur_s:
                self.state = "GEC"
                self._t0 = now
                print("[yaya] DUR bitti -> GEC ({:.1f} sn kör düz, gaz {:.2f} "
                      "= PWM {:.0f})".format(self.gec_s, self.gec_throttle,
                                             self.gec_pwm))

        # DURUM 4: GEC (Zebra çizgilerini kör düz geçiş)
        # [AÇIKLAMA]: out.duz_git = True döner; şerit takibi devre dışı kalır, direksiyon düz tutulur,
        #             gec_pwm gücüyle gec_s (örn: 3.0 sn) boyunca sürülür.
        elif self.state == "GEC":
            if now - self._t0 >= self.gec_s:
                self.state = "BITTI" if self.once else "BEKLIYOR"
                print("[yaya] GEC bitti -> normal sürüþ ({})".format(
                    self.state))

        # ==============================================================================
        # PARK GÖREVİ TETİKLEME VE GÜNCELLEME
        # ==============================================================================
        if self.park_enabled and raw_depth is not None and depth_scale:
            self._park_guncelle(out, raw_color, raw_depth, depth_scale)

        out.state = self.state
        out.park_state = self.park_state
        out.hedef_renk = self.hedef_renk

        # [GÖREV ÇIKTI ARBİTRASYONU]:
        if self.park_state == "ETTI":
            out.dur = True
            out.bitti = True
            out.steer = self._son_steer
        elif self.park_state == "AKTIF":
            out.throttle = self.park_throttle
            out.steer = self._son_steer
        elif self.state == "DUR":
            out.dur = True
        elif self.state == "GEC":
            out.duz_git = True
            out.throttle = self.gec_throttle
        return out

    def _park_guncelle(self, out, raw_color, raw_depth, depth_scale):
        if self.park_state == "ETTI":
            return

        # ==============================================================================
        # OTOMATİK PARK DURUM MAKİNESİ (STATE MACHINE)
        # Durumlar: NORMAL -> AKTIF (Yönelme) -> ETTI (Kalıcı Stop)
        # ==============================================================================
        yakin = False
        for (x1, y1, x2, y2, conf, cid) in self._son_dets:
            # PARK_ID (5) tabelası aranır ve alan/mesafe doğrulanır
            if cid != PARK_ID:
                continue
            if (x2 - x1) * (y2 - y1) < self.park_min_area_px:
                continue
            d, _n = bbox_mesafe_cm(raw_depth, x1, y1, x2, y2, depth_scale)
            if d is None:
                continue
            if out.park_cm is None or d < out.park_cm:
                out.park_cm = d
            # [TETİKLEME EŞİĞİ]: Tabela mesafesi park_tabela_cm (örn: 110 cm) altındaysa hazırlık başlar
            if d < self.park_tabela_cm:
                yakin = True

        # DURUM 1: NORMAL (Park tabelasını arama ve onaylama)
        # [AÇIKLAMA]: Park tabelası park_trigger_frames (örn: 3 kare) üst üste görülürse AKTIF moda geçilir.
        if self.park_state == "NORMAL":
            self._park_streak = (self._park_streak + 1) if yakin else 0
            if self._park_streak >= self.park_trigger_frames:
                self.park_state = "AKTIF"
                self._park_streak = 0
                print("[park] tabela {:.0f} cm -> AKTIF | hedef alan: {}{} | "
                      "gaz {:.2f} = PWM {:.0f}".format(
                          out.park_cm or -1, self.hedef_renk,
                          "" if self._renk_geldi else " (VARSAYILAN - "
                          "diðer Jetson'dan renk gelmedi!)",
                          self.park_throttle, self.park_pwm))
            return

        # DURUM 2: AKTIF (Zemindeki hedef rengi arama, oransal yönelme ve yanaşma)
        # [AÇIKLAMA]: detect_park_floor ile hedef renkteki (RED/GREEN/BLUE) zemin lekesi bulunur.
        try:
            red = detect_park_floor(raw_color, raw_depth, depth_scale,
                                    renk=self.hedef_renk,
                                    ust_kirp=self.ust_kirp,
                                    area_min=self.red_area_min,
                                    zemin_min_cm=self.zemin_min_cm,
                                    zemin_max_cm=self.zemin_max_cm)
        except Exception as e:
            red = None
            print("[park] detect_park_floor hatasý:", e)

        if red is not None:
            (rx, ry, rw, rh), red_cm, red_area = red
            out.red_bbox = (rx, ry, rw, rh)
            out.red_cm = red_cm
            self._red_gorulduy = True
            self._red_kayip = 0

            # [ORANSAL YÖNELME MATEMATİĞİ]:
            # Lekenin yatay merkezi (rx + rw/2) ile görüntü merkezi (w/2 = 320 px) arasındaki piksel farkı:
            # steer = (park_k * sapma_px) / max_delta  ([-1.0, +1.0] aralığına kırpılır)
            w = raw_color.shape[1]
            sapma_px = (rx + rw // 2) - (w // 2)
            steer = (self.park_k * sapma_px) / self.max_delta
            self._son_steer = max(-1.0, min(1.0, steer))

            # DURUŞ ŞARTI 1: Lekenin derinlik mesafesi park_dur_cm (örn: 25 cm) altına indiğinde araç durur.
            if red_cm is not None and red_cm < self.park_dur_cm:
                self.park_state = "ETTI"
                print("[park] kýrmýzý {:.0f} cm < {:.0f} -> PARK ETTÝ "
                      "(motor kalýcý 0)".format(red_cm, self.park_dur_cm))
        else:
            # DURUŞ ŞARTI 2: Leke daha önce görüldü ancak şimdi kayboldu (aracın burnunun altına girdi).
            # red_kayip_frames (örn: 5 kare) boyunca leke görülmezse kutunun üstüne çıkılmış sayılır ve durur.
            if self._red_gorulduy:
                self._red_kayip += 1
                if self._red_kayip >= self.red_kayip_frames:
                    self.park_state = "ETTI"
                    print("[park] kýrmýzý {} kare kayýp (üstünden geçildi) -> "
                          "PARK ETTÝ (motor kalýcý 0)".format(self._red_kayip))
