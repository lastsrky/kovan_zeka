"""
Trafik ışığı görevi: kırmızıda durur, yeşili görünce devam eder.

Karenin üst bandında kırmızı lamba arar; doğrulanınca motoru sıfırlar ve
direksiyona dokunmaz. DUR'dan çıkış şartı kırmızının kaybolması değil,
aynı sütunda YEŞİL görülmesidir.

Parkurun ilk görevidir ve bir kez tetiklenir.
"""
import time

import cv2
import numpy as np


# ==============================================================================
# TRAFİK IŞIĞI RENK VE FİLTRE SABİTLERİ
# ==============================================================================
# [AÇIKLAMA]: Kırmızı ışık HSV Renk Özü (Hue) bantları. OpenCV'de Hue 0-180 arasındadır;
#             kırmızı renk 0 noktasının iki tarafında yer aldığı için çift bant kullanılır.
# [NASIL DEĞİŞTİRİLİR]: Parantezleri ve virgülleri silmeyin, sadece sayıları değiştirin (örn: [(0, 10), (150, 180)]).
HUE_BANTLARI = [(0, 10), (150, 180)]

# [AÇIKLAMA]: Yeşil ışık HSV Renk Özü (Hue) bandı (35 ile 90 arası yeşil tonlarını filtreler).
# [NASIL DEĞİŞTİRİLİR]: Sayıları değiştirin (örn: [(35, 90)]).
YESIL_BANTLARI = [(35, 90)]
KERNEL = np.ones((3, 3), np.uint8)


