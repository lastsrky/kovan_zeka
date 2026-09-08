"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Industrial Pygame HMI Control Panel & Live Telemetry

Features:
- Tactile Pushbuttons: START, STOP, E-STOP (Red Mushroom), RESET, ADD CUBE (RED, GREEN, BLUE).
- Keyboard Shortcuts: [Space]/[S], [X]/[Esc], [E], [R], [1]/[2]/[3].
- Stack Signal Tower Visualization: Red, Amber/Yellow, Green circular lamps.
- Telemetry & Annunciators: PLC state, S1/S2/S3 sensor LEDs, production counters, live MQTT log.
- Headless Support: Runs cleanly without display in headless CI mode.
"""

from typing import Optional, Dict, List, Any, Tuple
import os
import pygame

from simulator.config import (
    COLOR_CUBE_RED,
    COLOR_CUBE_GREEN,
    COLOR_CUBE_BLUE,
    COLOR_TOWER_RED_OFF,
    COLOR_TOWER_RED_ON,
    COLOR_TOWER_AMBER_OFF,
    COLOR_TOWER_AMBER_ON,
    COLOR_TOWER_GREEN_OFF,
    COLOR_TOWER_GREEN_ON,
)
from simulator.core.plc_engine import (
    PLCEngine,
    STATE_OFF,
    STATE_READY,
    STATE_FEEDING,
    STATE_EXIT_STOPPED,
    STATE_TRIGGER_ROBOT,
    STATE_CYCLE_COMPLETE,
    STATE_ESTOP_FREEZE,
)


class HMIPanel:
    """
    Industrial Pygame HMI Control Panel and Live Telemetry Display.
    Positioned in the lower-right quadrant of the simulator window (1040, 420, 560, 480).
    """

    def __init__(self, plc: PLCEngine) -> None:
        self.plc: PLCEngine = plc

        # Production Telemetry Counters (F10 Contract)
        self.counters: Dict[str, int] = {
            "total": 0,
            "RED": 0,
            "GREEN": 0,
            "BLUE": 0,
        }

        # Event & MQTT Message Log (F10 Contract)
        self.mqtt_log: List[str] = []

        # Cycle Timing Metrics
        self.cycle_time_s: float = 0.0
        self.last_cycle_time_s: float = 0.0
        self._blink_timer: float = 0.0
        self._blink_on: bool = True

        # Layout Geometry (x=1040, y=420, w=560, h=480)
        self.panel_rect = pygame.Rect(1040, 420, 560, 480)

        # Interactive Button Rectangles (Screen Coordinates)
        self.btn_start = pygame.Rect(1060, 465, 100, 38)
        self.btn_stop = pygame.Rect(1170, 465, 100, 38)
        self.btn_estop = pygame.Rect(1290, 455, 60, 60)   # Mushroom boundary
        self.btn_reset = pygame.Rect(1415, 465, 100, 38)

        self.btn_add_red = pygame.Rect(1060, 516, 135, 30)
        self.btn_add_green = pygame.Rect(1205, 516, 135, 30)
        self.btn_add_blue = pygame.Rect(1350, 516, 135, 30)

        # Lazy Font Cache
        self._fonts_initialized: bool = False
        self._font_title: Optional[pygame.font.Font] = None
        self._font_body: Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None
        self._font_mono: Optional[pygame.font.Font] = None

    # -------------------------------------------------------------------------
    # Public Operator Control Interface (F9 Contract)
    # -------------------------------------------------------------------------
    def press_start(self) -> None:
        """Dispatches START command to PLC engine."""
        self.plc.press_start()

    def press_stop(self) -> None:
        """Dispatches STOP command to PLC engine."""
        self.plc.press_stop()

    def press_estop(self) -> None:
        """Dispatches E-STOP emergency cutoff to PLC engine."""
        self.plc.press_estop()

    def release_estop(self) -> None:
        """Releases physical E-STOP button on PLC engine."""
        self.plc.release_estop()

    def press_reset(self) -> None:
        """Dispatches RESET fault-clearing command to PLC engine."""
        self.plc.press_reset()

    def add_cube(self, world: Any, color: str) -> Any:
        """
        Dispenses a colored cube onto the conveyor infeed and updates counters.
        Raises ValueError if color is not 'RED', 'GREEN', or 'BLUE'.
        """
        color_upper = color.upper()
        if color_upper not in ("RED", "GREEN", "BLUE"):
            raise ValueError(f"Invalid cube color: {color}. Must be RED, GREEN, or BLUE.")

        cube = world.add_cube(color_upper)
        self.counters[color_upper] += 1
        self.counters["total"] += 1
        return cube

    def log_mqtt(self, topic: str, payload: str) -> None:
        """Appends an incoming or outgoing MQTT message to the live event log."""
        entry = f"[{topic}] {payload}"
        self.mqtt_log.append(entry)

    # -------------------------------------------------------------------------
    # Event Handling (Mouse Clicks & Keyboard Shortcuts)
    # -------------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event, world: Optional[Any] = None) -> bool:
        """
        Processes Pygame mouse clicks and keyboard shortcuts.
        Returns True if the event was consumed by the HMI panel.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # START
            if self.btn_start.collidepoint(mx, my):
                self.press_start()
                return True

            # STOP
            if self.btn_stop.collidepoint(mx, my):
                self.press_stop()
                return True

            # E-STOP Mushroom (Circular hit-test)
            ex = self.btn_estop.centerx
            ey = self.btn_estop.centery
            if (mx - ex) ** 2 + (my - ey) ** 2 <= 30 ** 2:
                if self.plc.estop_active and not self.plc.I_ESTOP:
                    # Clicking while latched releases physical button
                    self.release_estop()
                else:
                    self.press_estop()
                return True

            # RESET
            if self.btn_reset.collidepoint(mx, my):
                self.press_reset()
                return True

            # ADD CUBES
            if world is not None:
                if self.btn_add_red.collidepoint(mx, my):
                    self.add_cube(world, "RED")
                    return True
                if self.btn_add_green.collidepoint(mx, my):
                    self.add_cube(world, "GREEN")
                    return True
                if self.btn_add_blue.collidepoint(mx, my):
                    self.add_cube(world, "BLUE")
                    return True

        elif event.type == pygame.KEYDOWN:
            # START: [Space] or [S]
            if event.key in (pygame.K_SPACE, pygame.K_s):
                self.press_start()
                return True

            # STOP: [X] or [Esc]
            elif event.key in (pygame.K_x, pygame.K_ESCAPE):
                self.press_stop()
                return True

            # E-STOP: [E]
            elif event.key == pygame.K_e:
                if self.plc.estop_active and self.plc.I_ESTOP:
                    self.release_estop()
                else:
                    self.press_estop()
                return True

            # RESET: [R]
            elif event.key == pygame.K_r:
                self.press_reset()
                return True

            # ADD CUBE SHORTCUTS: [1]=RED, [2]=GREEN, [3]=BLUE
            elif world is not None:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self.add_cube(world, "RED")
                    return True
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    self.add_cube(world, "GREEN")
                    return True
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    self.add_cube(world, "BLUE")
                    return True

        return False

    # -------------------------------------------------------------------------
    # Font Management (Headless-Safe)
    # -------------------------------------------------------------------------
    def _ensure_fonts(self) -> None:
        if self._fonts_initialized:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            self._font_title = pygame.font.SysFont("Consolas, Courier, monospace", 13, bold=True)
            self._font_body = pygame.font.SysFont("Consolas, Courier, monospace", 11, bold=True)
            self._font_small = pygame.font.SysFont("Consolas, Courier, monospace", 10)
            self._font_mono = pygame.font.SysFont("Consolas, Courier, monospace", 10)
            self._fonts_initialized = True
        except Exception:
            self._fonts_initialized = False

    # -------------------------------------------------------------------------
    # Visual Pygame Rendering Pipeline
    # -------------------------------------------------------------------------
    def render(self, surface: pygame.Surface, world: Optional[Any] = None, dt: float = 0.016) -> None:
        """
        Renders the industrial HMI control panel, signal tower, telemetry, and live log.
        Safe for both interactive Pygame windows and headless off-screen buffers.
        """
        self._ensure_fonts()

        # Update blink animation timer (for warnings and E-Stop)
        self._blink_timer += dt
        if self._blink_timer >= 0.4:
            self._blink_timer = 0.0
            self._blink_on = not self._blink_on

        # Update production cycle timer
        if self.plc.is_running:
            self.cycle_time_s += dt
        elif self.plc.state == STATE_CYCLE_COMPLETE:
            if self.cycle_time_s > 0.0:
                self.last_cycle_time_s = self.cycle_time_s
                self.cycle_time_s = 0.0

        # ---------------------------------------------------------------------
        # 1. Panel Background & Bezel
        # ---------------------------------------------------------------------
        pygame.draw.rect(surface, (26, 29, 36), self.panel_rect)
        pygame.draw.rect(surface, (60, 66, 78), self.panel_rect, width=2)

        # Header Title Bar
        header_rect = pygame.Rect(1040, 420, 560, 32)
        pygame.draw.rect(surface, (36, 42, 54), header_rect)
        pygame.draw.line(surface, (70, 78, 92), (1040, 452), (1600, 452), 1)

        if self._font_title:
            title_surf = self._font_title.render(
                "SIEMENS S7-1200 HMI OPERATOR PANEL", True, (220, 228, 240)
            )
            surface.blit(title_surf, (1055, 428))

            # Cycle count header tag
            cyc_txt = self._font_title.render(f"CYCLE: {self.plc.cycle_count}", True, (80, 200, 120))
            surface.blit(cyc_txt, (1500, 428))

        # ---------------------------------------------------------------------
        # 2. Tactile Pushbuttons
        # ---------------------------------------------------------------------
        # START Button (Green)
        start_bg = (35, 160, 65) if not self.plc.estop_active else (40, 60, 45)
        pygame.draw.rect(surface, start_bg, self.btn_start, border_radius=4)
        pygame.draw.rect(surface, (60, 220, 100) if not self.plc.estop_active else (60, 80, 65), self.btn_start, width=2, border_radius=4)
        if self._font_body:
            lbl = self._font_body.render("START [S]", True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(center=self.btn_start.center))

        # STOP Button (Dark Gray/Red tone)
        stop_bg = (70, 75, 85)
        pygame.draw.rect(surface, stop_bg, self.btn_stop, border_radius=4)
        pygame.draw.rect(surface, (120, 125, 135), self.btn_stop, width=2, border_radius=4)
        if self._font_body:
            lbl = self._font_body.render("STOP [X]", True, (240, 240, 240))
            surface.blit(lbl, lbl.get_rect(center=self.btn_stop.center))

        # E-STOP Mushroom Button
        ex = self.btn_estop.centerx
        ey = self.btn_estop.centery
        # Yellow safety ring base
        pygame.draw.circle(surface, (230, 190, 20), (ex, ey), 28)
        pygame.draw.circle(surface, (100, 80, 10), (ex, ey), 28, width=2)
        # Red mushroom cap
        estop_color = (225, 30, 35)
        if self.plc.estop_active and self._blink_on:
            estop_color = (255, 70, 70)
            pygame.draw.circle(surface, (255, 50, 50), (ex, ey), 32, width=3)
        pygame.draw.circle(surface, estop_color, (ex, ey), 22)
        pygame.draw.circle(surface, (120, 15, 20), (ex, ey), 22, width=2)
        if self._font_small:
            lbl = self._font_small.render("E-STOP", True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(center=(ex, ey)))

        # RESET Button (Yellow / Amber)
        reset_bg = (210, 160, 20)
        pygame.draw.rect(surface, reset_bg, self.btn_reset, border_radius=4)
        pygame.draw.rect(surface, (255, 210, 50), self.btn_reset, width=2, border_radius=4)
        if self._font_body:
            lbl = self._font_body.render("RESET [R]", True, (15, 15, 15))
            surface.blit(lbl, lbl.get_rect(center=self.btn_reset.center))

        # Add Cube Buttons
        for btn, col_rgb, text in [
            (self.btn_add_red, (200, 25, 30), "+ RED [1]"),
            (self.btn_add_green, (25, 160, 45), "+ GREEN [2]"),
            (self.btn_add_blue, (25, 90, 200), "+ BLUE [3]"),
        ]:
            pygame.draw.rect(surface, col_rgb, btn, border_radius=4)
            pygame.draw.rect(surface, (220, 230, 240), btn, width=1, border_radius=4)
            if self._font_small:
                lbl = self._font_small.render(text, True, (255, 255, 255))
                surface.blit(lbl, lbl.get_rect(center=btn.center))

        # ---------------------------------------------------------------------
        # 3. Stack Signal Tower Visualization
        # ---------------------------------------------------------------------
        tower_x = 1060
        tower_y = 560
        tower_w = 64
        tower_h = 136
        pygame.draw.rect(surface, (18, 20, 24), (tower_x, tower_y, tower_w, tower_h), border_radius=4)
        pygame.draw.rect(surface, (50, 56, 68), (tower_x, tower_y, tower_w, tower_h), width=2, border_radius=4)

        # Red Lamp
        red_on = self.plc.red_lamp
        r_col = COLOR_TOWER_RED_ON if red_on else COLOR_TOWER_RED_OFF
        pygame.draw.circle(surface, r_col, (tower_x + 32, tower_y + 24), 14)
        if red_on:
            pygame.draw.circle(surface, (255, 100, 100), (tower_x + 32, tower_y + 24), 18, width=2)
        pygame.draw.circle(surface, (80, 30, 30), (tower_x + 32, tower_y + 24), 14, width=1)

        # Yellow / Amber Lamp (blinks on E-Stop)
        yellow_on = self.plc.yellow_lamp and (self._blink_on or not self.plc.estop_active)
        y_col = COLOR_TOWER_AMBER_ON if yellow_on else COLOR_TOWER_AMBER_OFF
        pygame.draw.circle(surface, y_col, (tower_x + 32, tower_y + 68), 14)
        if yellow_on:
            pygame.draw.circle(surface, (255, 220, 100), (tower_x + 32, tower_y + 68), 18, width=2)
        pygame.draw.circle(surface, (80, 70, 20), (tower_x + 32, tower_y + 68), 14, width=1)

        # Green Lamp
        green_on = self.plc.green_lamp
        g_col = COLOR_TOWER_GREEN_ON if green_on else COLOR_TOWER_GREEN_OFF
        pygame.draw.circle(surface, g_col, (tower_x + 32, tower_y + 112), 14)
        if green_on:
            pygame.draw.circle(surface, (100, 255, 120), (tower_x + 32, tower_y + 112), 18, width=2)
        pygame.draw.circle(surface, (20, 80, 30), (tower_x + 32, tower_y + 112), 14, width=1)

        # ---------------------------------------------------------------------
        # 4. Telemetry & Sensor Annunciators
        # ---------------------------------------------------------------------
        telem_x = 1140
        telem_y = 560
        telem_w = 440
        telem_h = 136
        pygame.draw.rect(surface, (20, 23, 29), (telem_x, telem_y, telem_w, telem_h), border_radius=4)
        pygame.draw.rect(surface, (45, 52, 64), (telem_x, telem_y, telem_w, telem_h), width=1, border_radius=4)

        if self._font_body:
            # PLC State Annunciator Badge
            st_name = self.plc.state_name
            if self.plc.state == STATE_ESTOP_FREEZE:
                st_color = (255, 50, 50)
            elif self.plc.state == STATE_FEEDING:
                st_color = (50, 220, 100)
            elif self.plc.state in (STATE_READY, STATE_EXIT_STOPPED):
                st_color = (240, 180, 50)
            else:
                st_color = (180, 190, 205)

            st_surf = self._font_body.render(f"PLC STATE: {self.plc.state} ({st_name})", True, st_color)
            surface.blit(st_surf, (telem_x + 12, telem_y + 10))

            # Sensor LEDs (%I)
            sensors = [
                ("S1 (Infeed)", self.plc.I_ENTRY),
                ("S2 (Exit)", self.plc.I_EXIT),
                ("S3 (Dock)", self.plc.I_VEHICLE_READY),
            ]
            led_x = telem_x + 12
            led_y = telem_y + 36
            for s_name, s_active in sensors:
                led_col = (40, 220, 80) if s_active else (50, 55, 65)
                pygame.draw.circle(surface, led_col, (led_x + 5, led_y + 6), 5)
                lbl = self._font_small.render(s_name, True, (200, 205, 215) if s_active else (110, 115, 125))
                surface.blit(lbl, (led_x + 15, led_y))
                led_x += 140

            # Actuator LEDs (%Q)
            actuators = [
                ("Motor (%Q0.0)", self.plc.is_running),
                ("Robot Trg (%Q0.4)", self.plc.robot_trigger),
                ("Cycle (%Q0.5)", self.plc.cycle_active),
            ]
            led_x = telem_x + 12
            led_y = telem_y + 58
            for a_name, a_active in actuators:
                led_col = (40, 180, 240) if a_active else (50, 55, 65)
                pygame.draw.circle(surface, led_col, (led_x + 5, led_y + 6), 5)
                lbl = self._font_small.render(a_name, True, (200, 220, 240) if a_active else (110, 115, 125))
                surface.blit(lbl, (led_x + 15, led_y))
                led_x += 140

            # Production Counters Line
            c_txt = (
                f"TOTAL: {self.counters['total']}  |  "
                f"RED: {self.counters['RED']}  |  "
                f"GREEN: {self.counters['GREEN']}  |  "
                f"BLUE: {self.counters['BLUE']}"
            )
            c_surf = self._font_small.render(c_txt, True, (220, 225, 235))
            surface.blit(c_surf, (telem_x + 12, telem_y + 86))

            # Timing line
            t_txt = f"ACTIVE TIME: {self.cycle_time_s:.1f}s   LAST CYCLE: {self.last_cycle_time_s:.1f}s"
            t_surf = self._font_small.render(t_txt, True, (160, 170, 185))
            surface.blit(t_surf, (telem_x + 12, telem_y + 110))

        # ---------------------------------------------------------------------
        # 5. Live MQTT & System Event Log
        # ---------------------------------------------------------------------
        log_x = 1060
        log_y = 712
        log_w = 520
        log_h = 172
        pygame.draw.rect(surface, (14, 16, 20), (log_x, log_y, log_w, log_h), border_radius=4)
        pygame.draw.rect(surface, (40, 46, 56), (log_x, log_y, log_w, log_h), width=1, border_radius=4)

        if self._font_small:
            log_title = self._font_small.render("LIVE EVENT & MQTT TICKER", True, (130, 140, 160))
            surface.blit(log_title, (log_x + 10, log_y + 6))
            pygame.draw.line(surface, (30, 35, 45), (log_x + 10, log_y + 22), (log_x + log_w - 10, log_y + 22), 1)

            # Show last 7 entries
            recent_logs = self.mqtt_log[-7:] if self.mqtt_log else ["[SYSTEM] Simulator operational. Ready for input."]
            line_y = log_y + 28
            for entry in recent_logs:
                # Clip long text
                display_entry = entry if len(entry) <= 68 else entry[:65] + "..."
                col = (80, 210, 140) if "arac/yuk" in entry else ((100, 180, 240) if "robot" in entry else (180, 190, 200))
                msg_surf = self._font_mono.render(display_entry, True, col)
                surface.blit(msg_surf, (log_x + 12, line_y))
                line_y += 19

    def __repr__(self) -> str:
        return (
            f"HMIPanel(total={self.counters['total']}, "
            f"red={self.counters['RED']}, green={self.counters['GREEN']}, "
            f"blue={self.counters['BLUE']}, log_count={len(self.mqtt_log)})"
        )
