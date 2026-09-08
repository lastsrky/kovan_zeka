"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Siemens S7-1200 PLC Discrete State Machine Engine

Models:
- Digital Inputs (%I0.0-%I0.6): START_PB, STOP_PB, ESTOP_PB, RESET_PB, ENTRY_SENSOR, EXIT_SENSOR, VEHICLE_READY
- Digital Outputs (%Q0.0-%Q0.5): CONVEYOR_MOTOR, GREEN_LAMP, RED_LAMP, YELLOW_LAMP, ROBOT_TRIGGER, CYCLE_ACTIVE
- Ladder logic discrete state machine:
    State 0: OFF
    State 1: READY
    State 2: FEEDING (conveyor moving, green lamp on)
    State 3: EXIT_STOPPED (conveyor stopped at exit, red lamp on)
    State 4: TRIGGER_ROBOT (robot trigger asserted to Arduino A5)
    State 5: CYCLE_COMPLETE (cycle counter increment, loop to ready)
    State 99: ESTOP_FREEZE (immediate motor cutoff, frozen until reset)
- E-Stop safety interlock: halts within 1 simulation step (<16ms), latched until release + RESET.
"""

from typing import Optional, Dict, Any
import math

from simulator.config import (
    PLC_ADDR_START_PB,
    PLC_ADDR_STOP_PB,
    PLC_ADDR_ESTOP_PB,
    PLC_ADDR_RESET_PB,
    PLC_ADDR_ENTRY_SENSOR,
    PLC_ADDR_EXIT_SENSOR,
    PLC_ADDR_VEHICLE_READY,
    PLC_ADDR_CONVEYOR_MOTOR,
    PLC_ADDR_GREEN_LAMP,
    PLC_ADDR_RED_LAMP,
    PLC_ADDR_YELLOW_LAMP,
    PLC_ADDR_ROBOT_TRIGGER,
    PLC_ADDR_CYCLE_ACTIVE,
    PLC_CYCLE_TIME_MS,
)

# PLC State Constants
STATE_OFF: int = 0
STATE_READY: int = 1
STATE_FEEDING: int = 2
STATE_EXIT_STOPPED: int = 3
STATE_TRIGGER_ROBOT: int = 4
STATE_CYCLE_COMPLETE: int = 5
STATE_ESTOP_FREEZE: int = 99

STATE_NAMES: Dict[int, str] = {
    STATE_OFF: "OFF",
    STATE_READY: "READY",
    STATE_FEEDING: "FEEDING",
    STATE_EXIT_STOPPED: "EXIT_STOPPED",
    STATE_TRIGGER_ROBOT: "TRIGGER_ROBOT",
    STATE_CYCLE_COMPLETE: "CYCLE_COMPLETE",
    STATE_ESTOP_FREEZE: "ESTOP_FREEZE",
}


class PLCEngine:
    """
    Siemens S7-1200 CPU 1214C DC/DC/DC Emulation Engine.
    Executes deterministic cyclic scan logic modeling 7 digital inputs (%I0.0-%I0.6)
    and 6 digital outputs (%Q0.0-%Q0.5).
    """

    def __init__(self) -> None:
        # Digital Inputs (%I - Process Image Input)
        self.I_START: bool = False           # %I0.0 (START Pushbutton, NO)
        self.I_STOP: bool = False            # %I0.1 (STOP Pushbutton, NC)
        self.I_ESTOP: bool = False           # %I0.2 (E-Stop Mushroom, NC, latched)
        self.I_RESET: bool = False           # %I0.3 (RESET Pushbutton, NO)
        self.I_ENTRY: bool = False           # %I0.4 (Optical Sensor S1 Infeed)
        self.I_EXIT: bool = False            # %I0.5 (Optical Sensor S2 Discharge)
        self.I_VEHICLE_READY: bool = True    # %I0.6 (Proximity Sensor S3 Docked)

        # Digital Outputs (%Q - Process Image Output)
        self.Q_CONVEYOR_MOTOR: bool = False  # %Q0.0 (Belt Drive DC Motor)
        self.Q_GREEN_LAMP: bool = False      # %Q0.1 (Stack Tower Green Light)
        self.Q_RED_LAMP: bool = False        # %Q0.2 (Stack Tower Red Light)
        self.Q_YELLOW_LAMP: bool = False     # %Q0.3 (Stack Tower Amber/Yellow Light)
        self.Q_ROBOT_TRIGGER: bool = False   # %Q0.4 (Arduino A5 / Robot Arm Trigger)
        self.Q_CYCLE_ACTIVE: bool = False    # %Q0.5 (Production Cycle Running Flag)

        # Internal Execution State & Latches
        self.state: int = STATE_OFF
        self.cycle_count: int = 0
        self._estop_latched: bool = False
        self._scan_cycle_time_ms: float = PLC_CYCLE_TIME_MS
        self._total_scan_cycles: int = 0

    # -------------------------------------------------------------------------
    # Public Observable Properties (Interface Contracts)
    # -------------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        """Indicates whether conveyor drive motor (%Q0.0) is active."""
        return self.Q_CONVEYOR_MOTOR

    @property
    def green_lamp(self) -> bool:
        """Stack tower Green signal lamp (%Q0.1)."""
        return self.Q_GREEN_LAMP

    @property
    def red_lamp(self) -> bool:
        """Stack tower Red signal lamp (%Q0.2)."""
        return self.Q_RED_LAMP

    @property
    def yellow_lamp(self) -> bool:
        """Stack tower Amber/Yellow warning signal lamp (%Q0.3)."""
        return self.Q_YELLOW_LAMP

    @property
    def robot_trigger(self) -> bool:
        """Hardware start trigger signal to robot arm (%Q0.4 / Arduino A5)."""
        return self.Q_ROBOT_TRIGGER

    @property
    def cycle_active(self) -> bool:
        """Automated cycle indicator (%Q0.5)."""
        return self.Q_CYCLE_ACTIVE

    @property
    def estop_active(self) -> bool:
        """Safety interlock latch active flag."""
        return self._estop_latched

    @property
    def state_name(self) -> str:
        """Human-readable name of the current PLC state."""
        return STATE_NAMES.get(self.state, f"UNKNOWN({self.state})")

    # -------------------------------------------------------------------------
    # Operator Controls (Pushbuttons & Interlocks)
    # -------------------------------------------------------------------------
    def press_start(self) -> None:
        """Asserts START pushbutton pulse (%I0.0). Ignored if E-Stop is latched."""
        if not self._estop_latched:
            self.I_START = True

    def press_stop(self) -> None:
        """Asserts normal STOP pushbutton pulse (%I0.1)."""
        self.I_STOP = True

    def press_estop(self) -> None:
        """Asserts emergency E-Stop mushroom pushbutton (%I0.2) and latches fault."""
        self.I_ESTOP = True
        self._estop_latched = True

    def release_estop(self) -> None:
        """Releases physical E-Stop pushbutton (%I0.2). Fault remains latched until RESET."""
        self.I_ESTOP = False

    def press_reset(self) -> None:
        """Asserts safety RESET pushbutton pulse (%I0.3)."""
        self.I_RESET = True

    def reset(self) -> None:
        """Full soft reset of the PLC engine to initial OFF state."""
        self.state = STATE_OFF
        self.I_START = False
        self.I_STOP = False
        self.I_ESTOP = False
        self.I_RESET = False
        self.I_ENTRY = False
        self.I_EXIT = False
        self.I_VEHICLE_READY = True
        self.Q_CONVEYOR_MOTOR = False
        self.Q_GREEN_LAMP = False
        self.Q_RED_LAMP = False
        self.Q_YELLOW_LAMP = False
        self.Q_ROBOT_TRIGGER = False
        self.Q_CYCLE_ACTIVE = False
        self._estop_latched = False

    # -------------------------------------------------------------------------
    # Cyclic Scan Cycle (OB1 Execution Loop)
    # -------------------------------------------------------------------------
    def update(self, dt: float, world: Optional[Any] = None) -> None:
        """
        Executes one discrete S7-1200 PLC cyclic scan cycle.

        Phases:
        1. Read physical sensors from factory world into Process Image Input (%I).
        2. Evaluate emergency stop and safety interlocks (priority cutoff <16ms).
        3. Evaluate normal operator stop.
        4. Execute discrete ladder logic state transitions.
        5. Update Process Image Output (%Q).
        6. Write motor outputs to physical factory world.
        """
        self._total_scan_cycles += 1

        # ---------------------------------------------------------------------
        # Phase 1: Read Inputs (%I) from Physical World
        # ---------------------------------------------------------------------
        if world is not None:
            if hasattr(world, "conveyor") and world.conveyor is not None:
                self.I_ENTRY = bool(world.conveyor.has_cube_at_entry)
                self.I_EXIT = bool(world.conveyor.has_cube_at_exit)

            # Check autonomous vehicle dock presence if vehicle is modeled
            if hasattr(world, "vehicle") and world.vehicle is not None and hasattr(world, "dock_pose"):
                dock_x, dock_y = world.dock_pose[0], world.dock_pose[1]
                veh_x, veh_y = world.vehicle.x, world.vehicle.y
                dist = math.hypot(veh_x - dock_x, veh_y - dock_y)
                self.I_VEHICLE_READY = bool(dist <= 35.0)

        # ---------------------------------------------------------------------
        # Phase 2: Safety Interlock Check (E-Stop Priority Cutoff)
        # ---------------------------------------------------------------------
        if self.I_ESTOP or self._estop_latched:
            self.state = STATE_ESTOP_FREEZE
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_YELLOW_LAMP = True  # Amber warning lamp active/flashing
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False

            if world is not None and hasattr(world, "conveyor") and world.conveyor is not None:
                world.conveyor.is_running = False

            # Reset logic: Safety fault only clears when physical button is released
            # AND the RESET pushbutton is pressed.
            if not self.I_ESTOP and self.I_RESET:
                self._estop_latched = False
                self.I_RESET = False
                self.state = STATE_OFF
                self.Q_YELLOW_LAMP = False
            return

        # ---------------------------------------------------------------------
        # Phase 3: Normal Operator STOP Check
        # ---------------------------------------------------------------------
        if self.I_STOP:
            self.state = STATE_OFF
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False
            self.I_STOP = False

            if world is not None and hasattr(world, "conveyor") and world.conveyor is not None:
                world.conveyor.is_running = False
            return

        # ---------------------------------------------------------------------
        # Phase 4: Discrete State Machine Ladder Logic
        # ---------------------------------------------------------------------
        if self.state == STATE_OFF:
            if self.I_START:
                self.I_START = False
                self.state = STATE_READY

        elif self.state == STATE_READY:
            # Transition to FEEDING when cube is detected at entry sensor S1
            if self.I_ENTRY:
                self.state = STATE_FEEDING

        elif self.state == STATE_FEEDING:
            # Exit sensor takes precedence: when cube arrives at exit sensor S2
            if self.I_EXIT:
                self.state = STATE_EXIT_STOPPED

        elif self.state == STATE_EXIT_STOPPED:
            # Transition to TRIGGER_ROBOT when vehicle is docked and ready
            if self.I_VEHICLE_READY:
                self.state = STATE_TRIGGER_ROBOT

        elif self.state == STATE_TRIGGER_ROBOT:
            # Transition to CYCLE_COMPLETE when robot arm picks cube (S2 clears)
            if not self.I_EXIT:
                self.state = STATE_CYCLE_COMPLETE

        elif self.state == STATE_CYCLE_COMPLETE:
            # Register completed production cycle and loop back to READY
            self.cycle_count += 1
            self.state = STATE_READY

        # Clear momentary START pulse if not consumed
        if self.state != STATE_OFF:
            self.I_START = False

        # ---------------------------------------------------------------------
        # Phase 5: Output Evaluation (%Q)
        # ---------------------------------------------------------------------
        if self.state == STATE_OFF:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = False
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = False

        elif self.state == STATE_READY:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True  # Red on ready / idle
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True

        elif self.state == STATE_FEEDING:
            self.Q_CONVEYOR_MOTOR = True
            self.Q_GREEN_LAMP = True  # Green on belt running
            self.Q_RED_LAMP = False
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True

        elif self.state == STATE_EXIT_STOPPED:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True  # Red on exit stop
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True

        elif self.state == STATE_TRIGGER_ROBOT:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = True  # Active high trigger to Arduino A5
            self.Q_CYCLE_ACTIVE = True

        elif self.state == STATE_CYCLE_COMPLETE:
            self.Q_CONVEYOR_MOTOR = False
            self.Q_GREEN_LAMP = False
            self.Q_RED_LAMP = True
            self.Q_YELLOW_LAMP = False
            self.Q_ROBOT_TRIGGER = False
            self.Q_CYCLE_ACTIVE = True

        # ---------------------------------------------------------------------
        # Phase 6: Actuate Physical World
        # ---------------------------------------------------------------------
        if world is not None and hasattr(world, "conveyor") and world.conveyor is not None:
            world.conveyor.is_running = self.Q_CONVEYOR_MOTOR

    # -------------------------------------------------------------------------
    # Diagnostics & Telemetry
    # -------------------------------------------------------------------------
    def get_telemetry(self) -> Dict[str, Any]:
        """Returns structured diagnostic dictionary of all I/O and internal state."""
        return {
            "state": self.state,
            "state_name": self.state_name,
            "cycle_count": self.cycle_count,
            "estop_latched": self._estop_latched,
            "inputs": {
                PLC_ADDR_START_PB: self.I_START,
                PLC_ADDR_STOP_PB: self.I_STOP,
                PLC_ADDR_ESTOP_PB: self.I_ESTOP,
                PLC_ADDR_RESET_PB: self.I_RESET,
                PLC_ADDR_ENTRY_SENSOR: self.I_ENTRY,
                PLC_ADDR_EXIT_SENSOR: self.I_EXIT,
                PLC_ADDR_VEHICLE_READY: self.I_VEHICLE_READY,
            },
            "outputs": {
                PLC_ADDR_CONVEYOR_MOTOR: self.Q_CONVEYOR_MOTOR,
                PLC_ADDR_GREEN_LAMP: self.Q_GREEN_LAMP,
                PLC_ADDR_RED_LAMP: self.Q_RED_LAMP,
                PLC_ADDR_YELLOW_LAMP: self.Q_YELLOW_LAMP,
                PLC_ADDR_ROBOT_TRIGGER: self.Q_ROBOT_TRIGGER,
                PLC_ADDR_CYCLE_ACTIVE: self.Q_CYCLE_ACTIVE,
            },
        }

    def __repr__(self) -> str:
        return (
            f"PLCEngine(state={self.state} ({self.state_name}), "
            f"motor={self.is_running}, green={self.green_lamp}, "
            f"red={self.red_lamp}, trigger={self.robot_trigger}, "
            f"estop={self.estop_active})"
        )