def bbox_mesafe_cm(depth, x, y, w, h, depth_scale):
    """
    [AÇIKLAMA]: Bounding box içindeki derinlik piksellerinin medyanını alarak
                cm cinsinden araca olan net mesafeyi hesaplar.
    """
    if depth is None or not depth_scale:
        return None
    dh, dw = depth.shape[:2]
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(dw, x + w)
    y2 = min(dh, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    roi = depth[y1:y2, x1:x2].astype(np.float32)
    gecerli = roi[roi > 0]
    if gecerli.size < 3:
        return None
    return float(np.median(gecerli)) * depth_scale * 100.0


def detect_kirmizi_isik(color_image, ust_bant=0.60, s_min=60, v_min=150,
                        area_min=100, area_max=3000, max_aspect=2.0,
                        depth=None, depth_scale=None, max_mesafe_cm=0.0,
                        depth_yoksa_kabul=True, hue_bantlari=None,
                        hedef_merkez=None, hedef_tol_px=80,
                        return_mask=False):
    """
    [AÇIKLAMA]: Karenin üst bandında kırmızı ışık lambasını tespit eder ve doğrular.
    Parametrelerin fiziksel etkileri:
      - ust_bant: Görüntünün üst %60'ı taranır; alt %40'ı kesilerek yerdeki kırmızı yansımalar elenir.
      - s_min & v_min: Doygunluk ve parlaklık eşikleri (sönük veya soluk lambaları eler).
      - area_min & area_max: Piksel alanı sınırları (100 px altı gürültü, 3000 px üstü dev nesneler elenir).
      - max_aspect: En/boy oran toleransı (max(w,h) <= 2.0 * min(w,h)), daire/kare lambaları kabul eder; uzun şeritleri eler.
      - max_mesafe_cm: Bu mesafeden (örn: 90 cm) uzaktaki lambaları yok sayar.
      - hedef_merkez & hedef_tol_px: Araç durduğunda lambaya kilitlenir; sadece +/-80 px dairesel alanda takip eder.
    """
    h, w = color_image.shape[:2]
    hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)

    bantlar = hue_bantlari if hue_bantlari else HUE_BANTLARI
    mask = None
    for hlo, hhi in bantlar:
        m = cv2.inRange(hsv, np.array([int(hlo), int(s_min), int(v_min)]),
                        np.array([int(hhi), 255, 255]))
        mask = m if mask is None else (mask | m)

    # [ÜST BANT KIRPMA]: Yerdeki yansımaları ve aracın burnunu elemek için alt kısım maskeden silinir
    kesme = int(h * float(ust_bant))
    if 0 < kesme < h:
        mask[kesme:, :] = 0

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    adaylar = []
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        area = int(cv2.contourArea(cnt))
        # [ALAN FİLTRESİ]: Çok küçük veya devasa lekeleri eler
        if area < area_min:
            break
        if area > area_max:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw <= 0 or bh <= 0:
            continue
        # [EN/BOY ORAN (ASPECT RATIO) KONTROLÜ]:
        # Trafik lambası yuvarlak/karedir; yatay/düşey uzun şeritleri elemek için oran 2.0'ı aşamaz.
        if max(bw, bh) > max_aspect * min(bw, bh):
            continue
        # [DERİNLİK MESAFESİ KONTROLÜ]:
        cm = bbox_mesafe_cm(depth, x, y, bw, bh, depth_scale)
        if max_mesafe_cm > 0.0:
            if cm is not None and cm > max_mesafe_cm:
                continue
            if cm is None and not depth_yoksa_kabul:
                continue
        adaylar.append(((x, y, bw, bh), area, cm))

    sonuc = None
    if adaylar:
        if hedef_merkez is None:
            sonuc = adaylar[0]
        else:
            # [HEDEF KİLİTLEME]: Durulduktan sonra kilitlenen kırmızı lambanın piksel takibi
            hx, hy = hedef_merkez
            en_iyi, en_uzaklik = None, None
            for ad in adaylar:
                (x, y, bw, bh) = ad[0]
                dx = (x + bw // 2) - hx
                dy = (y + bh // 2) - hy
                u = (dx * dx + dy * dy) ** 0.5
                if u <= hedef_tol_px and (en_uzaklik is None or u < en_uzaklik):
                    en_iyi, en_uzaklik = ad, u
            sonuc = en_iyi
    if return_mask:
        return sonuc, mask
    return sonuc


def detect_yesil_isik(color_image, ust_bant=0.60, s_min=60, v_min=120,
                      area_min=100, area_max=3000, max_aspect=2.0,
                      hue_bantlari=None, hedef_x=None, x_tol_px=90):
    """
    [AÇIKLAMA]: Karenin üst bandında ve kilitlenen kırmızı lambanın hemen altında YEŞİL ışığı tespit eder.
    Parametrelerin fiziksel etkileri:
      - ust_bant: Görüntünün üst %60'ı taranır (zemin elenir).
      - s_min & v_min: Yeşil için minimum doygunluk ve parlaklık eşikleri.
      - area_min & area_max: Yeşil lamba piksel alanı sınırları.
      - hedef_x & x_tol_px: Kilitlenen kırmızı lambanın yatay X koordinatı alınır. Yeşil ışığın
        bu sütundan en fazla x_tol_px (90 px) sapmasına izin verilir. Böylece parkurdaki yeşil
        tabelalar veya yeşil zemin aracı yanıltamaz; sadece aynı direkteki yeşil lamba kabul edilir!
    """
    h, w = color_image.shape[:2]
    hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
    bantlar = hue_bantlari if hue_bantlari else YESIL_BANTLARI
    mask = None
    for hlo, hhi in bantlar:
        m = cv2.inRange(hsv, np.array([int(hlo), int(s_min), int(v_min)]),
                        np.array([int(hhi), 255, 255]))
        mask = m if mask is None else (mask | m)
    kesme = int(h * float(ust_bant))
    if 0 < kesme < h:
        mask[kesme:, :] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        area = int(cv2.contourArea(cnt))
        if area < area_min:
            break
        if area > area_max:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw <= 0 or bh <= 0:
            continue
        if max(bw, bh) > max_aspect * min(bw, bh):
            continue
        # [SÜTUN HİZALAMA DOĞRULAMASI]:
        # Yeşil ışık, daha önce durulan kırmızı lambanın tam düşey ekseninde mi kontrol edilir
        if hedef_x is not None and abs((x + bw // 2) - hedef_x) > x_tol_px:
            continue
        return ((x, y, bw, bh), area)
    return None


class TrafikSonuc(object):
    def __init__(self):
        self.state = "BEKLIYOR"
        self.dur = False
        self.bbox = None
        self.area = 0
        self.dist_cm = None
        self.kirmizi = False
        self.yesil = False
        self.yesil_bbox = None
        self.yesil_area = 0


class TrafikIsigi(object):
    def __init__(self, cfg=None):
        c = cfg or {}

        # ==============================================================================
        # TRAFİK IŞIĞI YAPILANDIRMA PARAMETRELERİ
        # ==============================================================================
        # [AÇIKLAMA]: Trafik ışığı görevini tamamen açar/kapatır (False ise kırmızıda durmaz).
        # [NASIL DEĞİŞTİRİLİR]: config.yaml -> trafik -> enable değerini true/false yapın.
        self.enabled = bool(c.get("enable", True))

        # [AÇIKLAMA]: Görüntünün üstten taranacak dikey oranı (%60).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.60 yerine 0.50 yazın).
        self.ust_bant = float(c.get("ust_bant", 0.60))

        # [AÇIKLAMA]: Kırmızı ışık minimum doygunluk eşiği (0-255).
        # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 60 yerine 70 yazın).
        self.s_min = int(c.get("s_min", 60))

        # [AÇIKLAMA]: Kırmızı ışık minimum parlaklık eşiği (0-255).
        # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 150 yerine 130 yazın).
        self.v_min = int(c.get("v_min", 150))

        # [AÇIKLAMA]: Kırmızı ışık lekesi minimum piksel alanı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 100).
        self.area_min = int(c.get("area_min", 100))

        # [AÇIKLAMA]: Kırmızı ışık lekesi maksimum piksel alanı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 3000).
        self.area_max = int(c.get("area_max", 3000))

        # [AÇIKLAMA]: En/boy oran toleransı (daire/kare şekil kontrolü).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 2.0).
        self.max_aspect = float(c.get("max_aspect", 2.0))

        # [AÇIKLAMA]: Kırmızı ışığın DUR durumunu tetiklemesi için üst üste görülmesi gereken kare sayısı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 3 yerine 2 yazın).
        self.dur_frames = int(c.get("dur_frames", 3))

        # [AÇIKLAMA]: Kırmızı görüldükten sonra durmadan önce normal hızda sürülecek yaklaşma süresi (saniye).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.0 yerine 0.5 yazın).
        self.gecikme_s = float(c.get("gecikme_s", 0.0))

        # [AÇIKLAMA]: DUR durumundayken yeşil ışığın kalkışı tetiklemesi için üst üste görülmesi gereken kare sayısı (~0.83 sn).
        #             Hakem "Yeşili görünce daha çabuk kalk" derse bu sayıyı düşürün (örn: 15 veya 10).
        # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 25 yerine 15 yazın).
        self.gec_frames = int(c.get("gec_frames", 25))

        # [AÇIKLAMA]: Durulduğunda kırmızı lambayı takip için dairesel piksel yarıçapı toleransı.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 80).
        self.kilit_tol_px = int(c.get("kilit_tol_px", 80))

        # [AÇIKLAMA]: Kırmızıda maksimum bekleme süresi emniyet tavanı (saniye). 0.0 olursa sınırsız bekler.
        #             Hakem "Yeşil yanmasa da 5 saniye sonra kalk" derse bu değeri 5.0 yapın.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 30.0 yerine 5.0 yazın). Noktayı silmeyin.
        self.max_dur_s = float(c.get("max_dur_s", 30.0))

        # [AÇIKLAMA]: Görevin parkurda tek seferlik çalışmasını sağlar.
        # [NASIL DEĞİŞTİRİLİR]: True veya False yazın.
        self.once = bool(c.get("once", True))

        # [AÇIKLAMA]: Kırmızı ışığın dikkate alınacağı maksimum derinlik mesafesi (cm).
        #             Hakem "Işığa daha çok yaklaşınca dur" derse bu sayıyı düşürün (örn: 70.0).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 200.0 yerine 90.0 yazın).
        self.max_mesafe_cm = float(c.get("max_mesafe_cm", 200.0))

        # [AÇIKLAMA]: Derinlik okunamadığında kırmızıyı kabul etme bayrağı.
        # [NASIL DEĞİŞTİRİLİR]: True veya False yazın.
        self.depth_yoksa_kabul = bool(c.get("depth_yoksa_kabul", False))

        yb = c.get("yesil_bantlari")
        self.yesil_bantlari = ([(int(a), int(b)) for a, b in yb] if yb
                               else list(YESIL_BANTLARI))

        # [AÇIKLAMA]: Yeşil ışık minimum doygunluk ve parlaklık eşikleri.
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıları değiştirin.
        self.yesil_s_min = int(c.get("yesil_s_min", 60))
        self.yesil_v_min = int(c.get("yesil_v_min", 120))
        self.yesil_area_min = int(c.get("yesil_area_min", 100))

        # [AÇIKLAMA]: Yeşil ışığın kırmızı kilit sütunundan izin verilen maksimum yatay sapması (piksel).
        # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 90).
        self.yesil_x_tol_px = int(c.get("yesil_x_tol_px", 90))

        hb = c.get("hue_bantlari")
        self.hue_bantlari = ([(int(a), int(b)) for a, b in hb] if hb
                             else list(HUE_BANTLARI))

        self.state = "BEKLIYOR"
        self._kirmizi_streak = 0
        self._temiz_streak = 0
        self._yesil_streak = 0
        self._t0 = 0.0
        self._kilit = None
        self._son_kirmizi = None

    def reset(self):
        self.state = "BEKLIYOR"
        self._kilit = None
        self._son_kirmizi = None
        self._kirmizi_streak = 0
        self._temiz_streak = 0
        self._yesil_streak = 0
        print("[trafik] görev sýfýrlandý")

    def idle(self):
        self._kirmizi_streak = 0
        self._temiz_streak = 0
        self._yesil_streak = 0
        out = TrafikSonuc()
        out.state = self.state
        return out

    def update(self, raw_color, raw_depth=None, depth_scale=None, now=None):
        out = TrafikSonuc()
        if now is None:
            now = time.time()
        if not self.enabled or self.state == "BITTI" or raw_color is None:
            out.state = "KAPALI" if not self.enabled else self.state
            return out

        if self.state == "DUR" and self._kilit is not None:
            res = detect_kirmizi_isik(raw_color, ust_bant=self.ust_bant,
                                      s_min=self.s_min, v_min=self.v_min,
                                      area_min=self.area_min,
                                      area_max=self.area_max,
                                      max_aspect=self.max_aspect,
                                      depth=raw_depth,
                                      depth_scale=depth_scale,
                                      max_mesafe_cm=0.0,
                                      hue_bantlari=self.hue_bantlari,
                                      hedef_merkez=self._kilit,
                                      hedef_tol_px=self.kilit_tol_px)
        else:
            res = detect_kirmizi_isik(raw_color, ust_bant=self.ust_bant,
                                      s_min=self.s_min, v_min=self.v_min,
                                      area_min=self.area_min,
                                      area_max=self.area_max,
                                      max_aspect=self.max_aspect,
                                      depth=raw_depth,
                                      depth_scale=depth_scale,
                                      max_mesafe_cm=self.max_mesafe_cm,
                                      depth_yoksa_kabul=self.depth_yoksa_kabul,
                                      hue_bantlari=self.hue_bantlari)
        if res is not None:
            out.bbox, out.area, out.dist_cm = res
            out.kirmizi = True

        if self.state == "DUR":
            yres = detect_yesil_isik(
                raw_color, ust_bant=self.ust_bant,
                s_min=self.yesil_s_min, v_min=self.yesil_v_min,
                area_min=self.yesil_area_min, area_max=self.area_max,
                max_aspect=self.max_aspect,
                hue_bantlari=self.yesil_bantlari,
                hedef_x=(self._kilit[0] if self._kilit else None),
                x_tol_px=self.yesil_x_tol_px)
            if yres is not None:
                out.yesil_bbox, out.yesil_area = yres
                out.yesil = True

        # ==============================================================================
        # ARDIŞIK KARE (STREAK) VE KARARLILIK SAYIMI
        # ==============================================================================
        # [AÇIKLAMA]: Kırmızı ışık görüldükçe sayaç artar, görülmediğinde sıfırlanır (kararlılık filtresi).
        if out.kirmizi:
            self._kirmizi_streak += 1
            self._temiz_streak = 0
        else:
            self._temiz_streak += 1
            self._kirmizi_streak = 0

        # [AÇIKLAMA]: Yeşil ışık görüldükçe sayaç artar, görülmediğinde sıfırlanır.
        if out.yesil:
            self._yesil_streak += 1
        else:
            self._yesil_streak = 0

        if out.kirmizi and out.bbox is not None:
            bx, by, bw_, bh_ = out.bbox
            self._son_kirmizi = (bx + bw_ // 2, by + bh_ // 2)

        # ==============================================================================
        # TRAFİK IŞIĞI DURUM MAKİNESİ (STATE MACHINE)
        # Durumlar: BEKLIYOR -> YAKLASMA -> DUR -> BITTI
        # ==============================================================================
        # DURUM 1: BEKLIYOR (Kırmızı ışığı arama ve onaylama)
        # [AÇIKLAMA]: Kırmızı ışık üst üste dur_frames (örn: 3 kare) görüldüğünde duruş tetiklenir.
        if self.state == "BEKLIYOR":
            if self._kirmizi_streak >= self.dur_frames:
                self._t0 = now
                if self.gecikme_s > 0.0:
                    self.state = "YAKLASMA"
                    print("[trafik] KIRMIZI IÞIK (alan={}, {}) -> YAKLASMA "
                          "({:.1f} sn normal sür, sonra DUR)".format(
                              out.area,
                              "{:.0f} cm".format(out.dist_cm)
                              if out.dist_cm is not None else "mesafe yok",
                              self.gecikme_s))
                else:
                    self.state = "DUR"
                    self._kilit = self._son_kirmizi
                    print("[trafik] KIRMIZI IÞIK (alan={}, {}) -> DUR  "
                          "[kilit {} | YEÞÝL bekleniyor ({} kare), "
                          "süre sýnýrý {}]".format(
                              out.area,
                              "{:.0f} cm".format(out.dist_cm)
                              if out.dist_cm is not None else "mesafe yok",
                              self._kilit, self.gec_frames,
                              "{:.0f} sn".format(self.max_dur_s)
                              if self.max_dur_s > 0 else "YOK"))

        # DURUM 2: YAKLASMA (Kırmızı görüldükten sonra durmadan önceki yaklaşma payı)
        # [AÇIKLAMA]: gecikme_s saniyesi boyunca sürüşe devam edilir; süre dolunca DUR durumuna geçer.
        elif self.state == "YAKLASMA":
            if (now - self._t0) >= self.gecikme_s:
                self.state = "DUR"
                self._t0 = now
                self._kilit = self._son_kirmizi
                print("[trafik] YAKLASMA bitti -> DUR  [kilit {} | YEÞÝL "
                      "bekleniyor ({} kare), süre sýnýrý {}]".format(
                          self._kilit, self.gec_frames,
                          "{:.0f} sn".format(self.max_dur_s)
                          if self.max_dur_s > 0 else "YOK"))

        # DURUM 3: DUR (Kırmızı ışıkta tam duruş ve yeşil bekleme)
        # [AÇIKLAMA]: out.dur = True döner; motor kapatılır.
        # İki kalkış koşulu vardır:
        #   1. Yeşil lamba gec_frames (örn: 25 kare) boyunca üst üste görülürse kalkar.
        #   2. max_dur_s > 0 ise ve bu süre dolarsa yeşil yanmasa dahi emniyetten kalkar.
        elif self.state == "DUR":
            gecti = False
            sebep = ""
            # KALKIŞ KOŞULU 1: Yeşil ışık doğrulandı
            if self._yesil_streak >= self.gec_frames:
                gecti = True
                sebep = "YEÞÝL görüldü (alan={})".format(out.yesil_area)
            # KALKIŞ KOŞULU 2: Emniyet zaman aşımı doldu (max_dur_s > 0 ise)
            elif self.max_dur_s > 0 and (now - self._t0) >= self.max_dur_s:
                gecti = True
                sebep = "EMNÝYET: {:.0f} sn doldu, yeþil görülmedi".format(
                    self.max_dur_s)
            if gecti:
                self.state = "BITTI" if self.once else "BEKLIYOR"
                self._kilit = None
                print("[trafik] {} -> devam ({})".format(sebep, self.state))

        out.state = self.state
        out.dur = (self.state == "DUR")
        return out


def draw_trafik(vis, tr, ust_bant=0.60):
    h, w = vis.shape[:2]
    kesme = int(h * float(ust_bant))
    cv2.line(vis, (0, kesme), (w, kesme), (0, 140, 255), 1)
    if tr.yesil_bbox is not None:
        gx, gy, gw, gh = tr.yesil_bbox
        cv2.rectangle(vis, (gx, gy), (gx + gw, gy + gh), (0, 255, 0), 3)
        cv2.putText(vis, "YESIL a={}".format(tr.yesil_area),
                    (gx, max(15, gy - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 0), 2, cv2.LINE_AA)
    if tr.bbox is not None:
        x, y, bw, bh = tr.bbox
        cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 0, 255), 3)
        etiket = "KIRMIZI a={}".format(tr.area)
        if tr.dist_cm is not None:
            etiket += " {:.0f}cm".format(tr.dist_cm)
        cv2.putText(vis, etiket, (x, max(15, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
                    cv2.LINE_AA)
    return vis


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Trafik ýþýðý kýrmýzý tespitini canlý ayarla")
    ap.add_argument("--ust-bant", type=float, default=None)
    ap.add_argument("--s-min", type=int, default=None)
    ap.add_argument("--v-min", type=int, default=None)
    ap.add_argument("--max-cm", type=float, default=None,
                    help="mesafe filtresi (0 = kapali)")
    args = ap.parse_args()

    from config_loader import load_config
    from camera import RealSenseCamera

    cfg = load_config()
    tcfg = dict(cfg.get("trafik", {}) or {})
    if args.ust_bant is not None:
        tcfg["ust_bant"] = args.ust_bant
    if args.s_min is not None:
        tcfg["s_min"] = args.s_min
    if args.v_min is not None:
        tcfg["v_min"] = args.v_min
    if args.max_cm is not None:
        tcfg["max_mesafe_cm"] = args.max_cm
    tcfg["enable"] = True
    tcfg["once"] = False

    cam_cfg = dict(cfg["camera"])
    cam_cfg["crop_top_ratio"] = 0.0
    cam_cfg["enable_depth"] = True

    tr_ctl = TrafikIsigi(tcfg)
    print("[trafik] ust_bant=%.2f  S>=%d V>=%d  alan=%d..%d  aspect<=%.1f"
          % (tr_ctl.ust_bant, tr_ctl.s_min, tr_ctl.v_min, tr_ctl.area_min,
             tr_ctl.area_max, tr_ctl.max_aspect))
    print("[trafik] mesafe filtresi: <= %.0f cm  (depth yoksa kabul: %s)"
          % (tr_ctl.max_mesafe_cm, tr_ctl.depth_yoksa_kabul))
    print("[trafik] hue bantlari: %s" % (tr_ctl.hue_bantlari,))
    print("[trafik] [q] cikis   [r] gorevi sifirla")
    cam = RealSenseCamera(cam_cfg)
    cam.start()
    try:
        while True:
            ok, frame, _ = cam.read_with_depth()
            if not ok:
                continue
            raw = cam.last_raw_color
            rawd = cam.last_raw_depth
            res, mask = detect_kirmizi_isik(
                raw, ust_bant=tr_ctl.ust_bant, s_min=tr_ctl.s_min,
                v_min=tr_ctl.v_min, area_min=tr_ctl.area_min,
                area_max=tr_ctl.area_max, max_aspect=tr_ctl.max_aspect,
                depth=rawd, depth_scale=cam.depth_scale,
                max_mesafe_cm=tr_ctl.max_mesafe_cm,
                depth_yoksa_kabul=tr_ctl.depth_yoksa_kabul,
                hue_bantlari=tr_ctl.hue_bantlari,
                return_mask=True)
            tr = tr_ctl.update(raw, rawd, cam.depth_scale)
            vis = draw_trafik(raw.copy(), tr, tr_ctl.ust_bant)
            karar = "DUR (kirmizi)" if tr.dur else "GEC (kirmizi yok)"
            renk = (0, 0, 255) if tr.dur else (0, 255, 0)
            for txt, yy in (("durum: %s" % tr.state, 24),
                            (karar, 50),
                            ("alan: %d  mesafe: %s  streak k=%d t=%d" % (
                                tr.area,
                                "%.0fcm" % tr.dist_cm
                                if tr.dist_cm is not None else "-",
                                tr_ctl._kirmizi_streak,
                                tr_ctl._temiz_streak), 76)):
                cv2.putText(vis, txt, (10, yy), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(vis, txt, (10, yy), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, renk, 1, cv2.LINE_AA)
            cv2.imshow("trafik isigi", vis)
            cv2.imshow("kirmizi maske (ust bant)", mask)
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            elif k == ord("r"):
                tr_ctl.reset()
    finally:
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
