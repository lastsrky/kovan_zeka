"""
Park görevi için zemindeki renkli park alanını bulur.

Hedef rengin (RED / GREEN / BLUE) HSV bandıyla maske çıkarır, karenin üst
kısmını yok sayar (kırmızı tabela ve duvar yanlış pozitifi elenir) ve bbox
derinliği zemin aralığında olan en büyük alanı döndürür.

tabela_gorev.py bunu kullanır.
"""
import numpy as np
import cv2

PARK_RED_HSV_LOW1 = np.array([0, 50, 50])
PARK_RED_HSV_HIGH1 = np.array([10, 255, 255])
PARK_RED_HSV_LOW2 = np.array([170, 50, 50])
PARK_RED_HSV_HIGH2 = np.array([180, 255, 255])

PARK_RENK_BANTLARI = {
    "RED": [((0, 50, 50), (10, 255, 255)),
            ((170, 50, 50), (180, 255, 255))],
    "GREEN": [((35, 40, 40), (85, 255, 255))],
    "BLUE": [((100, 40, 40), (135, 255, 255))],
}
PARK_RENK_VARSAYILAN = "RED"


def renk_maskesi(hsv, renk):
    bantlar = PARK_RENK_BANTLARI[str(renk).strip().upper()]
    mask = None
    for lo, hi in bantlar:
        m = cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = m if mask is None else (mask | m)
    return mask

PARK_RED_AREA_MIN = 300
PARK_ROI_UST_KIRP = 0.45
PARK_ZEMIN_MIN_CM = 25.0
PARK_ZEMIN_MAX_CM = 350.0
PARK_RED_KERNEL = np.ones((5, 5), np.uint8)


def detect_park_floor(color_image, depth_image, depth_scale,
                      renk=PARK_RENK_VARSAYILAN,
                      ust_kirp=PARK_ROI_UST_KIRP,
                      area_min=PARK_RED_AREA_MIN,
                      zemin_min_cm=PARK_ZEMIN_MIN_CM,
                      zemin_max_cm=PARK_ZEMIN_MAX_CM,
                      return_mask=False):
    h, w = color_image.shape[:2]
    hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
    try:
        mask = renk_maskesi(hsv, renk)
    except KeyError:
        print("[park_zemin_renk] bilinmeyen renk '%s', %s kullaniliyor"
              % (renk, PARK_RENK_VARSAYILAN))
        mask = renk_maskesi(hsv, PARK_RENK_VARSAYILAN)
    if ust_kirp > 0:
        mask[:int(h * ust_kirp), :] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, PARK_RED_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, PARK_RED_KERNEL)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    res = None
    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours:
            area = int(cv2.contourArea(cnt))
            if area < area_min:
                break
            x, y, bw, bh = cv2.boundingRect(cnt)
            roi = depth_image[y:y+bh, x:x+bw].astype(np.float32)
            valid = roi[roi > 0]
            if valid.size == 0:
                continue
            dist_cm = float(np.median(valid)) * depth_scale * 100.0
            if zemin_min_cm <= dist_cm <= zemin_max_cm:
                res = ((x, y, bw, bh), dist_cm, area)
                break
    if return_mask:
        return res, mask
    return res


def main():
    import pyrealsense2 as rs
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    profile = pipeline.start(config)
    depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)
    print(f"[park_zemin_renk] depth_scale={depth_scale}")
    print(f"  ust_kirp={PARK_ROI_UST_KIRP} "
          f"zemin={PARK_ZEMIN_MIN_CM:.0f}-{PARK_ZEMIN_MAX_CM:.0f}cm "
          f"area>={PARK_RED_AREA_MIN}")
    print("  [r] KIRMIZI  [g] YESIL  [b] MAVI  [q] cikis")
    hedef = PARK_RENK_VARSAYILAN
    kutu_renk = {"RED": (0, 0, 255), "GREEN": (0, 200, 0), "BLUE": (255, 0, 0)}
    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()
            if not depth_frame or not color_frame:
                continue
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            res, mask = detect_park_floor(color_image, depth_image, depth_scale,
                                          renk=hedef, return_mask=True)
            vis = color_image.copy()
            col = kutu_renk.get(hedef, (0, 0, 255))
            kirp_y = int(vis.shape[0] * PARK_ROI_UST_KIRP)
            cv2.line(vis, (0, kirp_y), (vis.shape[1], kirp_y), (255, 255, 0), 1)
            cv2.putText(vis, f"hedef: {hedef}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
            cv2.putText(vis, f"hedef: {hedef}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
            if res is not None:
                (x, y, bw, bh), dist_cm, area = res
                cv2.rectangle(vis, (x, y), (x + bw, y + bh), col, 3)
                cv2.line(vis, (x + bw // 2, y), (x + bw // 2, y + bh), col, 2)
                cv2.putText(vis, f"{dist_cm:.1f} cm a={area}",
                            (x, max(15, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
            else:
                cv2.putText(vis, f"{hedef} bulunamadi (zemin)",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 255), 2)
            cv2.imshow("Park Zemin Renk", vis)
            cv2.imshow("Mask (alt yari)", mask)
            k = cv2.waitKey(1) & 0xFF
            if k == ord('q'):
                break
            elif k == ord('r'):
                hedef = "RED"
            elif k == ord('g'):
                hedef = "GREEN"
            elif k == ord('b'):
                hedef = "BLUE"
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
