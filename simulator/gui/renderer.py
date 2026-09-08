"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Pygame 2D Arena Birds-Eye Renderer Module

Author: M1 Core Simulator Team
Module: simulator.gui.renderer
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pygame

from simulator.config import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    BAY_BLUE_CENTER,
    BAY_BLUE_RECT,
    BAY_GREEN_CENTER,
    BAY_GREEN_RECT,
    BAY_HEIGHT,
    BAY_RED_CENTER,
    BAY_RED_RECT,
    BAY_WIDTH,
    COLOR_ARM_BASE,
    COLOR_ARM_GRIPPER,
    COLOR_ARM_LINK_1,
    COLOR_ARM_LINK_2,
    COLOR_BAY_BLUE,
    COLOR_BAY_BORDER,
    COLOR_BAY_GREEN,
    COLOR_BAY_LABEL,
    COLOR_BAY_RED,
    COLOR_CONVEYOR_ARROW,
    COLOR_CONVEYOR_BELT,
    COLOR_CONVEYOR_FRAME,
    COLOR_CONVEYOR_ROLLER,
    COLOR_CUBE_BLUE,
    COLOR_CUBE_BORDER,
    COLOR_CUBE_GREEN,
    COLOR_CUBE_RED,
    COLOR_FLOOR,
    COLOR_FLOOR_GRID,
    COLOR_ROAD_ASPHALT,
    COLOR_ROAD_CENTER_LINE,
    COLOR_ROAD_OUTER_LINE,
    COLOR_SENSOR_BEAM_OFF,
    COLOR_SENSOR_BEAM_ON,
    COLOR_SENSOR_HOUSING,
    COLOR_TOWER_AMBER_OFF,
    COLOR_TOWER_AMBER_ON,
    COLOR_TOWER_GREEN_OFF,
    COLOR_TOWER_GREEN_ON,
    COLOR_TOWER_RED_OFF,
    COLOR_TOWER_RED_ON,
    COLOR_VEHICLE_BED,
    COLOR_VEHICLE_BODY,
    COLOR_VEHICLE_HEADLIGHT,
    COLOR_VEHICLE_ROOF,
    COLOR_VEHICLE_WHEEL,
    COLOR_WALL_BORDER,
    COLOR_ZEBRA_STRIPES,
    CONVEYOR_HEIGHT,
    CONVEYOR_RECT,
    CONVEYOR_WIDTH,
    CONVEYOR_X,
    CONVEYOR_Y,
    EAST_CURVE_CENTER,
    EAST_CURVE_RADIUS,
    ROAD_WIDTH,
    ROBOT_BASE_POS,
    ROBOT_CELL_RECT,
    SENSOR_S1_BEAM_P1,
    SENSOR_S1_BEAM_P2,
    SENSOR_S1_HEIGHT,
    SENSOR_S1_X,
    SENSOR_S1_Y,
    SENSOR_S2_BEAM_P1,
    SENSOR_S2_BEAM_P2,
    SENSOR_S2_HEIGHT,
    SENSOR_S2_X,
    SENSOR_S2_Y,
    SENSOR_S3_CENTER,
    SENSOR_S3_RADIUS,
    SIGN_PARK_POS,
    SIGN_PARK_SIZE,
    SIGN_PEDESTRIAN_POS,
    SIGN_PEDESTRIAN_SIZE,
    SIGNAL_TOWER_RECT,
    TRACK_STRAIGHT_1_END,
    TRACK_STRAIGHT_1_START,
    TRACK_STRAIGHT_2_END,
    TRACK_STRAIGHT_2_START,
    TRACK_STRAIGHT_3_END,
    TRACK_STRAIGHT_3_START,
    VEHICLE_DOCK_CENTER,
    VEHICLE_DOCK_RECT,
    WEST_CURVE_CENTER,
    WEST_CURVE_RADIUS,
    ZEBRA_CROSSING_RECT,
)
from simulator.core.factory_world import Cube, CubeColor, CubeState, FactoryWorld


