"""
Sollama görevi: turuncu kutuyu görünce sol şeritten sağ şeride geçer.

Kutu belirli mesafeye girince şerit ortası hedefi yatayda kaydırılır;
PID bu sapmayı kapatırken araç yan şeride geçer. Servo açısı hiçbir zaman
doğrudan zorlanmaz, manevra hızdan ve pil durumundan bağımsızdır.

Geçişin bittiği, ölçülen şerit ortasının tek karede bir şerit genişliği
sıçramasından anlaşılır.
"""
import time

from orange_detect_depth import detect_orange


class OvertakeResult(object):
    def __init__(self):
        self.state = "BEKLE"
        self.shift_px = 0.0
        self.throttle_scale = 1.0
        self.bbox = None
        self.dist_cm = None
        self.area = 0
        self.reason = ""


class OvertakeController(object):
    def __init__(self, ovt_cfg, lane_half_width_px=232.0):
        c = ovt_cfg or {}
        self.enabled = bool(c.get("enable", True))

        self.trigger_cm = float(c.get("trigger_distance_cm", 90.0))
        self.max_cm = float(c.get("max_distance_cm", 200.0))
        self.trigger_frames = int(c.get("trigger_frames", 3))

        self.shift_px = float(c.get("lane_shift_px",
                                    2.0 * float(lane_half_width_px)))
        self.ramp_in = float(c.get("shift_ramp_px", 40.0))
        self.ramp_out = float(c.get("release_ramp_px", 60.0))
        self.switch_jump_px = float(c.get("switch_jump_px",
                                          0.5 * self.shift_px))
        self.min_transition_s = float(c.get("min_transition_s", 0.4))
        self.max_transition_s = float(c.get("max_transition_s", 2.5))
        self.settle_s = float(c.get("settle_s", 0.6))
        self.throttle_scale = float(c.get("throttle_scale", 0.8))
        self.once = bool(c.get("once", True))

        self.state = "BEKLE"
        self._near_streak = 0
        self._shift = 0.0
        self._t0 = 0.0
        self._t_settle = 0.0
        self._prev_lc = None
        self._warned_no_depth = False
        self._no_depth_streak = 0
        self._instant_release = False

    def reset(self):
        self.state = "BEKLE"
        self._near_streak = 0
        self._shift = 0.0
        self._prev_lc = None

    def idle(self):
        self._shift = 0.0
        self._near_streak = 0
        self._prev_lc = None
        out = OvertakeResult()
        out.state = self.state
        return out

    def update(self, color, depth, depth_scale, res, now=None):
        out = OvertakeResult()
        if now is None:
            now = time.time()

        if not self.enabled:
            out.state = "KAPALI"
            return out
        if self.state == "BITTI":
            self._shift = 0.0
            out.state = "BITTI"
            return out

        if self.state == "BEKLE":
            if depth is None or not depth_scale:
                self._no_depth_streak += 1
                if not self._warned_no_depth and self._no_depth_streak >= 30:
                    print("[sollama] UYARI: 30 karedir depth yok - sollama "
                          "çalýþmaz. config camera.enable_depth: true mu?")
                    self._warned_no_depth = True
            else:
                self._no_depth_streak = 0
                try:
                    det = detect_orange(color, depth, depth_scale, strict=True)
                except Exception as e:
                    det = None
                    print("[sollama] detect_orange hatasý:", e)
                if det is not None:
                    bbox, dist_cm, area = det
                    if dist_cm is not None and dist_cm <= self.max_cm:
                        out.bbox = bbox
                        out.dist_cm = dist_cm
                        out.area = area

            yakin = (out.dist_cm is not None and out.dist_cm < self.trigger_cm)
            self._near_streak = (self._near_streak + 1) if yakin else 0
            if self._near_streak >= self.trigger_frames:
                self.state = "GECIS"
                self._t0 = now
                self._near_streak = 0
                self._prev_lc = res.lane_center_px
                out.reason = "kutu {:.0f} cm".format(out.dist_cm)
                print("[sollama] GECIS: kutu {:.0f} cm -> sag serite geciliyor "
                      "(ofset {:.0f} px)".format(out.dist_cm, self.shift_px))

        elif self.state == "GECIS":
            self._shift = min(self.shift_px, self._shift + self.ramp_in)

            elapsed = now - self._t0
            gecildi = False
            sicrama = False
            sebep = ""
            lc = res.lane_center_px
            taze = (lc is not None and res.found and not res.from_memory)
            if taze and self._prev_lc is not None:
                atlama = lc - self._prev_lc
                if atlama > self.switch_jump_px:
                    gecildi = True
                    sicrama = True
                    sebep = "serit cifti degisti (+{:.0f} px)".format(atlama)
            if taze:
                self._prev_lc = lc
            if not gecildi and elapsed >= self.max_transition_s:
                gecildi = True
                sebep = "max sure ({:.1f} sn)".format(self.max_transition_s)

            if gecildi and elapsed >= self.min_transition_s:
                self.state = "OTUR"
                self._t_settle = now
                out.reason = sebep
                self._instant_release = sicrama
                if self._instant_release:
                    self._shift = 0.0
                print("[sollama] OTUR: {} - ofset {}".format(
                    sebep, "aninda sifirlandi" if self._instant_release
                    else "rampayla birakiliyor"))

        elif self.state == "OTUR":
            self._shift = max(0.0, self._shift - self.ramp_out)
            if self._shift <= 0.0 and (now - self._t_settle) >= self.settle_s:
                self.state = "BITTI" if self.once else "BEKLE"
                self._prev_lc = None
                print("[sollama] TAMAM - sag seritte devam ({})".format(
                    self.state))

        out.state = self.state
        out.shift_px = self._shift
        if self.state in ("GECIS", "OTUR"):
            out.throttle_scale = self.throttle_scale
        return out
