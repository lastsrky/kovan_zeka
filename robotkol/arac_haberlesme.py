#!/usr/bin/env python3
"""
Araçla MQTT haberleşmesi: küpün rengini ve başla komutunu araca yollar.

Kol yayınlar, araç dinler. Broker (mosquitto) kol tarafında çalışır.

Konular:
    robot/veri    algılanan renk (RED / GREEN / BLUE)
    robot/basla   yükleme bitti, araç harekete geçsin
    arac/yuk      araca yüklenen küpün rengi
    robot/durum   serbest durum metni (log)
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, Optional

import paho.mqtt.client as mqtt

TOPIC_YUK   = "arac/yuk"
TOPIC_DURUM = "robot/durum"
TOPIC_RENK  = "robot/veri"
TOPIC_BASLA = "robot/basla"

VARSAYILAN_BROKER = "127.0.0.1"
VARSAYILAN_PORT   = 1883


class MqttIstemci:
    def __init__(self, broker: str = VARSAYILAN_BROKER,
                 port: int = VARSAYILAN_PORT, client_id: str = "robot_kol"):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=client_id, clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self._aboneler: Dict[str, Callable[[str, str], None]] = {}
        self._lock = threading.Lock()
        self.bagli = False
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)

    def baglan(self, timeout: float = 5.0) -> bool:
        try:
            self.client.connect(self.broker, self.port, keepalive=30)
        except Exception as e:
            print(f"[mqtt] Baglanti hatasi: {e}")
            return False
        self.client.loop_start()
        import time
        t0 = time.time()
        while not self.bagli and (time.time() - t0) < timeout:
            time.sleep(0.05)
        return self.bagli

    def kapat(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        self.bagli = False

    def yayinla(self, topic: str, payload: str,
                qos: int = 1, retain: bool = True) -> bool:
        try:
            info = self.client.publish(topic, payload, qos=qos, retain=retain)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[mqtt] Yayin hatasi: {e}")
            return False

    def yuk_gonder(self, renk: str) -> bool:
        return self.yayinla(TOPIC_YUK, renk, qos=1, retain=True)

    def renk_gonder(self, renk: str) -> bool:
        if renk not in ("RED", "GREEN", "BLUE"):
            return False
        import json, time
        payload = json.dumps({"renk": renk, "zaman": time.time()})
        return self.yayinla(TOPIC_RENK, payload, qos=1, retain=True)

    def basla_gonder(self) -> bool:
        import json, time
        payload = json.dumps({"komut": "BASLA", "zaman": time.time()})
        return self.yayinla(TOPIC_BASLA, payload, qos=1, retain=False)

    def durum_gonder(self, metin: str) -> bool:
        return self.yayinla(TOPIC_DURUM, metin, qos=0, retain=False)

    def dinle(self, topic: str, callback: Callable[[str, str], None]) -> None:
        with self._lock:
            self._aboneler[topic] = callback
        if self.bagli:
            self.client.subscribe(topic, qos=1)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.bagli = True
            print(f"[mqtt] Baglandi: {self.broker}:{self.port}")
            with self._lock:
                for t in self._aboneler:
                    client.subscribe(t, qos=1)
        else:
            self.bagli = False
            print(f"[mqtt] Baglanti reddedildi: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.bagli = False
        print(f"[mqtt] Baglanti kesildi (rc={reason_code}), yeniden denenecek...")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        with self._lock:
            cb = self._aboneler.get(msg.topic)
        if cb:
            try:
                cb(msg.topic, payload)
            except Exception as e:
                print(f"[mqtt] callback hatasi: {e}")


if __name__ == "__main__":
    import sys, time
    broker = sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN_BROKER
    m = MqttIstemci(broker=broker, client_id="test_kol")
    if not m.baglan():
        print("Broker'a baglanilamadi. Once mosquitto calismali:")
        print("  sudo systemctl start mosquitto   (KURULUM.md'ye bak)")
        sys.exit(1)

    alinan = {"v": None}
    m.dinle(TOPIC_YUK, lambda t, p: alinan.__setitem__("v", p))
    time.sleep(0.3)
    m.yuk_gonder("RED")
    time.sleep(0.5)
    print("Gonderilen: RED  | Alinan:", alinan["v"],
          "->", "OK" if alinan["v"] == "RED" else "HATA")
    m.kapat()
