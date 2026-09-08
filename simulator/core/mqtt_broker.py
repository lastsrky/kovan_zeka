"""
TEKNOFEST 2026 Akıllı Fabrika SITL Digital Twin Simulator
Lightweight Embedded MQTT Message Broker & Client Bridge

Protocol Topics & Contracts:
- arac/yuk: Official competition topic declaring payload color (RED/GREEN/BLUE)
- robot/basla: Vehicle dispatch command (BASLA)
- robot/veri: Detailed JSON payload {"renk": ..., "zaman": ...}
- robot/durum: Diagnostic and telemetry log messages

Features:
- In-process zero-dependency subscriber dispatch
- Standard MQTT topic wildcard matching (+ and #)
- Thread-safe non-blocking publish/subscribe operations
- Message history tracking with timestamps for forensic audit
- Drop-in client bridge compatibility for MqttIstemci
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

TOPIC_ARAC_YUK: str = "arac/yuk"
TOPIC_ROBOT_BASLA: str = "robot/basla"
TOPIC_ROBOT_VERI: str = "robot/veri"
TOPIC_ROBOT_DURUM: str = "robot/durum"

VALID_COLORS = ("RED", "GREEN", "BLUE")


def _topic_matches_filter(filter_pattern: str, topic: str) -> bool:
    """Matches MQTT topics against patterns including single (+) and multi-level (#) wildcards."""
    if filter_pattern == "#":
        return True
    if filter_pattern == topic:
        return True

    # Convert MQTT wildcards to regex pattern
    p = filter_pattern.replace("/", r"\/")
    p = p.replace("+", r"[^\/]+")
    p = p.replace("#", r".*")
    pattern = f"^{p}$"
    return bool(re.match(pattern, topic))


class MQTTBroker:
    """
    Lightweight Embedded In-Memory MQTT Broker and Message Dispatcher.
    Provides fast, thread-safe, and zero-dependency inter-agent communication
    between the Robot Arm cell, S7-1200 PLC, HMI panel, and Autonomous Vehicle.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 1883):
        self.host: str = host
        self.port: int = port
        self.subscribers: Dict[str, List[Callable[[str, str], Any]]] = {}
        self.messages: List[Tuple[str, str, float]] = []
        self._retained_messages: Dict[str, str] = {}
        self._lock: threading.RLock = threading.RLock()
        self.is_connected: bool = True

    def subscribe(self, topic: str, callback: Callable[[str, str], Any]) -> None:
        """
        Subscribes a callback to a given topic or wildcard pattern.
        Callback signature: callback(topic: str, payload: str) -> None
        """
        with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            if callback not in self.subscribers[topic]:
                self.subscribers[topic].append(callback)

            # Deliver retained message if topic matches
            for ret_top, ret_pay in self._retained_messages.items():
                if _topic_matches_filter(topic, ret_top):
                    try:
                        callback(ret_top, ret_pay)
                    except Exception as e:
                        print(f"[MQTTBroker] Retained delivery error on {ret_top}: {e}")

    def unsubscribe(self, topic: str, callback: Optional[Callable[[str, str], Any]] = None) -> None:
        """Unsubscribes callback from topic."""
        with self._lock:
            if topic in self.subscribers:
                if callback is not None:
                    if callback in self.subscribers[topic]:
                        self.subscribers[topic].remove(callback)
                else:
                    self.subscribers[topic].clear()

    def publish(
        self,
        topic: str,
        payload: Union[str, bytes, Dict[str, Any]],
        qos: int = 1,
        retain: bool = False,
    ) -> bool:
        """
        Publishes a message to all matching subscribers and records history.
        """
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        now = time.time()
        callbacks_to_invoke: List[Callable[[str, str], Any]] = []

        with self._lock:
            self.messages.append((topic, payload_str, now))

            if retain:
                self._retained_messages[topic] = payload_str

            # Find matching subscriber callbacks
            for sub_topic, cbs in self.subscribers.items():
                if _topic_matches_filter(sub_topic, topic):
                    callbacks_to_invoke.extend(cbs)

        # Dispatch callbacks outside lock to prevent deadlocks
        for cb in callbacks_to_invoke:
            try:
                cb(topic, payload_str)
            except Exception as e:
                print(f"[MQTTBroker] Callback error on {topic}: {e}")

        return True

    def get_last_message(self, topic: str) -> Optional[str]:
        """Returns the most recent payload published to topic."""
        with self._lock:
            for t, p, _ in reversed(self.messages):
                if t == topic:
                    return p
        return None

    def get_messages_for_topic(self, topic: str) -> List[Tuple[str, str, float]]:
        """Returns all historical messages published to topic."""
        with self._lock:
            return [m for m in self.messages if m[0] == topic]

    def clear_messages(self) -> None:
        """Clears message log history and retained messages."""
        with self._lock:
            self.messages.clear()
            self._retained_messages.clear()

    def clear(self) -> None:
        """Alias for clear_messages()."""
        self.clear_messages()

    # =========================================================================
    # Compatibility Helper Methods (Drop-in for MqttIstemci)
    # =========================================================================

    def yayinla(
        self,
        topic: str,
        payload: str,
        qos: int = 1,
        retain: bool = False,
    ) -> bool:
        """Turkish alias for publish()."""
        return self.publish(topic, payload, qos=qos, retain=retain)

    def dinle(self, topic: str, callback: Callable[[str, str], Any]) -> None:
        """Turkish alias for subscribe()."""
        self.subscribe(topic, callback)

    def yuk_gonder(self, renk: str) -> bool:
        """Publishes loaded cube color to competition topic arac/yuk."""
        if renk not in VALID_COLORS:
            return False
        return self.publish(TOPIC_ARAC_YUK, renk, qos=1, retain=True)

    def renk_gonder(self, renk: str) -> bool:
        """Publishes detailed color JSON payload to topic robot/veri."""
        if renk not in VALID_COLORS:
            return False
        payload = json.dumps({"renk": renk, "zaman": time.time()})
        return self.publish(TOPIC_ROBOT_VERI, payload, qos=1, retain=True)

    def basla_gonder(self) -> bool:
        """Publishes departure start trigger to topic robot/basla."""
        payload = json.dumps({"komut": "BASLA", "zaman": time.time()})
        # Publish JSON format first, then raw "BASLA" so last message is BASLA
        ok1 = self.publish(TOPIC_ROBOT_BASLA, payload, qos=1, retain=False)
        ok2 = self.publish(TOPIC_ROBOT_BASLA, "BASLA", qos=1, retain=False)
        return ok1 and ok2

    def durum_gonder(self, metin: str) -> bool:
        """Publishes status telemetry to topic robot/durum."""
        return self.publish(TOPIC_ROBOT_DURUM, metin, qos=0, retain=False)
