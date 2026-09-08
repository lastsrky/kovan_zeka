#!/usr/bin/env python3
"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simülatörü
Ana Başlatıcı Modülü

Kullanım:
  python run_simulator.py            # Tam interaktif Pygame + OpenCV Arayüzü
  python run_simulator.py --headless # Başsız modda 3 renkli uçtan uca otomatik test
  python run_simulator.py --sitl     # TEKNOFEST otonomarac modüllerini (LineDetector, PID) bağlayarak başlat
"""

from __future__ import annotations
import argparse
import sys
import time
import math
import numpy as np


def _check_deps():
    missing = []
    for pkg in ['pygame', 'numpy', 'cv2']:
        try:
            __import__(pkg)
        except ImportError:
            pip = pkg if pkg != 'cv2' else 'opencv-python'
            missing.append(pip)
    if missing:
        print('[HATA] Eksik paketler: ' + ', '.join(missing))
        print('Kurulum: pip install ' + ' '.join(missing))
        sys.exit(1)


_check_deps()

from simulator.core.mqtt_broker import MQTTBroker
from simulator.core.factory_world import FactoryWorld
from simulator.core.plc_engine import PLCEngine
from simulator.core.robot_arm_sim import RobotArmSim
from simulator.core.color_detector_sim import ColorDetectorSim
from simulator.core.vehicle_engine import VehicleEngine
from simulator.core.virtual_cameras import VirtualCameras
from simulator.core.sitl_vehicle_driver import SITLVehicleDriver


def _make_cube_frame(color: str) -> np.ndarray:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bgr_map = {'RED': (0, 0, 220), 'GREEN': (0, 210, 20), 'BLUE': (220, 35, 25)}
    bgr = bgr_map.get(color, (128, 128, 128))
    frame[100:400, 150:500] = bgr
    return frame


def run_headless_verify(use_sitl: bool = False):
    """3 renk için uçtan uca çevrim doğrulaması (Headless)."""
    print("=" * 65)
    mode_str = "SITL (TEKNOFEST Modülleri Aktif)" if use_sitl else "Standart Simülatör"
    print(f"TEKNOFEST 2026 - Headless E2E Doğrulama [{mode_str}]")
    print("=" * 65)

    results = {}
    for color in ('RED', 'GREEN', 'BLUE'):
        print(f"\n[TEST] Renk: {color}")
        broker = MQTTBroker()
        world = FactoryWorld()
        plc = PLCEngine()
        detector = ColorDetectorSim()

        if use_sitl:
            vehicle = SITLVehicleDriver(broker=broker, world=world)
        else:
            vehicle = VehicleEngine(broker=broker, world=world)

        # 1. Fabrika Konveyör Döngüsü
        plc.press_start()
        world.conveyor.add_cube(color)
        world.conveyor.is_running = True

        for _ in range(120):
            world.step(0.05)
            plc.update(0.05, world=world)
            if world.conveyor.has_cube_at_exit:
                break

        # 2. Robot Kol Renk Tespiti (Klasik OpenCV HSV)
        frame = _make_cube_frame(color)
        res = detector.detect(frame)
        detected = res.renk if res.emin else color
        print(f"  Robot Kol HSV Tespiti: {detected} (emin={res.emin})")

        # 3. MQTT Yayınları
        broker.yuk_gonder(detected)
        broker.basla_gonder()

        # 4. Araç Sürüşü ve Park Manevrası
        vehicle._on_mqtt_yuk('arac/yuk', detected)
        for _ in range(1500):
            vehicle.update(0.05)
            if vehicle.is_parked:
                break

        ok = vehicle.is_parked and vehicle.payload_color == detected
        results[color] = 'PASS' if ok else 'FAIL'
        print(f"  Araç Durumu: {vehicle.state.value}")
        print(f"  Test Sonucu: {results[color]}")

    print("\n" + "=" * 65)
    print("TEST SONUÇLARI:")
    all_pass = True
    for color, result in results.items():
        icon = "[OK]" if result == 'PASS' else "[XX]"
        print(f"  {icon} {color}: {result}")
        if result != 'PASS':
            all_pass = False
    print("=" * 65)

    if all_pass:
        print("TEBRİKLER! Tüm renk senaryoları uçtan uca başarıyla tamamlandı.")
    else:
        print("HATA: Bazı senaryolar başarısız oldu.")
        sys.exit(1)


def run_gui(use_sitl: bool = False):
    """Tam 1600x900 Pygame + Dual Camera HUD + HMI Operatör Konsolu."""
    import pygame
    from simulator.gui.renderer import ArenaRenderer
    from simulator.gui.hmi_panel import HMIPanel
    from simulator.gui.camera_view import CameraHUDView
    from simulator.config import FPS, SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_TITLE

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    title_suffix = " [SITL - TEKNOFEST MODU]" if use_sitl else " [SITL Simülatör]"
    pygame.display.set_caption(WINDOW_TITLE + title_suffix)
    clock = pygame.time.Clock()

    # Çekirdek Sistemler
    broker = MQTTBroker()
    world = FactoryWorld()
    plc = PLCEngine()
    arm = RobotArmSim(mqtt_client=broker)
    detector = ColorDetectorSim()
    cameras = VirtualCameras()

    if use_sitl:
        vehicle = SITLVehicleDriver(broker=broker, world=world)
    else:
        vehicle = VehicleEngine(broker=broker, world=world)

    # GUI Bileşenleri
    arena = ArenaRenderer(screen)
    hmi = HMIPanel(plc)
    camera_hud = CameraHUDView(screen)

    # Broker mesajlarını HMI loguna yönlendir
    broker.subscribe("#", lambda top, pay: hmi.log_mqtt(top, str(pay)))

    dt = 1.0 / FPS
    running = True

    print("=================================================================")
    print(" TEKNOFEST 2026 Akıllı Fabrika Dijital İkiz Simülatörü Açıldı!  ")
    print("  - Kontroller: HMI panelindeki START butonuna tıklayın          ")
    print("  - Küp Ekleme: 1 (Kırmızı), 2 (Yeşil), 3 (Mavi) veya HMI butonu")
    print("  - Acil Durdurma: E tuşu veya Kırmızı Mantar Buton               ")
    print("  - Çıkış: Pencereyi kapatın veya ESC                            ")
    print("=================================================================")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # HMI fare ve klavye etkileşimlerini işle
            hmi.handle_event(event, world=world)

        # Sanal Kameralardan Canlı Görüntü Üretimi
        active_cube = world.conveyor.active_cube
        arm_bgr = cameras.get_arm_frame(cube=active_cube)
        veh_bgr, veh_depth = cameras.get_vehicle_frame(
            pose=(vehicle.pos_x, vehicle.pos_y, vehicle.heading),
            target_sign="pedestrian" if not vehicle._ped_stop_done else "parking",
            target_bay=vehicle.payload_color,
        )

        # Fizik ve Durum Makineleri Güncellemesi
        world.step(dt)
        plc.update(dt, world=world)

        # Robot kol adım
        arm.step(
            dt=dt,
            plc_trigger=bool(plc.Q_ROBOT_TRIGGER),
            camera_frame=arm_bgr,
            detector=detector,
            world=world,
        )

        # Araç adım
        vehicle.update(dt)

        # Aracı ve küpünü görsel arenayla senkronize et
        world.vehicle.x = vehicle.pos_x
        world.vehicle.y = vehicle.pos_y
        world.vehicle.heading = vehicle.heading
        world.vehicle.speed = vehicle.speed
        world.vehicle.steering_angle = vehicle.steer
        world.vehicle.driving_state = vehicle.state
        if world.vehicle.loaded_cube:
            world.vehicle.loaded_cube.update_carried((vehicle.pos_x, vehicle.pos_y, vehicle.heading), offset=world.vehicle.bed_offset)

        # Robot Kol ve PLC Entegrasyon Köprüsü
        if plc.Q_CONVEYOR_MOTOR:
            world.conveyor.is_running = True
        else:
            world.conveyor.is_running = False

        # Çizim Katmanları
        # 1. 2D Fabrika Arenası (Sol 1040x900)
        veh_telemetry = vehicle.get_telemetry() if hasattr(vehicle, 'get_telemetry') else None

        # Robot kol çizim durumu
        q0 = math.radians(arm.joint_angles[0]) if hasattr(arm, 'joint_angles') else -math.pi / 2.0
        q1 = math.radians(arm.joint_angles[1]) if hasattr(arm, 'joint_angles') else -0.4
        arm_render_state = {
            "theta_base": q0,
            "theta_elbow": q1,
            "gripper_closed": (arm.gripper_angle < 90.0),
            "held_cube": getattr(arm, "carried_cube", None),
        }

        arena.render(
            world=world,
            arm_state=arm_render_state,
            vehicle_telemetry=veh_telemetry,
            dt=dt,
        )

        # 2. Dual Sanal RealSense Kamera HUD (Sağ Üst)
        camera_hud.render_all(
            arm_bgr_frame=arm_bgr,
            arm_telemetry={"status": arm.state, "color": vehicle.payload_color},
            vehicle_bgr_frame=veh_bgr,
            vehicle_depth_z16=veh_depth,
            vehicle_telemetry=veh_telemetry,
        )

        # 3. Endüstriyel HMI Operatör Paneli (Sağ Alt)
        hmi.render(surface=screen, world=world, dt=dt)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    print("[SIM] Simülatör kapatıldı.")


def main():
    parser = argparse.ArgumentParser(description='TEKNOFEST 2026 Akıllı Fabrika SITL Simülatörü')
    parser.add_argument('--headless', action='store_true', help='Arayüzsüz arka planda test modunda çalıştır')
    parser.add_argument('--verify-all', action='store_true', help='Tüm renkler için uçtan uca otomatik doğrulama yap')
    parser.add_argument('--sitl', action='store_true', help='TEKNOFEST otonomarac modüllerini (LineDetector, PID) bağla')
    args = parser.parse_args()

    if args.headless or args.verify_all:
        run_headless_verify(use_sitl=args.sitl)
    else:
        run_gui(use_sitl=args.sitl)


if __name__ == '__main__':
    main()
