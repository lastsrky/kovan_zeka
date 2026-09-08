import pygame
import math
import numpy as np
import threading
import cv2
import time

class SanalOrtam:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SanalOrtam, cls).__new__(cls)
                cls._instance._init_once()
            return cls._instance

    def _init_once(self):
        self.width = 800
        self.height = 600
        self.car_x = 400.0
        self.car_y = 450.0
        self.car_angle = -math.pi / 2  # Yukarı bakıyor (Radyan)
        self.car_speed = 0.0
        self.car_steer = 0.0
        self.track_surface = None
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
    def _create_track(self):
        surface = pygame.Surface((self.width, self.height))
        surface.fill((200, 200, 200)) # Arka plan (gri)
        
        # Basit bir oval pist (Siyah şerit, ortası beyaz)
        pygame.draw.rect(surface, (255, 255, 255), (100, 100, 600, 400), border_radius=150)
        pygame.draw.rect(surface, (0, 0, 0), (100, 100, 600, 400), width=60, border_radius=150)
        # Beyaz şeritler (kesik kesik değil de düz yapalım şimdilik)
        pygame.draw.rect(surface, (255, 255, 255), (125, 125, 550, 350), width=10, border_radius=125)
        
        # Bir kırmızı tabela (Trafik lambası veya dur işareti)
        pygame.draw.circle(surface, (255, 0, 0), (150, 300), 20) # Kırmızı
        
        # Park alanları
        pygame.draw.rect(surface, (0, 255, 0), (600, 200, 50, 50)) # Yeşil
        pygame.draw.rect(surface, (0, 0, 255), (600, 300, 50, 50)) # Mavi

        return surface

    def _run_loop(self):
        try:
            pygame.init()
        except Exception as e:
            print("Pygame baslatilamadi, simulasyon gorseli calismayacak.", e)
            return

        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Sanal Ortam (Dijital Ikiz)")
        clock = pygame.time.Clock()
        
        self.track_surface = self._create_track()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Aracın pozisyonunu güncelle
            # max pwm ~ 300
            speed_px = (self.car_speed / 300.0) * 15.0
            
            # Açı güncelle (steer genelde ufak degerler)
            self.car_angle += self.car_steer * speed_px * 0.05
            
            self.car_x += speed_px * math.cos(self.car_angle)
            self.car_y += speed_px * math.sin(self.car_angle)

            # Çizim
            screen.blit(self.track_surface, (0, 0))
            
            # Aracı çiz
            car_surface = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(car_surface, (255, 0, 255), (10, 0, 20, 40))
            pygame.draw.rect(car_surface, (0, 255, 255), (10, 0, 20, 10))
            
            rotated_car = pygame.transform.rotate(car_surface, -math.degrees(self.car_angle) - 90)
            rect = rotated_car.get_rect(center=(int(self.car_x), int(self.car_y)))
            screen.blit(rotated_car, rect.topleft)

            pygame.display.flip()
            clock.tick(30)

        pygame.quit()
        
    def get_camera_view(self, cam_w=640, cam_h=480):
        if self.track_surface is None:
            return np.zeros((cam_h, cam_w, 3), dtype=np.uint8)
            
        view = pygame.surfarray.array3d(self.track_surface)
        view = view.transpose([1, 0, 2])
        view = cv2.cvtColor(view, cv2.COLOR_RGB2BGR)
        
        cam_x = self.car_x + 20 * math.cos(self.car_angle)
        cam_y = self.car_y + 20 * math.sin(self.car_angle)
        
        fov = math.pi / 2.5
        view_dist = 200
        
        pt_bl = (cam_x + 40 * math.cos(self.car_angle - math.pi/2), cam_y + 40 * math.sin(self.car_angle - math.pi/2))
        pt_br = (cam_x + 40 * math.cos(self.car_angle + math.pi/2), cam_y + 40 * math.sin(self.car_angle + math.pi/2))
        
        pt_tl = (cam_x + view_dist * math.cos(self.car_angle - fov/2), cam_y + view_dist * math.sin(self.car_angle - fov/2))
        pt_tr = (cam_x + view_dist * math.cos(self.car_angle + fov/2), cam_y + view_dist * math.sin(self.car_angle + fov/2))
        
        src_pts = np.float32([pt_tl, pt_tr, pt_bl, pt_br])
        dst_pts = np.float32([[0, 0], [cam_w, 0], [0, cam_h], [cam_w, cam_h]])
        
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(view, matrix, (cam_w, cam_h), flags=cv2.INTER_LINEAR)
        
        return warped

    def update_motor(self, speed, steer):
        self.car_speed = speed
        self.car_steer = steer

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
