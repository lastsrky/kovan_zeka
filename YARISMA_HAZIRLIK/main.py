"""
Aracın ana döngüsü.

Her karede sırasıyla: kamera -> şerit tespiti -> görevler -> PID -> motor.
Görevler (trafik ışığı, yaya geçidi, park, sollama) gerektiğinde şerit
takibini geçici olarak devralır; hiçbiri devrede değilse araç PID ile
şeridi takip eder.

Tuşlar: space otonom aç/kapa, +/- gaz, r PID reset, o sollama sıfırla,
t görev sıfırla, c renk+basla sıfırla, k ekran görüntüsü, q çıkış.
"""
import argparse
import os
import time
import signal
import sys

import cv2
import numpy as np

from config_loader import load_config
from camera import RealSenseCamera
from vision import LineDetector, draw_debug
from controller import PIDController
from motor import create_motor 
from overtake import OvertakeController
from colorlink import ColorLink
from tabela_gorev import TabelaGorevleri
from tabela import draw_tabela
from trafik import TrafikIsigi, draw_trafik

SHOT_DIR = os.path.expanduser("~/Desktop/resim")


def save_shot(vis, mask, raw_frame, index):
    try:
        os.makedirs(SHOT_DIR)
    except OSError:
        pass

    stamp = time.strftime("%H%M%S")
    base = "kare_%03d_%s" % (index, stamp)
    png_path = os.path.join(SHOT_DIR, base + ".png")

    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    if mask_bgr.shape[0] == vis.shape[0]:
        combo = np.hstack([vis, mask_bgr])
    else:
        combo = vis
    cv2.imwrite(png_path, combo)

    npy_path = os.path.join(SHOT_DIR, base + ".npy")
    try:
        np.save(npy_path, raw_frame)
    except Exception:
        npy_path = None

    print("[main] ekran goruntusu -> %s%s" %
          (png_path, "  (+ham kare .npy)" if npy_path else ""))
    return png_path