class ArenaRenderer:
    """
    Renders the 1040x900 birds-eye continuous factory environment:
    - High-tech industrial floor grid and safety boundaries
    - Closed-loop 2-lane track circuit with dashed centerline and direction markings
    - Pedestrian zebra crossing and physical traffic signposts
    - Red, Green, Blue parking bays with stall markings
    - Conveyor belt with dynamic texture animation, rollers, and optical beams (S1, S2)
    - Siemens S7-1200 Stack Lamp Tower with glowing translucent halos
    - 4-DOF articulated robot arm cell with gripper and carried workpieces
    - Autonomous vehicle with steerable wheels, headlights, cargo bed, and camera FOV
    """

    def __init__(self, target_surface: pygame.Surface):
        self.surface = target_surface
        self.arena_rect = pygame.Rect(0, 0, ARENA_WIDTH, ARENA_HEIGHT)

        # Pre-allocate font instances
        pygame.font.init()
        self._init_fonts()

        # Conveyor animation offset
        self.conveyor_phase: float = 0.0

        # Pre-baked static background surface for high rendering performance
        self.background_surface = pygame.Surface((ARENA_WIDTH, ARENA_HEIGHT))
        self._prebake_background()

    def _init_fonts(self):
        """Initializes fallback-safe UI fonts."""
        try:
            self.font_small = pygame.font.SysFont("consolas", 11, bold=True)
            self.font_medium = pygame.font.SysFont("consolas", 13, bold=True)
            self.font_title = pygame.font.SysFont("consolas", 16, bold=True)
            self.font_sign = pygame.font.SysFont("arial", 12, bold=True)
        except Exception:
            self.font_small = pygame.font.Font(None, 14)
            self.font_medium = pygame.font.Font(None, 16)
            self.font_title = pygame.font.Font(None, 20)
            self.font_sign = pygame.font.Font(None, 16)

    def _prebake_background(self):
        """Pre-renders static floor, walls, and track geometry onto a cached surface."""
        bg = self.background_surface
        bg.fill(COLOR_FLOOR)

        # 1. Subtle 1-meter (100 px) grid lines
        for x in range(0, ARENA_WIDTH, 100):
            pygame.draw.line(bg, COLOR_FLOOR_GRID, (x, 0), (x, ARENA_HEIGHT), 1)
        for y in range(0, ARENA_HEIGHT, 100):
            pygame.draw.line(bg, COLOR_FLOOR_GRID, (0, y), (ARENA_WIDTH, y), 1)

        # 2. Outer safety boundary walls
        pygame.draw.rect(bg, COLOR_WALL_BORDER, self.arena_rect, 4)
        pygame.draw.rect(bg, (210, 215, 222), self.arena_rect.inflate(-12, -12), 1)

        # 3. Zone Watermark Annotations
        txt_prod = self.font_title.render("PRODUCTION CELL A", True, (215, 220, 228))
        txt_track = self.font_title.render("AUTONOMOUS CIRCUIT TRACK", True, (215, 220, 228))
        txt_park = self.font_title.render("PARKING / STORAGE BAYS", True, (215, 220, 228))
        bg.blit(txt_prod, (140, 45))
        bg.blit(txt_track, (450, 410))
        bg.blit(txt_park, (220, 680))

        # 4. Pre-bake Static Track Asphalt Bed
        self._render_road_asphalt(bg)

    def _render_road_asphalt(self, surf: pygame.Surface):
        """Draws the asphalt road surface for straights and semicircular arcs."""
        half_w = ROAD_WIDTH / 2.0  # 45.0 px

        # Straight 1 (North): (380, 270) -> (850, 270)
        r1 = pygame.Rect(
            int(TRACK_STRAIGHT_1_START[0]),
            int(TRACK_STRAIGHT_1_START[1] - half_w),
            int(TRACK_STRAIGHT_1_END[0] - TRACK_STRAIGHT_1_START[0]),
            int(ROAD_WIDTH),
        )
        pygame.draw.rect(surf, COLOR_ROAD_ASPHALT, r1)

        # Straight 2 (South): (250, 570) -> (850, 570)
        r2 = pygame.Rect(
            int(TRACK_STRAIGHT_2_END[0]),
            int(TRACK_STRAIGHT_2_START[1] - half_w),
            int(TRACK_STRAIGHT_2_START[0] - TRACK_STRAIGHT_2_END[0]),
            int(ROAD_WIDTH),
        )
        pygame.draw.rect(surf, COLOR_ROAD_ASPHALT, r2)

        # Straight 3 (Dock Approach): (250, 270) -> (380, 270)
        r3 = pygame.Rect(
            int(TRACK_STRAIGHT_3_START[0]),
            int(TRACK_STRAIGHT_3_START[1] - half_w),
            int(TRACK_STRAIGHT_3_END[0] - TRACK_STRAIGHT_3_START[0]),
            int(ROAD_WIDTH),
        )
        pygame.draw.rect(surf, COLOR_ROAD_ASPHALT, r3)

        # East Curve (Turn 1): Center (850, 420), R=150
        cx_e, cy_e = int(EAST_CURVE_CENTER[0]), int(EAST_CURVE_CENTER[1])
        r_outer_e = int(EAST_CURVE_RADIUS + half_w)
        r_inner_e = int(EAST_CURVE_RADIUS - half_w)
        for r in range(r_inner_e, r_outer_e + 1):
            pygame.draw.circle(surf, COLOR_ROAD_ASPHALT, (cx_e, cy_e), r, 1)

        # West Curve (Turn 2): Center (250, 420), R=150
        cx_w, cy_w = int(WEST_CURVE_CENTER[0]), int(WEST_CURVE_CENTER[1])
        r_outer_w = int(WEST_CURVE_RADIUS + half_w)
        r_inner_w = int(WEST_CURVE_RADIUS - half_w)
        for r in range(r_inner_w, r_outer_w + 1):
            pygame.draw.circle(surf, COLOR_ROAD_ASPHALT, (cx_w, cy_w), r, 1)

    def render(
        self,
        world: FactoryWorld,
        plc_state: Optional[Dict[str, Any]] = None,
        arm_state: Optional[Dict[str, Any]] = None,
        vehicle_telemetry: Optional[Dict[str, Any]] = None,
        dt: float = 0.01667,
    ):
        """
        Master render call. Draws all factory entities onto the arena surface.
        """
        # Blit pre-baked background
        self.surface.blit(self.background_surface, (0, 0))

        # Update animated conveyor offset
        if world.conveyor.is_running:
            self.conveyor_phase = (self.conveyor_phase + world.conveyor.speed * dt) % 24.0

        # Layer 1: Road Lane Markings & Dashed Centerlines
        self._render_lane_markings()

        # Layer 2: Pedestrian Crossing & Traffic Signs
        self._render_pedestrian_crossing()
        self._render_traffic_signs()

        # Layer 3: Ground Color Parking Bays
        self._render_parking_bays(world)

        # Layer 4: Vehicle Loading Dock (DOCK)
        self._render_loading_dock(world)

        # Layer 5: Conveyor Belt, Sensors & Moving Cubes
        self._render_conveyor(world)

        # Layer 6: S7-1200 Stack Signal Tower
        self._render_stack_tower(world, plc_state)

        # Layer 7: 4-DOF Articulated Robot Arm Cell
        self._render_robot_arm_cell(world, arm_state)

        # Layer 8: Autonomous Vehicle with Wheels, Frustum & Cargo
        self._render_vehicle(world, vehicle_telemetry)

        # Layer 9: HUD Scale, Coordinate Grid, and Status Badges
        self._render_hud_annotations(world)

    def _render_lane_markings(self):
        """Renders solid white outer boundaries and dashed yellow centerlines."""
        surf = self.surface
        half_w = ROAD_WIDTH / 2.0

        # Outer & Inner Solid Lines - Straight 1
        y_top_1 = int(TRACK_STRAIGHT_1_START[1] - half_w)
        y_bot_1 = int(TRACK_STRAIGHT_1_START[1] + half_w)
        x_start_1 = int(TRACK_STRAIGHT_3_START[0])
        x_end_1 = int(TRACK_STRAIGHT_1_END[0])
        pygame.draw.line(surf, COLOR_ROAD_OUTER_LINE, (x_start_1, y_top_1), (x_end_1, y_top_1), 2)
        pygame.draw.line(surf, COLOR_ROAD_OUTER_LINE, (x_start_1, y_bot_1), (x_end_1, y_bot_1), 2)

        # Outer & Inner Solid Lines - Straight 2
        y_top_2 = int(TRACK_STRAIGHT_2_START[1] - half_w)
        y_bot_2 = int(TRACK_STRAIGHT_2_START[1] + half_w)
        x_start_2 = int(TRACK_STRAIGHT_2_END[0])
        x_end_2 = int(TRACK_STRAIGHT_2_START[0])
        pygame.draw.line(surf, COLOR_ROAD_OUTER_LINE, (x_start_2, y_top_2), (x_end_2, y_top_2), 2)
        pygame.draw.line(surf, COLOR_ROAD_OUTER_LINE, (x_start_2, y_bot_2), (x_end_2, y_bot_2), 2)

        # Outer & Inner Curves - East Curve
        cx_e, cy_e = int(EAST_CURVE_CENTER[0]), int(EAST_CURVE_CENTER[1])
        r_out_e = int(EAST_CURVE_RADIUS + half_w)
        r_in_e = int(EAST_CURVE_RADIUS - half_w)
        pygame.draw.arc(surf, COLOR_ROAD_OUTER_LINE, (cx_e - r_out_e, cy_e - r_out_e, 2 * r_out_e, 2 * r_out_e), -math.pi / 2, math.pi / 2, 2)
        pygame.draw.arc(surf, COLOR_ROAD_OUTER_LINE, (cx_e - r_in_e, cy_e - r_in_e, 2 * r_in_e, 2 * r_in_e), -math.pi / 2, math.pi / 2, 2)

        # Outer & Inner Curves - West Curve
        cx_w, cy_w = int(WEST_CURVE_CENTER[0]), int(WEST_CURVE_CENTER[1])
        r_out_w = int(WEST_CURVE_RADIUS + half_w)
        r_in_w = int(WEST_CURVE_RADIUS - half_w)
        pygame.draw.arc(surf, COLOR_ROAD_OUTER_LINE, (cx_w - r_out_w, cy_w - r_out_w, 2 * r_out_w, 2 * r_out_w), math.pi / 2, 3 * math.pi / 2, 2)
        pygame.draw.arc(surf, COLOR_ROAD_OUTER_LINE, (cx_w - r_in_w, cy_w - r_in_w, 2 * r_in_w, 2 * r_in_w), math.pi / 2, 3 * math.pi / 2, 2)

        # Dashed Centerlines: Straight 1
        dash_len = 16
        gap_len = 14
        y_mid_1 = int(TRACK_STRAIGHT_1_START[1])
        for x in range(x_start_1, x_end_1, dash_len + gap_len):
            pygame.draw.line(surf, COLOR_ROAD_CENTER_LINE, (x, y_mid_1), (min(x + dash_len, x_end_1), y_mid_1), 2)

        # Dashed Centerlines: Straight 2
        y_mid_2 = int(TRACK_STRAIGHT_2_START[1])
        for x in range(x_start_2, x_end_2, dash_len + gap_len):
            pygame.draw.line(surf, COLOR_ROAD_CENTER_LINE, (x, y_mid_2), (min(x + dash_len, x_end_2), y_mid_2), 2)

        # Dashed Centerlines: East Curve
        n_dashes_e = 14
        d_theta = math.pi / (n_dashes_e * 2)
        for i in range(n_dashes_e):
            th1 = -math.pi / 2 + (2 * i) * d_theta
            th2 = th1 + d_theta
            pts = []
            for th in np.linspace(th1, th2, 4):
                px = cx_e + EAST_CURVE_RADIUS * math.cos(th)
                py = cy_e + EAST_CURVE_RADIUS * math.sin(th)
                pts.append((int(px), int(py)))
            if len(pts) >= 2:
                pygame.draw.lines(surf, COLOR_ROAD_CENTER_LINE, False, pts, 2)

        # Dashed Centerlines: West Curve
        for i in range(n_dashes_e):
            th1 = math.pi / 2 + (2 * i) * d_theta
            th2 = th1 + d_theta
            pts = []
            for th in np.linspace(th1, th2, 4):
                px = cx_w + WEST_CURVE_RADIUS * math.cos(th)
                py = cy_w + WEST_CURVE_RADIUS * math.sin(th)
                pts.append((int(px), int(py)))
            if len(pts) >= 2:
                pygame.draw.lines(surf, COLOR_ROAD_CENTER_LINE, False, pts, 2)

    def _render_pedestrian_crossing(self):
        """Renders zebra crossing stripes across the roadway."""
        surf = self.surface
        zx, zy, zw, zh = ZEBRA_CROSSING_RECT
        n_stripes = 7
        stripe_h = zh / n_stripes
        for i in range(0, n_stripes, 2):
            sy = zy + i * stripe_h
            pygame.draw.rect(surf, COLOR_ZEBRA_STRIPES, (zx, int(sy), zw, int(stripe_h - 1)))

    def _render_traffic_signs(self):
        """Renders signposts and pictograms for Pedestrian (ID 0) and Parking (ID 5)."""
        surf = self.surface

        # 1. Pedestrian Sign (ID 0)
        px, py = SIGN_PEDESTRIAN_POS
        pw, ph = SIGN_PEDESTRIAN_SIZE
        pygame.draw.line(surf, (80, 85, 95), (px + pw // 2, py + ph), (px + pw // 2, py + ph + 16), 3)
        tri_pts = [(px + pw // 2, py), (px, py + ph), (px + pw, py + ph)]
        pygame.draw.polygon(surf, (255, 215, 0), tri_pts)
        pygame.draw.polygon(surf, (20, 20, 20), tri_pts, 2)
        txt_ped = self.font_small.render("YAYA", True, (20, 20, 20))
        surf.blit(txt_ped, (px + 3, py + 12))

        # 2. Parking Sign (ID 5)
        kx, ky = SIGN_PARK_POS
        kw, kh = SIGN_PARK_SIZE
        pygame.draw.line(surf, (80, 85, 95), (kx + kw // 2, ky + kh), (kx + kw // 2, ky + kh + 16), 3)
        pygame.draw.rect(surf, (30, 100, 240), (kx, ky, kw, kh), border_radius=4)
        pygame.draw.rect(surf, (255, 255, 255), (kx, ky, kw, kh), 2, border_radius=4)
        txt_p = self.font_sign.render("P", True, (255, 255, 255))
        surf.blit(txt_p, (kx + 10, ky + 6))

    def _render_parking_bays(self, world: FactoryWorld):
        """Renders Red, Green, Blue floor parking bays with stall markings."""
        surf = self.surface

        bays = [
            ("RED", BAY_RED_RECT, COLOR_BAY_RED, "RED / 1"),
            ("GREEN", BAY_GREEN_RECT, COLOR_BAY_GREEN, "GREEN / 2"),
            ("BLUE", BAY_BLUE_RECT, COLOR_BAY_BLUE, "BLUE / 3"),
        ]

        for name, rect, color, label in bays:
            rx, ry, rw, rh = rect
            pygame.draw.rect(surf, color, rect)
            pygame.draw.rect(surf, COLOR_BAY_BORDER, rect, 2)
            pygame.draw.rect(surf, (50, 50, 50), (rx + 6, ry + rh - 8, rw - 12, 5))
            lbl = self.font_small.render(label, True, COLOR_BAY_LABEL)
            surf.blit(lbl, (rx + 4, ry + 10))

    def _render_loading_dock(self, world: FactoryWorld):
        """Renders the autonomous vehicle loading bay with diagonal hazard stripes."""
        surf = self.surface
        dx, dy, dw, dh = VEHICLE_DOCK_RECT

        pygame.draw.rect(surf, (35, 40, 48), VEHICLE_DOCK_RECT)
        pygame.draw.rect(surf, (245, 200, 30), VEHICLE_DOCK_RECT, 2)

        stripe_w = 8
        for sx in range(dx - dh, dx + dw, stripe_w * 2):
            p1 = (max(dx, sx), dy)
            p2 = (min(dx + dw, sx + dh), min(dy + dh, dy + (min(dx + dw, sx + dh) - sx)))
            if p2[0] > p1[0] and p2[1] > p1[1]:
                pygame.draw.line(surf, (245, 200, 30), p1, p2, 2)

        s3_active = world.dock_sensor.is_active
        led_color = (0, 255, 120) if s3_active else (80, 85, 95)
        pygame.draw.circle(surf, led_color, (int(SENSOR_S3_CENTER[0]), int(SENSOR_S3_CENTER[1])), 5)
        lbl_s3 = self.font_small.render("S3 DOCK", True, (200, 205, 215))
        surf.blit(lbl_s3, (dx + 12, dy + dh - 16))

    def _render_conveyor(self, world: FactoryWorld):
        """Renders conveyor belt with moving chevron textures, rollers, and optical beams."""
        surf = self.surface
        cx, cy, cw, ch = CONVEYOR_RECT

        # Frame
        pygame.draw.rect(surf, COLOR_CONVEYOR_FRAME, (cx - 6, cy - 4, cw + 12, ch + 8), border_radius=4)
        for bx in (cx + 20, cx + cw // 2, cx + cw - 20):
            pygame.draw.rect(surf, (50, 54, 62), (bx - 4, cy + ch + 4, 8, 10))

        # Belt
        pygame.draw.rect(surf, COLOR_CONVEYOR_BELT, CONVEYOR_RECT)

        # Chevrons
        chevron_gap = 36
        for offset in range(-chevron_gap, cw + chevron_gap, chevron_gap):
            px = cx + offset + int(self.conveyor_phase)
            if cx + 4 <= px <= cx + cw - 16:
                pts = [(px, cy + 10), (px + 10, cy + ch // 2), (px, cy + ch - 10)]
                pygame.draw.lines(surf, COLOR_CONVEYOR_ARROW, False, pts, 2)

        # Rollers
        pygame.draw.circle(surf, COLOR_CONVEYOR_ROLLER, (cx + 4, cy + ch // 2), ch // 2 - 2)
        pygame.draw.circle(surf, COLOR_CONVEYOR_ROLLER, (cx + cw - 4, cy + ch // 2), ch // 2 - 2)

        # Sensors S1 & S2
        s1_active = world.conveyor.sensor_s1.is_active
        beam_s1_col = COLOR_SENSOR_BEAM_ON if s1_active else COLOR_SENSOR_BEAM_OFF
        pygame.draw.rect(surf, COLOR_SENSOR_HOUSING, (SENSOR_S1_X - 4, cy - 8, 8, 8))
        pygame.draw.rect(surf, COLOR_SENSOR_HOUSING, (SENSOR_S1_X - 4, cy + ch, 8, 8))
        pygame.draw.line(surf, beam_s1_col, SENSOR_S1_BEAM_P1, SENSOR_S1_BEAM_P2, 2 if s1_active else 1)

        s2_active = world.conveyor.sensor_s2.is_active
        beam_s2_col = COLOR_SENSOR_BEAM_ON if s2_active else COLOR_SENSOR_BEAM_OFF
        pygame.draw.rect(surf, COLOR_SENSOR_HOUSING, (SENSOR_S2_X - 4, cy - 8, 8, 8))
        pygame.draw.rect(surf, COLOR_SENSOR_HOUSING, (SENSOR_S2_X - 4, cy + ch, 8, 8))
        pygame.draw.line(surf, beam_s2_col, SENSOR_S2_BEAM_P1, SENSOR_S2_BEAM_P2, 2 if s2_active else 1)

        t_s1 = self.font_small.render("S1", True, (220, 225, 235))
        t_s2 = self.font_small.render("S2", True, (220, 225, 235))
        surf.blit(t_s1, (SENSOR_S1_X - 6, cy - 20))
        surf.blit(t_s2, (SENSOR_S2_X - 6, cy - 20))

        # Render Active Cubes on Conveyor
        for cube in world.conveyor.cubes:
            if not cube.is_picked and not cube.is_loaded and cube.state != CubeState.DELIVERED:
                self._render_cube(cube)

    def _render_cube(self, cube: Cube):
        """Renders an industrial workpiece cube with 2.5D bevel highlight."""
        surf = self.surface
        sz = int(cube.size // 2) if cube.size > 25.0 else int(cube.size)
        half = sz // 2
        cx, cy = int(cube.position[0]), int(cube.position[1])
        rect = pygame.Rect(cx - half, cy - half, sz, sz)

        pygame.draw.rect(surf, cube.rgb, rect)
        pygame.draw.line(surf, (255, 255, 255), (rect.left, rect.top), (rect.right, rect.top), 1)
        pygame.draw.line(surf, (255, 255, 255), (rect.left, rect.top), (rect.left, rect.bottom), 1)
        pygame.draw.line(surf, (30, 30, 30), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1), 1)
        pygame.draw.line(surf, (30, 30, 30), (rect.right - 1, rect.top), (rect.right - 1, rect.bottom), 1)

        glyph = str(cube.color)[0]
        txt = self.font_small.render(glyph, True, (255, 255, 255))
        surf.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

    def _render_stack_tower(self, world: FactoryWorld, plc_state: Optional[Dict[str, Any]]):
        """Renders S7-1200 signal tower with glowing translucent illumination halos."""
        surf = self.surface
        tx, ty, tw, th = SIGNAL_TOWER_RECT

        pygame.draw.rect(surf, (40, 44, 50), (tx + tw // 2 - 3, ty + th, 6, 20))
        pygame.draw.rect(surf, (30, 33, 38), SIGNAL_TOWER_RECT, border_radius=4)
        pygame.draw.rect(surf, (70, 75, 85), SIGNAL_TOWER_RECT, 1, border_radius=4)

        red_on = plc_state.get("red_lamp", True) if plc_state else True
        amber_on = plc_state.get("amber_lamp", False) if plc_state else False
        green_on = plc_state.get("green_lamp", False) if plc_state else False

        lamps = [
            (ty + 14, COLOR_TOWER_RED_ON if red_on else COLOR_TOWER_RED_OFF, red_on, (255, 40, 40)),
            (ty + 39, COLOR_TOWER_AMBER_ON if amber_on else COLOR_TOWER_AMBER_OFF, amber_on, (255, 200, 30)),
            (ty + 64, COLOR_TOWER_GREEN_ON if green_on else COLOR_TOWER_GREEN_OFF, green_on, (40, 255, 60)),
        ]

        for ly, col, is_lit, glow_col in lamps:
            pygame.draw.circle(surf, col, (tx + tw // 2, ly), 9)
            pygame.draw.circle(surf, (20, 22, 26), (tx + tw // 2, ly), 9, 1)

            if is_lit:
                halo_surf = pygame.Surface((36, 36), pygame.SRCALPHA)
                pygame.draw.circle(halo_surf, (*glow_col, 70), (18, 18), 17)
                pygame.draw.circle(halo_surf, (*glow_col, 130), (18, 18), 11)
                surf.blit(halo_surf, (tx + tw // 2 - 18, ly - 18))

    def _render_robot_arm_cell(self, world: FactoryWorld, arm_state: Optional[Dict[str, Any]]):
        """Renders 4-DOF robot arm workstation, links, gripper, and safety enclosure."""
        surf = self.surface
        bx, by = ROBOT_BASE_POS

        fence_r = 58
        pygame.draw.circle(surf, (220, 180, 20), (bx, by), fence_r, 1)
        lbl_fence = self.font_small.render("ARM CELL DANGER ZONE", True, (160, 140, 40))
        surf.blit(lbl_fence, (bx - lbl_fence.get_width() // 2, by + fence_r + 4))

        pygame.draw.circle(surf, COLOR_ARM_BASE, (bx, by), 24)
        pygame.draw.circle(surf, (40, 44, 50), (bx, by), 24, 2)
        pygame.draw.circle(surf, (100, 105, 115), (bx, by), 16)

        theta_base = arm_state.get("theta_base", -math.pi / 2.0) if arm_state else -math.pi / 2.0
        theta_elbow = arm_state.get("theta_elbow", -0.4) if arm_state else -0.4

        l1_len = 38.0
        p1 = (bx + l1_len * math.cos(theta_base), by + l1_len * math.sin(theta_base))
        pygame.draw.line(surf, COLOR_ARM_LINK_1, (bx, by), p1, 8)
        pygame.draw.circle(surf, (50, 54, 62), (int(p1[0]), int(p1[1])), 6)

        l2_angle = theta_base + theta_elbow
        l2_len = 34.0
        p2 = (p1[0] + l2_len * math.cos(l2_angle), p1[1] + l2_len * math.sin(l2_angle))
        pygame.draw.line(surf, COLOR_ARM_LINK_2, p1, p2, 6)
        pygame.draw.circle(surf, (50, 54, 62), (int(p2[0]), int(p2[1])), 5)

        grip_closed = arm_state.get("gripper_closed", False) if arm_state else False
        grip_span = 4 if grip_closed else 10
        perp_angle = l2_angle + math.pi / 2.0
        g1 = (p2[0] + grip_span * math.cos(perp_angle), p2[1] + grip_span * math.sin(perp_angle))
        g2 = (p2[0] - grip_span * math.cos(perp_angle), p2[1] - grip_span * math.sin(perp_angle))
        pygame.draw.line(surf, COLOR_ARM_GRIPPER, p2, g1, 3)
        pygame.draw.line(surf, COLOR_ARM_GRIPPER, p2, g2, 3)

        held_cube = arm_state.get("held_cube") if arm_state else None
        if held_cube:
            if hasattr(held_cube, "position"):
                try:
                    held_cube.position[0] = p2[0]
                    held_cube.position[1] = p2[1]
                except (TypeError, IndexError):
                    held_cube.position = (p2[0], p2[1])
            self._render_cube(held_cube)

    def _render_vehicle(self, world: FactoryWorld, telemetry: Optional[Dict[str, Any]]):
        """Renders autonomous vehicle with steerable wheels, headlights cone, and cargo bed."""
        surf = self.surface
        veh = world.vehicle
        cx, cy = veh.x, veh.y
        heading = veh.heading
        steer = veh.steering_angle

        veh_len = 54.0
        veh_wid = 32.0
        cos_h = math.cos(heading)
        sin_h = math.sin(heading)

        # 1. RealSense Camera Vision Frustum Cone (86 deg FOV)
        fov_rad = math.radians(86.0)
        cone_len = 140.0
        p_cam = (cx + (veh_len / 2.0) * cos_h, cy + (veh_len / 2.0) * sin_h)
        cone_left = (
            p_cam[0] + cone_len * math.cos(heading - fov_rad / 2.0),
            p_cam[1] + cone_len * math.sin(heading - fov_rad / 2.0),
        )
        cone_right = (
            p_cam[0] + cone_len * math.cos(heading + fov_rad / 2.0),
            p_cam[1] + cone_len * math.sin(heading + fov_rad / 2.0),
        )
        frustum_surf = pygame.Surface((ARENA_WIDTH, ARENA_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(
            frustum_surf,
            (40, 200, 255, 32),
            [(int(p_cam[0]), int(p_cam[1])), (int(cone_left[0]), int(cone_left[1])), (int(cone_right[0]), int(cone_right[1]))],
        )
        surf.blit(frustum_surf, (0, 0))

        # 2. Chassis 4 Corners
        half_l = veh_len / 2.0
        half_w = veh_wid / 2.0
        corners_local = [
            (half_l, -half_w),
            (half_l, half_w),
            (-half_l, half_w),
            (-half_l, -half_w),
        ]
        corners_world = []
        for lx, ly in corners_local:
            wx = cx + lx * cos_h - ly * sin_h
            wy = cy + lx * sin_h + ly * cos_h
            corners_world.append((int(wx), int(wy)))

        # 3. 4 Wheels
        wheel_w, wheel_l = 5, 12
        wheel_mounts = [
            (half_l - 6, -half_w - 2, True),
            (half_l - 6, half_w + 2, True),
            (-half_l + 8, -half_w - 2, False),
            (-half_l + 8, half_w + 2, False),
        ]
        for mx, my, is_front in wheel_mounts:
            w_head = heading + (steer if is_front else 0.0)
            wx = cx + mx * cos_h - my * sin_h
            wy = cy + mx * sin_h + my * cos_h
            w_cos = math.cos(w_head)
            w_sin = math.sin(w_head)
            w_pts = [
                (wx + (wheel_l / 2) * w_cos - (wheel_w / 2) * w_sin, wy + (wheel_l / 2) * w_sin + (wheel_w / 2) * w_cos),
                (wx + (wheel_l / 2) * w_cos + (wheel_w / 2) * w_sin, wy + (wheel_l / 2) * w_sin - (wheel_w / 2) * w_cos),
                (wx - (wheel_l / 2) * w_cos + (wheel_w / 2) * w_sin, wy - (wheel_l / 2) * w_sin - (wheel_w / 2) * w_cos),
                (wx - (wheel_l / 2) * w_cos - (wheel_w / 2) * w_sin, wy - (wheel_l / 2) * w_sin + (wheel_w / 2) * w_cos),
            ]
            pygame.draw.polygon(surf, COLOR_VEHICLE_WHEEL, [(int(p[0]), int(p[1])) for p in w_pts])

        # 4. Main Body Chassis
        pygame.draw.polygon(surf, COLOR_VEHICLE_BODY, corners_world)
        pygame.draw.polygon(surf, (20, 40, 80), corners_world, 2)

        # Cabin
        cabin_pts = [
            (cx + (half_l - 12) * cos_h - (half_w - 5) * sin_h, cy + (half_l - 12) * sin_h + (half_w - 5) * cos_h),
            (cx + (half_l - 12) * cos_h + (half_w - 5) * sin_h, cy + (half_l - 12) * sin_h - (half_w - 5) * cos_h),
            (cx + 4 * cos_h + (half_w - 5) * sin_h, cy + 4 * sin_h - (half_w - 5) * cos_h),
            (cx + 4 * cos_h - (half_w - 5) * sin_h, cy + 4 * sin_h + (half_w - 5) * cos_h),
        ]
        pygame.draw.polygon(surf, COLOR_VEHICLE_ROOF, [(int(p[0]), int(p[1])) for p in cabin_pts])

        # Cargo Bed at Rear
        bed_pts = [
            (cx - 2 * cos_h - (half_w - 4) * sin_h, cy - 2 * sin_h + (half_w - 4) * cos_h),
            (cx - 2 * cos_h + (half_w - 4) * sin_h, cy - 2 * sin_h - (half_w - 4) * cos_h),
            (cx - (half_l - 3) * cos_h + (half_w - 4) * sin_h, cy - (half_l - 3) * sin_h - (half_w - 4) * cos_h),
            (cx - (half_l - 3) * cos_h - (half_w - 4) * sin_h, cy - (half_l - 3) * sin_h + (half_w - 4) * cos_h),
        ]
        pygame.draw.polygon(surf, COLOR_VEHICLE_BED, [(int(p[0]), int(p[1])) for p in bed_pts])
        pygame.draw.polygon(surf, (80, 85, 95), [(int(p[0]), int(p[1])) for p in bed_pts], 1)

        # 5. Render Carried Cube on Bed
        if veh.loaded_cube:
            self._render_cube(veh.loaded_cube)

        # 6. Twin Front Headlights
        hl_left = (cx + half_l * cos_h - (half_w - 6) * sin_h, cy + half_l * sin_h + (half_w - 6) * cos_h)
        hl_right = (cx + half_l * cos_h + (half_w - 6) * sin_h, cy + half_l * sin_h - (half_w - 6) * cos_h)
        pygame.draw.circle(surf, COLOR_VEHICLE_HEADLIGHT, (int(hl_left[0]), int(hl_left[1])), 3)
        pygame.draw.circle(surf, COLOR_VEHICLE_HEADLIGHT, (int(hl_right[0]), int(hl_right[1])), 3)

    def _render_hud_annotations(self, world: FactoryWorld):
        """Draws coordinate scale ruler and simulation status badges."""
        surf = self.surface

        # Metric scale bar (1.0 meter = 100 pixels)
        bar_x, bar_y = 20, ARENA_HEIGHT - 30
        pygame.draw.line(surf, (60, 65, 75), (bar_x, bar_y), (bar_x + 100, bar_y), 3)
        pygame.draw.line(surf, (60, 65, 75), (bar_x, bar_y - 4), (bar_x, bar_y + 4), 2)
        pygame.draw.line(surf, (60, 65, 75), (bar_x + 100, bar_y - 4), (bar_x + 100, bar_y + 4), 2)
        txt_scale = self.font_small.render("1.0 m (100 px)", True, (100, 105, 115))
        surf.blit(txt_scale, (bar_x + 12, bar_y - 18))

        # Vehicle HUD telemetry pill
        veh = world.vehicle
        v_spd_m_s = (veh.speed * 0.01)
        v_steer_deg = math.degrees(veh.steering_angle)
        status_txt = f"POSE: ({veh.x:.1f}, {veh.y:.1f}) | SPEED: {v_spd_m_s:.2f} m/s | STEER: {v_steer_deg:+.1f}° | STATE: {veh.driving_state.value}"
        badge = self.font_small.render(status_txt, True, (240, 245, 255))
        badge_bg = pygame.Rect(180, ARENA_HEIGHT - 35, badge.get_width() + 16, 22)
        pygame.draw.rect(surf, (25, 28, 35), badge_bg, border_radius=4)
        pygame.draw.rect(surf, (60, 65, 75), badge_bg, 1, border_radius=4)
        surf.blit(badge, (badge_bg.x + 8, badge_bg.y + 4))
