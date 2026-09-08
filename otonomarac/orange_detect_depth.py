"""
Sollama için turuncu kutuyu bulur ve mesafesini ölçer.

HSV ve LAB a* kanalıyla turuncuyu sarıdan ayırır, boyut / oran / konum
filtreleriyle zemin ve duvar yansımalarını eler, bbox içindeki depth
medyanıyla mesafeyi cm olarak döndürür.

overtake.py bunu kullanır.
"""

import pyrealsense2 as rs
import numpy as np
import cv2

ORANGE_HSV_MIN = np.array([0, 100, 70])
ORANGE_HSV_MAX = np.array([22, 255, 255])
ORANGE_AREA_MIN = 600
ORANGE_KERNEL = np.ones((3, 3), np.uint8)
ORANGE_MAX_ASPECT = 2.0
ORANGE_MIN_WH = 35
ORANGE_X_KENAR = 0.15
ORANGE_Y_ALT_ORAN = 0.40
ORANGE_LAB_A_MIN = 130


def detect_orange(color_image, depth_image, depth_scale, *, strict=True):
    hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
    hsv_mask = cv2.inRange(hsv, ORANGE_HSV_MIN, ORANGE_HSV_MAX)

    lab = cv2.cvtColor(color_image, cv2.COLOR_BGR2LAB)
    a_kanal = lab[:, :, 1]
    lab_mask = (a_kanal >= ORANGE_LAB_A_MIN).astype(np.uint8) * 255
    mask = cv2.bitwise_and(hsv_mask, lab_mask)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, ORANGE_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ORANGE_KERNEL)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_h, img_w = color_image.shape[:2]
    x_min_kabul = int(img_w * ORANGE_X_KENAR)
    x_max_kabul = int(img_w * (1 - ORANGE_X_KENAR))
    y_min_alt = int(img_h * ORANGE_Y_ALT_ORAN)
    best = None
    for cnt in contours:
        area = int(cv2.contourArea(cnt))
        if area < ORANGE_AREA_MIN:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if strict:
            if w < ORANGE_MIN_WH or h < ORANGE_MIN_WH:
                continue
            if max(w, h) > ORANGE_MAX_ASPECT * min(w, h):
                continue
            cx = x + w // 2
            if cx < x_min_kabul or cx > x_max_kabul:
                continue
            if (y + h) < y_min_alt:
                continue
        roi = depth_image[y:y+h, x:x+w].astype(np.float32)
        valid = roi[roi > 0]
        if valid.size == 0:
            continue
        dist_cm = float(np.median(valid)) * depth_scale * 100.0
        if best is None or dist_cm < best[0]:
            best = (dist_cm, area, (x, y, w, h))
    if best is None:
        return None
    dist_cm, area, bbox = best
    return (bbox, dist_cm, area)


def main():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    profile = pipeline.start(config)

    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()
    align = rs.align(rs.stream.color)

    print(f"[orange_detect] depth_scale={depth_scale}")
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

            hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
            preview_mask = cv2.inRange(hsv, ORANGE_HSV_MIN, ORANGE_HSV_MAX)
            preview_mask = cv2.morphologyEx(preview_mask, cv2.MORPH_OPEN, ORANGE_KERNEL)
            preview_mask = cv2.morphologyEx(preview_mask, cv2.MORPH_CLOSE, ORANGE_KERNEL)

            result = detect_orange(color_image, depth_image, depth_scale)
            if result is not None:
                (x, y, w, h), dist_cm, area = result
                label = f"{dist_cm:.1f} cm a={area}" if dist_cm is not None else f"-- cm a={area}"
                cv2.rectangle(color_image, (x, y), (x + w, y + h), (0, 140, 255), 2)
                cv2.putText(color_image, label, (x, max(15, y - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2)

            cv2.imshow("Orange Detect + Depth", color_image)
            cv2.imshow("Orange Mask", preview_mask)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