def parse_args():
    ap = argparse.ArgumentParser(description="Otonom çizgi takip aracý")
    ap.add_argument("--config", default=None, help="config.yaml yolu")
    ap.add_argument("--dummy", action="store_true",
                    help="motor donanýmý olmadan çalýþtýr (DummyMotor)")
    ap.add_argument("--no-debug", action="store_true",
                    help="debug overlay penceresini gösterme")
    ap.add_argument("--throttle", type=float, default=None,
                    help="baþlangýç gazýný override et (0..1)")
    ap.add_argument("--record", action="store_true",
                    help="her kareyi CSV+ham kare olarak kaydet (teþhis)")
    ap.add_argument("--no-remote", action="store_true",
                    help="MQTT renk/basla beklemeden elle kontrol (tezgah "
                         "testi): space doðrudan otonomu açar")
    return ap.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)

    # ==============================================================================
    # RUN VE HIZ PARAMETRELERİ (config.yaml'dan okunur, yoksa fallback kullanılır)
    # ==============================================================================
    # [AÇIKLAMA]: Görsel hata ayıklama (debug overlay) pencerelerini açar/kapatır.
    # [NASIL DEĞİŞTİRİLİR]: Sadece True veya False yazın (Baş harf BÜYÜK olmalıdır).
    debug = bool(cfg.get("run", {}).get("debug", True)) and not args.no_debug

    # [AÇIKLAMA]: Açılıştaki varsayılan gaz oranı (0.0 = araç beklemede kalır).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.0 yerine 0.25 yazın). Virgül KULLANMAYIN.
    throttle = cfg.get("run", {}).get("default_throttle", 0.0)
    if args.throttle is not None:
        throttle = args.throttle

    spd = cfg.get("speed", {})
    # [AÇIKLAMA]: Viraj eğim ölü bölgesi eşiği. Bu değerin altındaki virajlarda hız kesilmez.
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.9 yerine 1.0 yazın).
    slope_deadzone = float(spd.get("slope_deadzone", 0.9))

    # [AÇIKLAMA]: Virajda gaz kesme şiddeti katsayısı. Artarsa araç keskin virajlarda daha çok yavaşlar.
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.35 yerine 0.45 yazın).
    speed_gain = float(spd.get("speed_gain", 0.35))

    # [AÇIKLAMA]: Frenleme/yavaşlama adım büyüklüğü (kare başına maksimum gaz düşüşü).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.10 yerine 0.15 yazın).
    throttle_rate_down = float(spd.get("throttle_rate_down", 0.10))

    # [AÇIKLAMA]: Hızlanma adım büyüklüğü (kare başına maksimum gaz artışı - ani kalkışı önler).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.02 yerine 0.03 yazın).
    throttle_rate_up = float(spd.get("throttle_rate_up", 0.02))

    # [AÇIKLAMA]: Minimum hareket PWM tabanı (aracın sürtünmeden dolayı bayılmasını önleyen donanımsal alt sınır).
    # [NASIL DEĞİŞTİRİLİR]: Sadece tamsayıyı değiştirin (örn: 90 yerine 80 veya 100 yazın).
    min_move_pwm = float(spd.get("min_move_pwm", 90))

    # [AÇIKLAMA]: Sol şerit 4 kare kayıpsa uygulanacak gaz çarpanı (%75 hız).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.75 yerine 0.70 yazın).
    lm_scale_kayip4 = float(spd.get("lm_scale_kayip4", 0.75))

    # [AÇIKLAMA]: Sol şerit 2 kare kayıpsa uygulanacak gaz çarpanı (%80 hız).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.80 yerine 0.75 yazın).
    lm_scale_kayip2 = float(spd.get("lm_scale_kayip2", 0.80))

    # [AÇIKLAMA]: Kesikli şerit sonu algılandığında uygulanacak gaz çarpanı (%85 hız).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.85 yerine 0.80 yazın).
    lm_scale_ending = float(spd.get("lm_scale_ending", 0.85))
    sent_throttle = 0.0

    cam = RealSenseCamera(cfg["camera"])
    detector = LineDetector(cfg["vision"])
    pid = PIDController(cfg["controller"])
    motor = create_motor(cfg["motor"], use_dummy=args.dummy)
    overtake = OvertakeController(
        cfg.get("overtake", {}),
        lane_half_width_px=float(cfg["vision"].get("lane_half_width_px", 232)))

    gorevler = TabelaGorevleri(
        cfg.get("tabela", {}), cfg.get("yaya", {}), cfg.get("park", {}),
        max_pwm=int(cfg["motor"].get("throttle_max_pwm", 300)),
        max_delta=int(cfg["motor"].get("steering_max_delta", 35)))
    gorevler.start()
    onceki_gorev = gorevler.state

    trafik = TrafikIsigi(cfg.get("trafik", {}))
    print("[trafik] {} (kýrmýzýda dur; üst %{:.0f} taranýr)".format(
        "AÇIK" if trafik.enabled else "KAPALI", trafik.ust_bant * 100))

    link = ColorLink(cfg.get("colorlink", {}))
    if args.no_remote:
        link.enabled = False
        link.require_for_start = False
        link.auto_start = False
    link.start()
    baslangic_renk = None
    start_uygulandi = False
    # [AÇIKLAMA]: Uzaktan (MQTT) start mesajı geldiğinde otomatik verilecek başlangıç gazı (%30 = ~90 PWM).
    # [NASIL DEĞİŞTİRİLİR]: Sadece sayıyı değiştirin (örn: 0.30 yerine 0.35 yazın). Noktayı koruyun.
    start_throttle = float(cfg.get("run", {}).get("start_throttle", 0.30))

    stop_flag = {"stop": False}

    def _sigint(signum, frame):
        stop_flag["stop"] = True
    signal.signal(signal.SIGINT, _sigint)

    fps = 0.0
    fps_t0 = time.time()
    fps_frames = 0

    kirp_ofset = int(cfg["camera"].get("height", 480) *
                     float(cfg["camera"].get("crop_top_ratio", 0.0)))
    autonomous = False
    max_pwm = int(cfg["motor"].get("throttle_max_pwm", 300))
    shot_count = 0

    rec_csv = None
    rec_raws = None
    rec_dir = None
    if args.record:
        rec_dir = os.path.join(SHOT_DIR, "rec_" + time.strftime("%H%M%S"))
        try:
            os.makedirs(rec_dir)
        except OSError:
            pass
        rec_csv = open(os.path.join(rec_dir, "log.csv"), "w")
        rec_csv.write("frame,dev,raw_dev,servo,steer,lines,durum,auto,"
                      "throttle,slope,eff_gaz,eff_pwm,left_missing,"
                      "left_ending,corner_turn,sollama,kutu_cm,shift_px,"
                      "renk,yaya,yaya_cm,park,park_cm,kirmizi_cm,"
                      "trafik,trafik_alan\n")
        rec_raws = []
        print("[main] KAYIT modu -> {}".format(rec_dir))

    print("=" * 56)
    print(" Çizgi takip baþlýyor.")
    print("  [space] otonom aç/kapa      [q] çýkýþ")
    print("  [+]/[-] gaz  +/-0.05        [0-9] gazý doðrudan ayarla")
    print("  [r] PID reset               [k] ekran görüntüsü")
    print("  [o] sollamayý yeniden kur   (sollama: {})".format(
        "AÇIK" if overtake.enabled else "KAPALI"))
    print("  [t] trafik+yaya+park sýfýrla [c] renk+basla sýfýrla + dur")
    if link.auto_start and link.enabled:
        print("  UZAKTAN START: renk(RED/GREEN/BLUE) + basla gelince OTOMATÝK")
        print("                 baþlar, gaz={:.2f}. Durum: {}".format(
            start_throttle, link.durum()))
    else:
        print("  UZAKTAN START: KAPALI (renk/basla aracý baþlatmaz)")
    if link.require_for_start:
        print("  SPACE        : renk+basla gelmeden ENGELLÝ")
    else:
        print("  SPACE        : her zaman çalýþýr (manuel deneme)")
    if link.enabled and not link.auto_start:
        print("                 renk yine DÝNLENÝYOR (park hedefi için)")
    print("  Ekran görüntüleri -> {}".format(SHOT_DIR))
    print("  Baþlangýç: otonom KAPALI, gaz={:.2f} (PWM tavaný {})".format(
        throttle, max_pwm))
    print("=" * 56)

    try:
        cam.start()
        while not stop_flag["stop"]:
            ok, frame, depth = cam.read_with_depth()
            if not ok:
                print("[main] frame alýnamadý, atlanýyor")
                continue

            yeni_renk = link.renk
            if yeni_renk != baslangic_renk:
                baslangic_renk = yeni_renk
                print("[main] renk: {}".format(baslangic_renk))
            gorevler.set_hedef_renk(baslangic_renk)

            if link.auto_start and link.hazir and not start_uygulandi:
                start_uygulandi = True
                if throttle <= 0.0:
                    throttle = start_throttle
                autonomous = True
                pid.reset()
                print("[main] UZAKTAN START: renk={} gaz={:.2f} "
                      "(PWM ~{:.0f}) -> otonom ON".format(
                          baslangic_renk, throttle, throttle * max_pwm))

            res = detector.process(frame)

            # ==============================================================================
            # GÖREV GÜNCELLEME VE ARBİTRASYON (ÖNCELİK KONTROLÜ)
            # ==============================================================================
            # [AÇIKLAMA]: Tabela görevleri (Yaya geçidi ve Park durum makineleri) çalıştırılır.
            if autonomous:
                gorev = gorevler.update(cam.last_raw_color,
                                        cam.last_raw_depth, cam.depth_scale)
            else:
                gorev = gorevler.idle()
            if onceki_gorev == "GEC" and gorev.state != "GEC":
                detector.reset_memory()
                pid.reset()
                sent_throttle = 0.0
                print("[main] geçit sonrasý þerit hafýzasý sýfýrlandý")
            onceki_gorev = gorev.state

            # [AÇIKLAMA]: Park görevi aktif olduğunda ("AKTIF" veya "ETTI"), trafik ışığı ve
            #             sollama modülleri devre dışı bırakılır (görev çakışmasını önleyen bayrak).
            # [NASIL DEĞİŞTİRİLİR]: Kod mantığıdır; tırnakları veya parantezleri silmeyin.
            park_devrede = gorev.park_state in ("AKTIF", "ETTI")

            # [AÇIKLAMA]: Trafik ışığı denetimi: Park devrede DEĞİLSE ve otonom açıksa çalışır.
            if autonomous and not park_devrede:
                tr = trafik.update(cam.last_raw_color,
                                   cam.last_raw_depth, cam.depth_scale)
            else:
                tr = trafik.idle()

            # [AÇIKLAMA]: Sollama (engelden kaçma) denetimi: Park devrede DEĞİLSE çalışır.
            if autonomous and not park_devrede:
                ovt = overtake.update(cam.last_raw_color, cam.last_raw_depth,
                                      cam.depth_scale, res)
            else:
                ovt = overtake.idle()
            detector.set_lane_shift(ovt.shift_px)

            # ==============================================================================
            # DİREKSİYON ARBİTRASYONU (ÖNCELİK SIRALAMASI)
            # ==============================================================================
            # 1. ÖNCELİK: Park Manevrası (Zemindeki hedef renkli alana yönelme)
            # [AÇIKLAMA]: Park lekesi görüldüğünde şerit takibi ve PID sıfırlanır; araç renge kilitlenir.
            if gorev.steer is not None:
                steer = gorev.steer
                pid.reset()
            # 2. ÖNCELİK: Yaya Geçidi Kör Düz Geçiş
            # [AÇIKLAMA]: Zebra çizgileri şerit takibini bozmasın diye direksiyon tam düz (0.0) tutulur.
            elif gorev.duz_git:
                steer = 0.0
                pid.reset()
            # 3. ÖNCELİK: 90 Derece Keskin Köşe Dönüşü
            # [AÇIKLAMA]: Şerit algoritması keskin viraj/T-kavşak yakaladığında sabit açı basılır.
            elif res.corner_turn != 0.0:
                steer = res.corner_turn
                pid.reset()
            # 4. ÖNCELİK: Normal Şerit Takip PID Kontrolü
            # [AÇIKLAMA]: Yol şeridi tespit edildiğinde PID kontrolcüsü sapmayı açıya çevirir.
            elif res.found:
                steer = pid.update(res.deviation)
            # 5. ÖNCELİK: Şerit Kayıp / Güvenli Mod
            # [AÇIKLAMA]: Hiçbir şerit bulunamazsa direksiyon düzlenir (0.0) ve PID sıfırlanır.
            else:
                steer = 0.0
                pid.reset()

            # ==============================================================================
            # HIZ ŞEKİLLENDİRME VE VİRAJ YAVAŞLAMASI (SPEED SHAPING)
            # ==============================================================================
            # [AÇIKLAMA]: Eğim ölü bölgeyi (slope_deadzone) aştığında viraj sertliğine göre gaz kesilir.
            etkin = max(0.0, res.slope_metric - slope_deadzone)
            slope_scale = max(0.0, 1.0 - speed_gain * etkin)

            # [AÇIKLAMA]: Eksik şerit cezaları: Sol çizgi kayboldukça güvenlik için gaz kademeli kısılır.
            if res.left_missing >= 4:
                lm_scale = lm_scale_kayip4
            elif res.left_missing >= 2:
                lm_scale = lm_scale_kayip2
            elif res.left_ending:
                lm_scale = lm_scale_ending
            else:
                lm_scale = 1.0

            # [AÇIKLAMA]: Nihai hedef gaz = Ana gaz * Viraj çarpanı * Eksik şerit çarpanı * Sollama çarpanı.
            hedef_gaz = throttle * min(slope_scale, lm_scale) * \
                ovt.throttle_scale

            # [AÇIKLAMA]: Görev gazı bayrağı (Yaya kör geçiş veya park yanaşma kendi özel gazını dikte eder).
            gorev_suruyor = (gorev.throttle is not None)

            eff_pwm = 0
            # ==============================================================================
            # FREN VE MOTOR ÇIKIŞI ARBİTRASYONU
            # ==============================================================================
            # 1. ACİL VE GÖREV DURUŞU: Trafik ışığı kırmızıysa veya yaya/park durma emri verdiyse
            # [AÇIKLAMA]: Motor derhal kapatılır (motor.stop) ve gaz sıfırlanır. Direksiyona dokunulmaz.
            if gorev.dur or tr.dur:
                motor.set_steering(steer)
                motor.stop()
                sent_throttle = 0.0
                eff_pwm = 0
            # 2. NORMAL OTONOM SÜRÜŞ VE GAZ RAMPALAMA (SLEW-RATE):
            elif autonomous and (res.found or gorev_suruyor or
                                 res.corner_turn != 0.0):
                if gorev_suruyor:
                    # Görev kendi özel sabit gazını (örn: yaya gec_pwm veya park_pwm) doğrudan uygular
                    sent_throttle = gorev.throttle
                else:
                    # Gaz yumuşatma (slew-rate): Gaz aniden verilmez, kademeli artırılır/azaltılır
                    delta = hedef_gaz - sent_throttle
                    step = (throttle_rate_up if delta > 0
                            else throttle_rate_down)
                    if abs(delta) > step:
                        sent_throttle += step if delta > 0 else -step
                    else:
                        sent_throttle = hedef_gaz

                # [AÇIKLAMA]: GAZ TABANI (THROTTLE FLOOR / min_move_pwm):
                #             Gaz sıfırdan büyükse motora giden PWM min_move_pwm (örn: 80 veya 90 PWM)
                #             altına düşemez; böylece aracın sürtünmeyi yenemeyip durması önlenir.
                # [NASIL DEĞİŞTİRİLİR]: Tabanı değiştirmek için config.yaml -> speed -> min_move_pwm düzenlenmelidir.
                if throttle > 0.0:
                    min_scale = min_move_pwm / max(1.0, float(max_pwm))
                    if sent_throttle < min_scale:
                        sent_throttle = min_scale
                eff_pwm = int(round(sent_throttle * max_pwm))

                motor.set_steering(steer)
                motor.set_throttle(sent_throttle)
            # 3. GÜVENLİ DURUŞ (Şerit Yok veya Otonom Kapalı):
            else:
                motor.set_steering(0.0)
                motor.stop()
                sent_throttle = 0.0
                eff_pwm = 0

            if rec_csv is not None and autonomous:
                if hasattr(motor, "deviation_to_angle"):
                    rec_ang = motor.deviation_to_angle(steer)
                else:
                    rec_ang = 0
                durum = "LOST" if not res.found else (
                    "MEM" if res.from_memory else (res.rejected or "OK"))
                raw_dev = res.raw_deviation if res.raw_deviation is not None \
                    else res.deviation
                fi = len(rec_raws)
                rec_csv.write(
                    "%d,%.4f,%.4f,%d,%.4f,%d,%s,%d,%.2f,%.3f,%.3f,%d,%d,%d,"
                    "%.1f,%s,%.0f,%.1f,%s,%s,%.0f,%s,%.0f,%.0f,%s,%d\n"
                    % (fi, res.deviation, raw_dev, rec_ang, steer,
                       res.n_components, durum, 1, throttle,
                       res.slope_metric, sent_throttle, eff_pwm,
                       res.left_missing, 1 if res.left_ending else 0,
                       res.corner_turn,
                       ovt.state,
                       ovt.dist_cm if ovt.dist_cm is not None else -1.0,
                       ovt.shift_px,
                       baslangic_renk or "-",
                       gorev.state,
                       gorev.dist_cm if gorev.dist_cm is not None else -1.0,
                       gorev.park_state,
                       gorev.park_cm if gorev.park_cm is not None else -1.0,
                       gorev.red_cm if gorev.red_cm is not None else -1.0,
                       tr.state, tr.area))
                rec_csv.flush()
                rec_raws.append(frame.copy())
                if fi > 0 and fi % 90 == 0:
                    try:
                        np.save(os.path.join(rec_dir, "frames.npy"),
                                np.array(rec_raws))
                    except Exception:
                        pass

            fps_frames += 1
            now = time.time()
            if now - fps_t0 >= 0.5:
                fps = fps_frames / (now - fps_t0)
                fps_frames = 0
                fps_t0 = now

            if debug:
                if autonomous and hedef_gaz < sent_throttle - 1e-6:
                    gaz_yon = "FREN"
                elif autonomous and hedef_gaz > sent_throttle + 1e-6:
                    gaz_yon = "TOPLA"
                else:
                    gaz_yon = "-"
                extra = [
                    "steer: {:+.3f}".format(steer),
                    "slope: {:.2f}  etkin: {:.2f}".format(
                        res.slope_metric, etkin),
                    "gaz: {:.2f} -> PWM {} [{}]".format(
                        throttle, eff_pwm, gaz_yon),
                    "left_missing: {}  ending: {}".format(
                        res.left_missing, "E" if res.left_ending else "-"),
                    "uzak: {}".format(link.durum()),
                    "trafik: {}{}".format(
                        tr.state,
                        "  KIRMIZI a={} {}".format(
                            tr.area,
                            "{:.0f}cm".format(tr.dist_cm)
                            if tr.dist_cm is not None else "?cm")
                        if tr.kirmizi else ""),
                    "yaya: {}  {}  tespit:{}".format(
                        gorev.state,
                        "{:.0f}cm".format(gorev.dist_cm)
                        if gorev.dist_cm is not None else "-",
                        len(gorev.dets)),
                    "park: {}  hedef:{}  tabela:{}  alan:{}".format(
                        gorev.park_state,
                        gorev.hedef_renk or "-",
                        "{:.0f}cm".format(gorev.park_cm)
                        if gorev.park_cm is not None else "-",
                        "{:.0f}cm".format(gorev.red_cm)
                        if gorev.red_cm is not None else "-"),
                    "sollama: {}  kutu: {}  shift: {:.0f}px".format(
                        ovt.state,
                        "{:.0f}cm".format(ovt.dist_cm)
                        if ovt.dist_cm is not None else "-",
                        ovt.shift_px),
                    "auto: {}".format("ON" if autonomous else "OFF"),
                    "fps: {:.1f}".format(fps),
                ]
                if hasattr(motor, "deviation_to_angle"):
                    angle = motor.deviation_to_angle(steer)
                    extra.insert(1, "servo: {} der ({})".format(
                        angle,
                        "SOL" if angle < motor.center else
                        ("SAG" if angle > motor.center else "ORTA")))
                extra.append("[k] ekran goruntusu ({})".format(shot_count))
                vis = draw_debug(frame, res, extra_lines=extra)
                if ovt.bbox is not None:
                    bx, by, bw_, bh_ = ovt.bbox
                    by -= kirp_ofset
                    yakin = (ovt.dist_cm is not None and
                             ovt.dist_cm < overtake.trigger_cm)
                    col = (0, 140, 255) if yakin else (0, 200, 255)
                    cv2.rectangle(vis, (bx, by), (bx + bw_, by + bh_), col, 2)
                    cv2.putText(vis, "KUTU {:.0f}cm a={}".format(
                        ovt.dist_cm, ovt.area), (bx, max(15, by - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
                if ovt.state in ("GECIS", "OTUR"):
                    h_, w_ = vis.shape[:2]
                    txt = "SAGA GEC" if ovt.state == "GECIS" else "OTURUYOR"
                    cv2.putText(vis, txt, (w_ // 2 - 140, h_ // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 6,
                                cv2.LINE_AA)
                    cv2.putText(vis, txt, (w_ // 2 - 140, h_ // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 140, 255),
                                3, cv2.LINE_AA)
                if res.corner_turn != 0.0 and not park_devrede:
                    h_, w_ = vis.shape[:2]
                    cv2.putText(vis, "TURN LEFT", (w_ // 2 - 150, h_ // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 6,
                                cv2.LINE_AA)
                    cv2.putText(vis, "TURN LEFT", (w_ // 2 - 150, h_ // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 3,
                                cv2.LINE_AA)
                if tr.dur or tr.state == "YAKLASMA" or \
                        gorev.park_state in ("AKTIF", "ETTI") or \
                        gorev.state in ("YAKLASMA", "DUR", "GEC"):
                    h_, w_ = vis.shape[:2]
                    if tr.dur:
                        yazi, renk_ = "KIRMIZI ISIK - DUR", (0, 0, 255)
                    elif tr.state == "YAKLASMA":
                        yazi, renk_ = "KIRMIZI ISIK - YAKLASIYOR", (0, 200, 255)
                    elif gorev.park_state == "ETTI":
                        yazi, renk_ = "PARK ETTI", (0, 255, 0)
                    elif gorev.park_state == "AKTIF":
                        _hr = gorev.hedef_renk or "?"
                        yazi = ("PARK: {} ALANA YONEL".format(_hr)
                                if gorev.red_bbox is not None
                                else "PARK: {} ALAN ARANIYOR".format(_hr))
                        renk_ = (0, 200, 255)
                    else:
                        renk_ = (0, 0, 255) if gorev.state == "DUR" else \
                            (0, 200, 255)
                        yazi = {"YAKLASMA": "YAYA YAKLASIYOR",
                                "DUR": "DUR (YAYA)",
                                "GEC": "GECITTEN GEC"}[gorev.state]
                    cv2.putText(vis, yazi, (w_ // 2 - 190, h_ // 2 + 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6,
                                cv2.LINE_AA)
                    cv2.putText(vis, yazi, (w_ // 2 - 190, h_ // 2 + 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.3, renk_, 3,
                                cv2.LINE_AA)
                cv2.imshow("line-follow (debug)", vis)
                cv2.imshow("mask", res.mask)
                if cam.last_raw_color is not None:
                    tvis = draw_tabela(cam.last_raw_color.copy(), gorev.dets,
                                       cam.last_raw_depth, cam.depth_scale)
                    draw_trafik(tvis, tr, trafik.ust_bant)
                    if gorev.red_bbox is not None:
                        rx, ry, rw_, rh_ = gorev.red_bbox
                        pcol = {"RED": (0, 0, 255), "GREEN": (0, 200, 0),
                                "BLUE": (255, 0, 0)}.get(gorev.hedef_renk,
                                                         (0, 0, 255))
                        cv2.rectangle(tvis, (rx, ry), (rx + rw_, ry + rh_),
                                      pcol, 3)
                        cv2.line(tvis, (rx + rw_ // 2, ry),
                                 (rx + rw_ // 2, ry + rh_), pcol, 2)
                        cv2.putText(tvis, "{} {}".format(
                            gorev.hedef_renk or "PARK",
                            "{:.0f}cm".format(gorev.red_cm)
                            if gorev.red_cm is not None else "?"),
                            (rx, max(15, ry - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, pcol, 2,
                            cv2.LINE_AA)
                    bilgi = "trafik:{}  yaya:{}  park:{} ({})".format(
                        tr.state, gorev.state, gorev.park_state,
                        gorev.hedef_renk or "-")
                    cv2.putText(tvis, bilgi, (10, 24),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3,
                                cv2.LINE_AA)
                    cv2.putText(tvis, bilgi, (10, 24),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255),
                                1, cv2.LINE_AA)
                    cv2.imshow("tabela (ham kare)", tvis)
                key = cv2.waitKey(1) & 0xFF
                # ==============================================================================
                # KLAVYE ETKİLEŞİMİ VE ÇALIŞMA ZAMANI MANUEL MÜDAHALE KONTROLLERİ
                # ==============================================================================
                if key == ord("q"):
                    # [AÇIKLAMA]: Programı güvenle sonlandırır, motoru ve kamerayı kapatır.
                    break
                elif key == ord(" "):
                    # [AÇIKLAMA]: Space tuşu otonom sürüşü başlatır veya durdurur.
                    #             link.require_for_start=True ise robot koldan MQTT start mesajı gelmeden başlamaz!
                    # [NASIL DEĞİŞTİRİLİR]: config.yaml -> colorlink -> require_for_start: false yapılırsa her zaman başlar.
                    if (not autonomous and link.require_for_start and
                            not link.hazir):
                        print("[main] BAÞLATILAMADI: {} "
                              "(tezgah testi için --no-remote)".format(
                                  link.durum()))
                    else:
                        autonomous = not autonomous
                        pid.reset()
                        if not autonomous:
                            motor.stop()
                        print("[main] otonom:",
                              "ON" if autonomous else "OFF")
                        if autonomous and throttle <= 0.0:
                            print("[main] DÝKKAT: gaz 0.00 -> araç hareket "
                                  "ETMEZ. '3' tuþu = 0.30, '+' ile artýr.")
                elif key == ord("r"):
                    # [AÇIKLAMA]: Direksiyon PID kontrolcüsünü sıfırlar (integral ve türev birikimini siler).
                    pid.reset()
                    print("[main] PID reset")
                elif key == ord("o"):
                    # [AÇIKLAMA]: Sollama durum makinesini ve şerit kaydırmasını sıfırlar (yeniden kurar).
                    overtake.reset()
                    detector.set_lane_shift(0.0)
                    print("[main] sollama yeniden kuruldu (BEKLE)")
                elif key == ord("t"):
                    # [AÇIKLAMA]: Trafik ışığı, yaya geçidi ve park görev durum sayaçlarını sıfırlar.
                    gorevler.reset()
                    trafik.reset()
                elif key == ord("c"):
                    # [AÇIKLAMA]: MQTT renk ve start durumunu sıfırlar, motoru durdurur, yeni start bekler.
                    link.reset()
                    baslangic_renk = None
                    start_uygulandi = False
                    autonomous = False
                    motor.stop()
                    print("[main] otonom OFF, yeni renk+basla bekleniyor")
                elif key == ord("k"):
                    # [AÇIKLAMA]: Anlık kamera karesini, ikili maskeyi ve telemetriyi ~/Desktop/resim içine kaydeder.
                    shot_count += 1
                    save_shot(vis, res.mask, frame, shot_count)
                elif key in (ord("+"), ord("=")):
                    # [AÇIKLAMA]: Seyir gazını %5 artırır (+0.05).
                    throttle = min(1.0, throttle + 0.05)
                    print("[main] gaz: {:.2f} (PWM ~{:.0f})".format(
                        throttle, throttle * max_pwm))
                elif key in (ord("-"), ord("_")):
                    # [AÇIKLAMA]: Seyir gazını %5 azaltır (-0.05).
                    throttle = max(0.0, throttle - 0.05)
                    print("[main] gaz: {:.2f} (PWM ~{:.0f})".format(
                        throttle, throttle * max_pwm))
                elif ord("0") <= key <= ord("9"):
                    # [AÇIKLAMA]: Rakam tuşlarıyla doğrudan gaz belirler ('3' tuşu = 0.30 = %30 gaz).
                    throttle = (key - ord("0")) / 10.0
                    print("[main] gaz: {:.2f} (PWM ~{:.0f})".format(
                        throttle, throttle * max_pwm))
            else:
                if fps_frames == 0:
                    sys.stdout.write(
                        "\rfps={:.1f} dev={:+.3f} steer={:+.3f} auto={} PWM={:3d} | "
                        "uzak={} | trafik={} yaya={} park={}({})   "
                        .format(fps, res.deviation, steer,
                                "ON" if autonomous else "OFF", eff_pwm,
                                link.durum(), tr.state, gorev.state,
                                gorev.park_state, gorev.hedef_renk or "-"))
                    sys.stdout.flush()
    finally:
        print("\n[main] kapanýyor, motor durduruluyor...")
        try:
            motor.stop()
            motor.close()
        except Exception as e:
            print("[main] motor kapanýþ hatasý:", e)
        cam.stop()
        link.stop()
        if rec_csv is not None:
            try:
                rec_csv.close()
                np.save(os.path.join(rec_dir, "frames.npy"),
                        np.array(rec_raws))
                print("[main] KAYIT: {} kare -> {}".format(
                    len(rec_raws), rec_dir))
            except Exception as e:
                print("[main] kayýt kapanýþ hatasý:", e)
        if debug:
            cv2.destroyAllWindows()
        print("[main] bitti.")


if __name__ == "__main__":
    main()
