"""
Şerit tespiti: kareden aracın şeridin ortasından ne kadar saptığını hesaplar.

Maske -> bağlantılı bileşenler -> aracı kuşatan iki çizgiye polinom ->
şerit ortası -> lookahead noktasında sapma. Çizgi kaybolursa son polinom
sınırlı sayıda kare boyunca kullanılır, sonra araç güvenli durur.

Ürettiği sapma main.py'de PID'e girer.
"""
import cv2
import numpy as np


class DetectionResult(object):
    def __init__(self):
        self.found = False
        self.from_memory = False
        self.deviation = 0.0
        self.deviation_px = 0.0
        self.poly = None
        self.target_point = None
        self.mask = None
        self.roi_y0 = 0
        self.roi_y1 = 0
        self.n_pixels = 0
        self.n_components = 0
        self.rejected = None
        self.poly_left = None
        self.poly_right = None
        self.rate_limited = False
        self.roi_poly = None
        self.raw_deviation = None
        self.slope_metric = 0.0
        self.left_missing = 0
        self.corner_turn = 0.0
        self.left_ending = False
        self.lane_center_px = None
        self.lane_shift_px = 0.0
        self.left_ref_x = None
        self.right_ref_x = None


class LineDetector(object):
    def __init__(self, vision_cfg):
        self.cfg = vision_cfg
        self._last_poly = None
        self._memory_count = 0
        self.memory_frames = int(vision_cfg.get("memory_frames", 10))
        self._last_lr = None
        self._side_lock = None
        self._last_single_x = None
        self._last_dev = None
        self._learned_offset = {}
        self._corner_count = 0
        self._cornering = None
        self._corner_hold = 0
        self._corner_exit_count = 0
        self._slope_streak = 0
        self._slope_sign = 0
        self._slope_smooth = None
        self._left_missing = 0
        self._corner_turn_active = False
        self._corner_turn_frames = 0
        self._left_found_streak = 0
        self._left_ending_streak = 0
        self._lane_shift_px = 0.0

    def _get(self, key, default):
        return self.cfg.get(key, default)

    def set_lane_shift(self, px):
        self._lane_shift_px = float(px)

    def make_mask(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        blur_k = int(self._get("blur_ksize", 5))
        if blur_k and blur_k >= 3:
            if blur_k % 2 == 0:
                blur_k += 1
            gray = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

        mode = self._get("threshold_mode", "adaptive")
        if mode == "binary":
            thr = int(self._get("binary_thresh", 180))
            _, mask = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)
        else:
            block = int(self._get("adaptive_block_size", 51))
            if block % 2 == 0:
                block += 1
            if block < 3:
                block = 3
            C = int(self._get("adaptive_C", -20))
            mask = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, block, C)

        kw = max(1, int(self._get("morph_kernel_w", 3)))
        kh = max(1, int(self._get("morph_kernel_h", 25)))
        iters = max(1, int(self._get("morph_iterations", 2)))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel,
                                iterations=iters)
        return mask

    def find_components(self, roi_mask):
        min_area = int(self._get("min_component_area", 300))
        min_h_ratio = float(self._get("min_line_height_ratio", 0.0))
        max_fill = float(self._get("max_component_fill", 1.0))

        n_labels, labels, stats, centroids = \
            cv2.connectedComponentsWithStats(roi_mask, connectivity=8)

        roi_h = roi_mask.shape[0]
        bottom_start = int(roi_h * 0.75)

        comps = []
        for i in range(1, n_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < min_area:
                continue
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])
            btop = int(stats[i, cv2.CC_STAT_TOP])
            bbot = btop + bh
            if min_h_ratio > 0.0 and bh < min_h_ratio * roi_h:
                continue
            if bool(self._get("require_roi_span", False)):
                tol = float(self._get("span_tolerance_ratio", 0.12)) * roi_h
                if btop > tol or bbot < (roi_h - tol):
                    continue
            if max_fill < 1.0 and bw > 0 and bh > 0:
                if float(area) / float(bw * bh) > max_fill:
                    continue
            max_rw = float(self._get("max_row_width_px", 0.0))
            if max_rw > 0.0 and bh > 0 and (float(area) / float(bh)) > max_rw:
                continue
            ys, xs = np.where(labels == i)
            bmask = ys >= bottom_start
            if np.any(bmask):
                ref_x = float(np.mean(xs[bmask]))
            else:
                ref_x = float(centroids[i][0])
            comps.append({"ys": ys, "xs": xs, "area": area, "ref_x": ref_x})
        return comps

    def _fit_component(self, comp, y0, y_bottom):
        xs = comp["xs"]
        if xs.shape[0] < 3:
            return None
        ys_full = comp["ys"].astype(np.float64) + y0
        degree = int(self._get("poly_degree", 2))
        try:
            poly = np.polyfit(ys_full, xs.astype(np.float64), degree)
        except Exception:
            return None
        if bool(self._get("reject_folded_fit", True)):
            if self._is_folded(poly, y0, y_bottom):
                return None
        return poly

    def select_line_pixels(self, roi_mask, img_center_x):
        comps = self.find_components(roi_mask)
        if not comps:
            return None, None, 0
        mode = self._get("line_select_mode", "center")

        def score(c):
            if mode == "left":
                return c["ref_x"]
            elif mode == "right":
                return -c["ref_x"]
            elif mode == "largest":
                return -c["area"]
            return abs(c["ref_x"] - img_center_x)

        best = min(comps, key=score)
        return best["ys"], best["xs"], len(comps)

    def _is_folded(self, poly, y_top, y_bottom):
        if poly is None or len(poly) < 3:
            return False
        a = float(poly[0])
        b = float(poly[1])
        if abs(a) < 1e-9:
            return False
        vertex_y = -b / (2.0 * a)
        if not (y_top < vertex_y < y_bottom):
            return False

        x_v = float(np.polyval(poly, vertex_y))
        x_t = float(np.polyval(poly, y_top))
        x_b = float(np.polyval(poly, y_bottom))
        backtrack = min(abs(x_t - x_v), abs(x_b - x_v))
        max_bt = float(self._get("max_fold_backtrack_px", 20.0))
        return backtrack > max_bt

    def process(self, frame_bgr):
        res = DetectionResult()
        h, w = frame_bgr.shape[:2]
        img_center_x = w / 2.0 + float(self._get("image_center_offset_px", 0.0))

        mask_full = self.make_mask(frame_bgr)
        res.mask = mask_full

        top_r = min(max(float(self._get("roi_top_ratio", 0.5)), 0.0), 0.95)
        bot_r = min(max(float(self._get("roi_bottom_ratio", 1.0)), 0.05), 1.0)
        if bot_r <= top_r:
            bot_r = 1.0
        y0 = int(h * top_r)
        y1 = int(h * bot_r)
        if y1 - y0 < 8:
            y1 = min(h, y0 + 8)
        res.roi_y0 = y0
        res.roi_y1 = y1
        roi_mask = mask_full[y0:y1, :]

        if bool(self._get("roi_trapezoid", False)):
            roi_mask = roi_mask.copy()
            rh, rw = roi_mask.shape[:2]
            tw = float(self._get("roi_top_width_ratio", 0.5)) * rw
            bw = float(self._get("roi_bottom_width_ratio", 1.0)) * rw
            cxr = rw * float(self._get("roi_center_ratio", 0.5))
            poly = np.array([[
                (int(cxr - tw / 2.0), 0), (int(cxr + tw / 2.0), 0),
                (int(cxr + bw / 2.0), rh), (int(cxr - bw / 2.0), rh)]],
                dtype=np.int32)
            keep = np.zeros((rh, rw), np.uint8)
            cv2.fillPoly(keep, poly, 255)
            roi_mask = cv2.bitwise_and(roi_mask, keep)
            res.roi_poly = poly[0]

        if self._get("line_select_mode", "center") == "lane_center" and \
                bool(self._get("select_single_line", True)):
            return self._process_lane_center(res, roi_mask, y0, y1,
                                             img_center_x)

        if bool(self._get("select_single_line", True)):
            ys, xs, n_comp = self.select_line_pixels(roi_mask, img_center_x)
            res.n_components = n_comp
            if ys is None:
                ys = np.array([], dtype=np.int64)
                xs = np.array([], dtype=np.int64)
        else:
            ys, xs = np.where(roi_mask > 0)
            res.n_components = 1

        n = int(xs.shape[0])
        res.n_pixels = n
        min_pixels = int(self._get("min_pixels", 400))

        poly = None
        if n >= min_pixels:
            ys_full = ys.astype(np.float64) + y0
            xs_f = xs.astype(np.float64)
            degree = int(self._get("poly_degree", 2))
            try:
                poly = np.polyfit(ys_full, xs_f, degree)
            except Exception:
                poly = None
            if poly is not None and bool(self._get("reject_folded_fit", True)):
                if self._is_folded(poly, y0, y1):
                    res.rejected = "folded"
                    poly = None
        elif n > 0:
            res.rejected = "few_pixels"

        return self._finalize(res, poly, y0, y1, img_center_x)

    def _process_lane_center(self, res, roi_mask, y0, y1, img_center_x):
        comps = self.find_components(roi_mask)
        res.n_components = len(comps)

        corner_enable = bool(self._get("corner_enable", True))
        if not corner_enable:
            self._cornering = None
            self._corner_hold = 0
            self._corner_exit_count = 0
            self._slope_streak = 0

        roi_w = roi_mask.shape[1]
        dom_slope = self._dominant_slope(comps)

        if dom_slope is not None:
            ham = min(abs(dom_slope), 3.0)
        elif self._slope_smooth is not None:
            ham = self._slope_smooth
        else:
            ham = 0.0
        if self._slope_smooth is None:
            self._slope_smooth = ham
        else:
            self._slope_smooth = 0.3 * ham + 0.7 * self._slope_smooth
        res.slope_metric = self._slope_smooth

        slope_thr = float(self._get("corner_slope_threshold", 1.0))
        exit_slope = float(self._get("corner_exit_slope", 0.4))

        fixed = self._get("corner_fixed_direction", "left")
        if dom_slope is not None and abs(dom_slope) >= slope_thr:
            self._slope_streak += 1
            self._slope_sign = 1 if dom_slope > 0 else -1
        else:
            self._slope_streak = 0

        trig = int(self._get("corner_trigger_frames", 3))
        if corner_enable and self._cornering is None and \
                self._slope_streak >= trig:
            if fixed == "left":
                self._cornering = -1.0
            elif fixed == "right":
                self._cornering = 1.0
            else:
                self._cornering = -1.0 if self._slope_sign > 0 else 1.0
            self._corner_hold = 0
            self._corner_exit_count = 0
            strength = float(self._get("horizontal_turn", 0.9))
            return self._emit_corner(res, self._cornering, strength,
                                     img_center_x, "corner_horizontal")

        if self._cornering is not None:
            self._corner_hold += 1
            exit_frac = float(self._get("corner_exit_center_frac", 0.25))
            straight = False
            if dom_slope is not None and abs(dom_slope) < slope_thr and \
                    len(comps) >= 2:
                xs_sorted = sorted(c["ref_x"] for c in comps)
                mid = (xs_sorted[0] + xs_sorted[-1]) / 2.0
                if abs(mid - img_center_x) < exit_frac * img_center_x:
                    straight = True
            if straight:
                self._corner_exit_count += 1
            else:
                self._corner_exit_count = 0

            need = int(self._get("corner_exit_frames", 3))
            backstop = int(self._get("corner_max_hold", 150))
            if self._corner_exit_count >= need or \
                    self._corner_hold >= backstop:
                self._cornering = None
                self._corner_hold = 0
                self._corner_exit_count = 0
            else:
                strength = float(self._get("horizontal_turn", 0.9))
                return self._emit_corner(res, self._cornering, strength,
                                         img_center_x, "corner_hold")

        comps.sort(key=lambda c: c["ref_x"])

        jump = float(self._get("max_line_jump_px", 0.0))
        if jump > 0.0 and self._last_lr is not None:
            lx, rx = self._last_lr
            keep = []
            for c in comps:
                near_l = (lx is not None and abs(c["ref_x"] - lx) <= jump)
                near_r = (rx is not None and abs(c["ref_x"] - rx) <= jump)
                if near_l or near_r:
                    keep.append(c)
            if len(keep) >= 2:
                comps = keep

        left = None
        right = None
        if len(comps) >= 2:
            pair = None
            for i in range(len(comps) - 1):
                if comps[i]["ref_x"] <= img_center_x <= comps[i + 1]["ref_x"]:
                    pair = (comps[i], comps[i + 1])
                    break
            if pair is None:
                if img_center_x < comps[0]["ref_x"]:
                    pair = (comps[0], comps[1])
                else:
                    pair = (comps[-2], comps[-1])
            left, right = pair
        elif len(comps) == 1:
            c0 = comps[0]
            side = None
            if self._side_lock is not None and self._last_single_x is not None:
                lim = float(self._get("max_line_jump_px", 120)) or 120.0
                if abs(c0["ref_x"] - self._last_single_x) <= lim:
                    side = self._side_lock
            if side is None:
                side = "left" if c0["ref_x"] < img_center_x else "right"
            if side == "left":
                left = c0
            else:
                right = c0
            self._side_lock = side
            self._last_single_x = c0["ref_x"]
        if left is not None and right is not None:
            self._side_lock = None
            self._last_single_x = None

        self._last_lr = (left["ref_x"] if left else None,
                         right["ref_x"] if right else None)
        res.left_ref_x, res.right_ref_x = self._last_lr

        poly_l = self._fit_component(left, y0, y1) if left else None
        poly_r = self._fit_component(right, y0, y1) if right else None
        res.poly_left = poly_l
        res.poly_right = poly_r

        if poly_l is not None:
            self._left_missing = 0
        else:
            self._left_missing += 1
        res.left_missing = self._left_missing

        roi_h_le = max(1, y1 - y0)
        ending = False
        if left is not None and left["ys"].shape[0] > 0:
            top_ratio = float(left["ys"].min()) / float(roi_h_le)
            ending = top_ratio > 0.20
        if ending:
            self._left_ending_streak += 1
        else:
            self._left_ending_streak = 0
        res.left_ending = self._left_ending_streak >= 3

        self._update_corner_turn(res)

        half_w = float(self._get("lane_half_width_px", 160))

        look_ratio = min(max(float(self._get("lookahead_ratio", 0.35)),
                             0.0), 1.0)
        ty = y0 + look_ratio * (y1 - y0)

        def _offset_poly(base_poly, signed_offset):
            p = np.asarray(base_poly, dtype=np.float64).copy()
            p[-1] += signed_offset
            return p

        def _direct_dev(sp):
            return (float(np.polyval(sp, ty)) - img_center_x) / img_center_x

        poly = None
        corner = False
        if poly_l is not None and poly_r is not None:
            poly = (np.asarray(poly_l) + np.asarray(poly_r)) / 2.0
            res.n_pixels = int(left["xs"].shape[0] + right["xs"].shape[0])
            self._corner_count = 0
            cx = float(np.polyval(poly, ty))
            a = float(self._get("offset_learn_rate", 0.2))
            for side, sp in (("left", poly_l), ("right", poly_r)):
                d = cx - float(np.polyval(sp, ty))
                prev = self._learned_offset.get(side)
                self._learned_offset[side] = d if prev is None \
                    else (1.0 - a) * prev + a * d
        elif poly_l is not None or poly_r is not None:
            single = poly_l if poly_l is not None else poly_r
            side = "left" if poly_l is not None else "right"
            direct = _direct_dev(single)

            corner = self._get("corner_direct_enable", False)
            if corner:
                cthr = float(self._get("corner_direct_threshold", 0.6))
                cframes = int(self._get("corner_frames", 3))
                if abs(direct) >= cthr:
                    self._corner_count += 1
                else:
                    self._corner_count = 0
                corner = self._corner_count >= cframes

            if corner:
                poly = np.asarray(single, dtype=np.float64)
                res.rejected = "corner_" + side
            else:
                off = self._learned_offset.get(side)
                if off is None:
                    off = half_w if side == "left" else -half_w
                    res.rejected = "only_" + side
                else:
                    res.rejected = "only_%s*" % side
                poly = _offset_poly(single, off)
            res.n_pixels = int((left if side == "left" else right)
                               ["xs"].shape[0])

        if poly is not None and res.n_pixels < int(self._get("min_pixels", 400)):
            poly = None
            res.rejected = "few_pixels"

        return self._finalize(res, poly, y0, y1, img_center_x)

    def _dominant_slope(self, comps):
        if not comps:
            return None
        big = max(comps, key=lambda c: c["xs"].shape[0])
        ys = big["ys"].astype(np.float64)
        xs = big["xs"].astype(np.float64)
        if xs.shape[0] < 10 or (ys.max() - ys.min()) < 5:
            return None
        try:
            return float(np.polyfit(ys, xs, 1)[0])
        except Exception:
            return None

    def _update_corner_turn(self, res):
        if res.left_missing == 0:
            self._left_found_streak += 1
        else:
            self._left_found_streak = 0

        lm_trig = int(self._get("corner_lm_trigger", 3))
        slope_min = float(self._get("corner_slope_min", 0.5))
        exit_found = int(self._get("corner_exit_found", 3))
        max_frames = int(self._get("corner_max_frames", 60))

        if self._corner_turn_active:
            self._corner_turn_frames += 1
            if self._left_found_streak >= exit_found or \
                    self._corner_turn_frames >= max_frames:
                self._corner_turn_active = False
                self._corner_turn_frames = 0
                self._last_dev = None
        else:
            if res.left_missing >= lm_trig and \
                    res.slope_metric >= slope_min:
                self._corner_turn_active = True
                self._corner_turn_frames = 0

        res.corner_turn = -1.0 if self._corner_turn_active else 0.0

    def _emit_corner(self, res, sgn, strength, img_center_x, tag):
        res.rejected = tag
        res.deviation = sgn * strength
        res.deviation_px = res.deviation * img_center_x
        res.found = True
        res.from_memory = False
        res.poly = None
        self._last_poly = None
        self._memory_count = 0
        self._corner_count = 0
        self._apply_dev_filters(res)
        return res

    def _finalize(self, res, poly, y0, y1, img_center_x):
        if poly is not None:
            self._last_poly = poly
            self._memory_count = 0
            res.found = True
            res.from_memory = False
            res.poly = poly
        elif self._last_poly is not None and \
                self._memory_count < self.memory_frames:
            self._memory_count += 1
            res.found = True
            res.from_memory = True
            res.poly = self._last_poly
        else:
            self._last_poly = None
            res.found = False
            res.poly = None
            res.deviation = 0.0
            return res

        look_ratio = float(self._get("lookahead_ratio", 0.35))
        look_ratio = min(max(look_ratio, 0.0), 1.0)
        target_y = y0 + look_ratio * (y1 - y0)
        line_x = float(np.polyval(res.poly, target_y))

        res.lane_center_px = line_x

        res.lane_shift_px = self._lane_shift_px
        if self._lane_shift_px != 0.0:
            line_x += self._lane_shift_px

        res.target_point = (int(round(line_x)), int(round(target_y)))
        res.deviation_px = line_x - img_center_x
        res.deviation = float(res.deviation_px / img_center_x)
        res.deviation = min(max(res.deviation, -1.5), 1.5)

        self._apply_dev_filters(res)
        return res

    def _apply_dev_filters(self, res):
        alpha = float(self._get("deviation_smoothing", 1.0))
        if 0.0 < alpha < 1.0 and self._last_dev is not None:
            res.raw_deviation = res.deviation
            res.deviation = alpha * res.deviation + (1.0 - alpha) * self._last_dev

        max_step = float(self._get("max_deviation_step", 0.0))
        if max_step > 0.0 and self._last_dev is not None:
            delta = res.deviation - self._last_dev
            if abs(delta) > max_step:
                limited = self._last_dev + (max_step if delta > 0
                                            else -max_step)
                res.rate_limited = True
                res.raw_deviation = res.deviation
                res.deviation = limited
        self._last_dev = res.deviation
        return res

    def reset_memory(self):
        self._last_poly = None
        self._memory_count = 0
        self._last_lr = None
        self._side_lock = None
        self._last_single_x = None
        self._last_dev = None
        self._slope_smooth = None
        self._left_missing = 0
        self._corner_turn_active = False
        self._corner_turn_frames = 0
        self._left_found_streak = 0
        self._left_ending_streak = 0


