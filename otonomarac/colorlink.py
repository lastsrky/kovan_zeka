"""
Diğer Jetson'dan MQTT ile RENK ve BASLA komutlarını alır.

Bu cihaz yalnızca abone olur, hiçbir şey yayınlamaz.
RENK (RED/GREEN/BLUE) aracın hangi park alanına gireceğini belirler,
BASLA aracın harekete geçmesini sağlar. İkisi de gelmeden araç kıpırdamaz.

Bağlantı arka planda kurulur, ana döngü asla bloklanmaz.
"""
import json
import threading
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


GECERLI_RENKLER = ("RED", "GREEN", "BLUE")

RENK_TAKMA_AD = {
    "KIRMIZI": "RED",
    "YESIL": "GREEN",
    "YEÞIL": "GREEN",
    "MAVI": "BLUE",
}

BASLA_KELIMELERI = ("BASLA", "BAÞLA", "START", "GO", "BEGIN", "BASLAT")

BASLA_ANAHTARLARI = ("start", "basla", "baslat", "baþla", "go")

ARANAN_ANAHTARLAR = ("renk", "color", "komut", "command", "cmd", "durum",
                     "status", "state", "start", "basla", "baslat", "go")


def renk_normalize(deger):
    if deger is None or isinstance(deger, bool):
        return None
    s = str(deger).strip().upper()
    if not s:
        return None
    s = RENK_TAKMA_AD.get(s, s)
    return s if s in GECERLI_RENKLER else None


def basla_mi(deger):
    if deger is None or isinstance(deger, bool):
        return False
    s = str(deger).strip().upper()
    return s in BASLA_KELIMELERI