def draw_debug(frame_bgr, res, extra_lines=None):
    vis = frame_bgr.copy()
    h, w = vis.shape[:2]
    cx = w // 2

    cv2.line(vis, (0, res.roi_y0), (w, res.roi_y0), (60, 60, 60), 1)

    if res.roi_poly is not None:
        p = res.roi_poly.copy()
        p[:, 1] = p[:, 1] + res.roi_y0
        cv2.polylines(vis, [p], True, (0, 200, 200), 1)
    cv2.line(vis, (0, res.roi_y1), (w, res.roi_y1), (60, 60, 60), 1)

    cv2.line(vis, (cx, res.roi_y0), (cx, res.roi_y1), (120, 120, 120), 1)

    for side_poly in (res.poly_left, res.poly_right):
        if side_poly is None:
            continue
        spts = []
        for y in range(res.roi_y0, res.roi_y1, 6):
            x = int(round(float(np.polyval(side_poly, y))))
            if 0 <= x < w:
                spts.append((x, y))
        for i in range(1, len(spts)):
            cv2.line(vis, spts[i - 1], spts[i], (255, 160, 0), 1)

    if res.poly is not None:
        pts = []
        for y in range(res.roi_y0, res.roi_y1, 4):
            x = int(round(float(np.polyval(res.poly, y))))
            if 0 <= x < w:
                pts.append((x, y))
        if len(pts) >= 2:
            color = (0, 165, 255) if res.from_memory else (0, 255, 0)
            for i in range(1, len(pts)):
                cv2.line(vis, pts[i - 1], pts[i], color, 2)

    if res.target_point is not None:
        tx, ty = res.target_point
        cv2.circle(vis, (tx, ty), 6, (0, 0, 255), -1)
        cv2.line(vis, (cx, ty), (tx, ty), (0, 0, 255), 2)

    status = "MEMORY" if res.from_memory else ("OK" if res.found else "LOST")
    scolor = (0, 165, 255) if res.from_memory else \
             ((0, 255, 0) if res.found else (0, 0, 255))
    lines = [
        "status: {}".format(status),
        "deviation: {:+.3f}".format(res.deviation),
        "pixels: {}  lines: {}".format(res.n_pixels, res.n_components),
    ]
    if res.rejected:
        lines.append("REJECTED: {}".format(res.rejected))
    if extra_lines:
        lines.extend(extra_lines)
    y = 22
    for txt in lines:
        cv2.putText(vis, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    scolor, 1, cv2.LINE_AA)
        y += 24
    return vis