class ColorLink(object):
    def __init__(self, cfg=None):
        c = cfg or {}
        self.enabled = bool(c.get("enable", True))
        self.broker = str(c.get("broker", "10.50.58.21"))
        self.port = int(c.get("port", 1883))
        self.topic = str(c.get("topic", "robot/veri"))
        self.extra_topics = list(c.get("extra_topics", []) or [])
        self.field = str(c.get("field", "renk"))
        self.client_id = str(c.get("client_id", "araba-main"))
        self.keepalive = int(c.get("keepalive", 60))
        self.require_for_start = bool(c.get("require_for_start", True))
        self.auto_start = bool(c.get("auto_start", True))
        self.ignore_retained = bool(c.get("ignore_retained", True))
        self.verbose = bool(c.get("verbose", True))

        self._anahtarlar = tuple(
            [self.field] + [a for a in ARANAN_ANAHTARLAR if a != self.field])

        self._lock = threading.Lock()
        self._renk = None
        self._renk_t = 0.0
        self._son_mesaj_t = 0.0
        self._son_renk = None
        self._basla = False
        self._basla_t = 0.0
        self._connected = False
        self._msg_sayaci = 0
        self._bilinmeyen = 0
        self._client = None
        self._started = False

    def start(self):
        if not self.enabled:
            print("[link] KAPALI - uzaktan renk/basla dinlenmiyor")
            return False
        if mqtt is None:
            print("[link] UYARI: paho-mqtt yok -> uzaktan start devre dýþý. "
                  "Kurulum: pip3 install paho-mqtt")
            return False

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id=self.client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        try:
            self._client.connect_async(self.broker, self.port,
                                       keepalive=self.keepalive)
            self._client.loop_start()
        except Exception as e:
            print("[link] baþlatma hatasý:", e)
            return False
        self._started = True
        konular = ", ".join([self.topic] + self.extra_topics)
        print("[link] dinleniyor: {}:{} konu '{}' (arka planda)".format(
            self.broker, self.port, konular))
        return True

    def stop(self):
        if self._client is None or not self._started:
            return
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
        self._started = False

    def _on_connect(self, client, userdata, flags, reason_code,
                    properties=None):
        if reason_code == 0:
            with self._lock:
                self._connected = True
            for t in [self.topic] + self.extra_topics:
                client.subscribe(t, qos=1)
            print("[link] broker baðlandý -> abone: {}".format(
                ", ".join([self.topic] + self.extra_topics)))
        else:
            print("[link] baðlantý reddedildi, rc =", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code=None,
                       properties=None):
        with self._lock:
            self._connected = False
        print("[link] baðlantý koptu (otomatik yeniden denenecek)")

    def _on_message(self, client, userdata, msg):
        try:
            self._mesaj_isle(msg)
        except Exception as e:
            print("[link] mesaj iþleme hatasý (yok sayýldý):", e)

    def _mesaj_isle(self, msg):
        if self.ignore_retained and getattr(msg, "retain", False):
            print("[link] ESKÝ (retained) mesaj atlandý [konu: {}]: {}".format(
                getattr(msg, "topic", "?"), msg.payload[:60]))
            return

        sonuc = self._payload_coz(msg.payload)
        if sonuc is None:
            self._bilinmeyen += 1
            if self._bilinmeyen <= 5 or self._bilinmeyen % 50 == 0:
                try:
                    ham = msg.payload.decode("utf-8", "replace")[:120]
                except Exception:
                    ham = repr(msg.payload[:60])
                print("[link] TANINMAYAN payload (#{}) [konu: {}]: {}".format(
                    self._bilinmeyen, getattr(msg, "topic", "?"), ham))
            return

        tip, deger = sonuc
        simdi = time.time()
        olay = None
        konu = getattr(msg, "topic", "?")
        with self._lock:
            self._msg_sayaci += 1
            self._son_mesaj_t = simdi
            if tip == "RENK":
                self._son_renk = deger
                if self._renk is None:
                    self._renk = deger
                    self._renk_t = simdi
                    olay = ("RENK", deger)
            else:
                if not self._basla:
                    self._basla = True
                    self._basla_t = simdi
                    olay = ("BASLA", self._renk)

        if self.verbose:
            with self._lock:
                n = self._msg_sayaci
            print("[link] #{:d} [{}] {}".format(
                n, konu,
                "RENK {}".format(deger) if tip == "RENK" else "BASLA"))

        if olay is None:
            return
        if olay[0] == "RENK":
            print("=" * 56)
            print(" RENK ALINDI: {}   (basla bekleniyor)  [konu: {}]".format(
                olay[1], konu))
            print("=" * 56)
        else:
            print("=" * 56)
            if olay[1] is None:
                print(" BASLA ALINDI [konu: {}] - ama RENK GELMEDÝ, "
                      "araç HAREKET ETMEZ".format(konu))
                print(" (renk gelince start geçerli olacak)")
            else:
                print(" BASLA ALINDI [konu: {}] - renk {} -> ARAÇ HAREKETE "
                      "GEÇÝYOR".format(konu, olay[1]))
            print("=" * 56)

    def _payload_coz(self, payload):
        try:
            metin = payload.decode("utf-8", "replace").strip()
        except Exception:
            return None
        if not metin:
            return None
        try:
            veri = json.loads(metin)
        except ValueError:
            return self._deger_coz(metin)
        if isinstance(veri, dict):
            for anahtar in self._anahtarlar:
                if anahtar in veri:
                    s = self._deger_coz(veri[anahtar], anahtar)
                    if s is not None:
                        return s
            return None
        return self._deger_coz(veri)

    def _deger_coz(self, deger, anahtar=None):
        ad = (anahtar or "").strip().lower()
        if isinstance(deger, bool) or isinstance(deger, (int, float)):
            if ad in BASLA_ANAHTARLARI and deger:
                return ("BASLA", None)
            return None
        r = renk_normalize(deger)
        if r is not None:
            return ("RENK", r)
        if basla_mi(deger):
            return ("BASLA", None)
        return None

    @property
    def renk(self):
        with self._lock:
            return self._renk

    @property
    def son_renk(self):
        with self._lock:
            return self._son_renk

    @property
    def basla(self):
        with self._lock:
            return self._basla

    @property
    def hazir(self):
        with self._lock:
            return (self._renk is not None) and self._basla

    @property
    def connected(self):
        with self._lock:
            return self._connected

    @property
    def mesaj_sayisi(self):
        with self._lock:
            return self._msg_sayaci

    def reset(self):
        with self._lock:
            self._renk = None
            self._renk_t = 0.0
            self._basla = False
            self._basla_t = 0.0
        print("[link] renk+basla sýfýrlandý, yeni tur bekleniyor")

    def bekle(self, timeout=None):
        t0 = time.time()
        while True:
            if self.hazir:
                return True
            if timeout is not None and (time.time() - t0) >= timeout:
                return False
            time.sleep(0.05)

    def durum(self):
        if not self.enabled:
            return "KAPALI"
        if mqtt is None:
            return "paho yok"
        with self._lock:
            bagli = self._connected
            renk = self._renk
            basla = self._basla
            n = self._msg_sayaci
            son_t = self._son_mesaj_t
        if n == 0:
            return "BAGLI, veri yok" if bagli else "BAGLANIYOR..."

        ek = " #{:d}".format(n)
        if son_t > 0.0:
            ek += " {:.0f}s".format(time.time() - son_t)
        if not bagli:
            ek += " KOPUK!"

        if renk is None:
            return ("BASLA(renk YOK)" if basla else "?") + ek
        if not basla:
            return "{} basla-bekle{}".format(renk, ek)
        return "{}+BASLA HAZIR{}".format(renk, ek)


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Diðer Jetson'dan gelen renk/basla mesajlarýný dinle")
    ap.add_argument("--broker", default=None, help="broker IP")
    ap.add_argument("--topic", default=None, help="MQTT konusu")
    args = ap.parse_args()

    cfg = {}
    try:
        from config_loader import load_config
        cfg = (load_config() or {}).get("colorlink", {}) or {}
    except Exception:
        pass
    if args.broker:
        cfg["broker"] = args.broker
    if args.topic:
        cfg["topic"] = args.topic
    cfg["enable"] = True
    cfg["client_id"] = str(cfg.get("client_id", "araba")) + "-dinleyici"

    link = ColorLink(cfg)
    if not link.start():
        return
    print("Dinleniyor... (Ctrl+C ile dur)")
    onceki = None
    try:
        while True:
            time.sleep(0.5)
            d = link.durum()
            if d != onceki:
                print("[link] durum: {}   (renk={} basla={} hazir={})".format(
                    d, link.renk, link.basla, link.hazir))
                onceki = d
    except KeyboardInterrupt:
        print("\nDurduruldu.")
    finally:
        link.stop()


if __name__ == "__main__":
    main()
