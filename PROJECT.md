# Project: TEKNOFEST 2026 Mesleki Yetenek Yarışması Akıllı Fabrika Digital Twin (SITL) Simulator

## Architecture
The simulator is a full-featured Software-in-the-Loop (SITL) digital twin modeling the entire smart factory cell:
- **Factory World & Physics (`simulator/core/factory_world.py`)**: 2D continuous space ($10.4\text{ m} \times 9.0\text{ m}$) hosting conveyor belt, optical sensors, signal tower, 4-DOF robot arm cell, 2-lane track circuit, traffic signs, vehicle docking bay, and 3 ground color parking bays.
- **Virtual RealSense Sensors (`simulator/core/virtual_cameras.py`)**:
  - Arm Overhead Camera ($640 \times 480$ BGR) focused on conveyor exit pick zone with classical HSV detection compatibility.
  - Vehicle Perspective Camera ($640 \times 480$ BGR + aligned 16-bit Depth $Z16$) with projective geometry rendering lanes, zebra stripes, signs, and parking floor bays.
- **PLC & Conveyor Engine (`simulator/core/plc_engine.py`)**: Exact cyclic scan S7-1200 state machine handling 7 digital inputs (%I0.0-%I0.6), 6 digital outputs (%Q0.0-%Q0.5), Green/Red/Amber stack tower lamps, optical beam-break sensors, and hardware-equivalent E-Stop safety latching.
- **Robot Arm Cell & MQTT Bridge (`simulator/core/robot_arm_sim.py`, `simulator/core/color_detector_sim.py`, `simulator/core/mqtt_broker.py`)**:
  - 4-DOF kinematics and 8-state sequence (`HOME` -> `GORME` -> `BASLA_BEK` -> `RENK` -> `AL` -> `DOGRULA` -> `YUKLE` -> `GONDER`).
  - Strict classical HSV thresholding matching `renk_algila.py` and `renk_kalibrasyon.json` without deep learning.
  - Embedded MQTT broker on port 1883 with topic publication `arac/yuk` (`RED`/`GREEN`/`BLUE`) and `robot/basla`.
- **Autonomous Vehicle Engine (`simulator/core/vehicle_sim.py`)**:
  - Ackerman steering physics, speed governor, PID lane tracking ($75^\circ-145^\circ$), pedestrian sign response, and closed-loop proportional color parking bay alignment.
- **Pygame 2D Factory & HMI GUI (`simulator/gui/renderer.py`, `simulator/gui/hmi_panel.py`)**:
  - $1600 \times 900$ viewport displaying $1040 \times 900$ birds-eye factory floor, dual real-time OpenCV camera streams ($270 \times 202$ scaled), tactile buttons (START, STOP, E-STOP, RESET, ADD CUBE RED/GREEN/BLUE), stack lights, and telemetry.
- **Single-Command & Headless CI Launcher (`run_simulator.py`, `simulator/sim_app.py`)**:
  - Launches interactive GUI or headless automated verification (`--headless --verify-all`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | 2D Arena & Factory Layout | $1600 \times 900$ Pygame window, $1040 \times 900$ factory arena, conveyor, arm cell, track, signs, bays | M1 | R1, explorer_survey_3 |
| 2 | Virtual Arm RealSense Camera | Overhead $640 \times 480$ BGR camera rendering conveyor exit with calibrated RGB cube textures and noise | M1 | R1, R3, explorer_survey_3 |
| 3 | Virtual Vehicle RealSense D455 | Perspective $640 \times 480$ BGR + aligned 16-bit depth ($Z16$) rendering lanes, zebra crossing, signs, bays | M1 | R1, R4, spec_miner_survey_1 |
| 4 | Dual OpenCV Camera HUD Viewports | Top-right camera panels with ROI overlays, HSV detection status, and vehicle vision telemetry | M1 | R1, explorer_survey_3 |
| 5 | S7-1200 Discrete State Machine | Deterministic cyclic scan (%I0.0-%I0.6, %Q0.0-%Q0.5), states OFF, READY, FEEDING, EXIT_STOPPED, TRIGGER_ROBOT | M2 | R2, explorer_survey_3 |
| 6 | Stack Signal Tower Logic | Green lamp on belt moving, Red lamp on exit stop / idle, Amber blinking on warning/E-stop | M2 | R2, explorer_survey_3 |
| 7 | Conveyor Belt Mechanics & Sensors | $800\text{ mm}$ belt, $80\text{ mm/s}$ travel, entry optical sensor S1, exit optical sensor S2 | M2 | R2, explorer_survey_3 |
| 8 | E-Stop Safety Freeze & Reset | State 99 immediate motor cutoff, actuator freeze within 1 frame, latched until E-Stop release + RESET | M2 | R2, Acceptance Criteria |
| 9 | Industrial HMI Pushbuttons | START, STOP, E-STOP (mushroom), RESET, ADD RED/GREEN/BLUE CUBE with keyboard shortcuts | M2 | R1, explorer_survey_3 |
| 10 | HMI Telemetry & Event Log | Real-time sensor indicators, cycle counter, color tally, and MQTT event ticker | M2 | R1, explorer_survey_3 |
| 11 | Classical HSV Color Detection | Exact OpenCV HSV dual-band Red, single-band Green/Blue, ROI crop, Gaussian blur, morphological open | M3 | R3, spec_miner_survey_2 |
| 12 | Color Confidence & Occupancy | $0.40$ minimum fill ratio, $0.12$ winner confidence margin, returns UNKNOWN if ambiguous | M3 | R3, spec_miner_survey_2 |
| 13 | 4-DOF Robot Arm Kinematics | Base, Shoulder, Elbow, Wrist, RC servo gripper, waypoints GORME, AL, YUKLE, GECIS | M3 | R3, spec_miner_survey_2 |
| 14 | Robot Arm State Machine | States HOME, GORME, BASLA_BEK, RENK, AL, DOGRULA, YUKLE, GONDER with 3-stage clearance trajectory | M3 | R3, spec_miner_survey_2 |
| 15 | PLC Hardware Trigger A5 Emulation | Evaluates PLC trigger signal to start robot pick sequence upon conveyor exit stop | M3 | R2, R3, spec_miner_survey_2 |
| 16 | Embedded MQTT Broker & Bridge | Embedded port 1883 broker, publishes `arac/yuk` (`RED`/`GREEN`/`BLUE`), `robot/basla`, `robot/veri` | M3 | R3, spec_miner_survey_2 |
| 17 | Autonomous Vehicle Kinematics | 2D kinematic bicycle model, speed control, servo steering angle $[75^\circ, 145^\circ]$ (center $110^\circ$) | M4 | R4, spec_miner_survey_1 |
| 18 | Vision Lane Detection & Tracking | Binary thresholding, vertical morphology $(3, 55)$, polynomial fit, target lookahead, PID steering | M4 | R4, spec_miner_survey_1 |
| 19 | Traffic Sign & Pedestrian Stop | Pedestrian crossing sign detection, 3.0 s stop, blind pass, speed governor | M4 | R4, spec_miner_survey_1 |
| 20 | MQTT Color Subscription & Auto-Start | Subscribes to `arac/yuk` and `robot/basla`, requires color + start to launch autonomous navigation | M4 | R4, spec_miner_survey_1 |
| 21 | Ground Color Parking Bay Detection | HSV segmentation of parking floor, $A \ge 300$, depth $[25, 350]\text{ cm}$, proportional bay steering | M4 | R4, spec_miner_survey_1 |
| 22 | Precision Bay Stop & Cycle Terminus | Stops when distance $\le 25\text{ cm}$ inside designated color bay, cuts motor permanently (ETTI) | M4 | R4, spec_miner_survey_1 |
| 23 | Single-Command Application Launcher | `python run_simulator.py` launches interactive simulator with all subsystems linked | M5 | Acceptance Criteria |
| 24 | Headless CI Multi-Color Verification | `python run_simulator.py --headless --verify-all` verifying RED, GREEN, BLUE cycles and E-Stop | M5 | Acceptance Criteria |
| 25 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test cases across feature, boundary, pairwise, and application workloads | E2E Track | Project Pattern |
| 26 | Adversarial Coverage Hardening | White-box stress-testing, boundary perturbation, and race condition verification (Tier 5) | M5 Phase 2 | Project Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| E2E | E2E Testing Track | Independent requirement-driven test suite (Tiers 1-4), harness & runner, produces `TEST_READY.md` | none | DONE |
| M1 | Core Simulator Infra & 2D World | 2D factory/track layout, virtual RealSense camera generators (arm overhead + vehicle perspective & depth) | none | DONE |
| M2 | S7-1200 PLC, Conveyor & HMI | PLC state machine, sensors S1/S2/S3, stack lamps, conveyor physics, E-Stop safety freeze/reset, HMI GUI | M1 | DONE |
| M3 | Robot Arm, Classical HSV & MQTT | 4-DOF arm kinematics/sequence, HSV detection, PLC A5 trigger, embedded MQTT broker (`arac/yuk`) | M1, M2 | IN_PROGRESS |
| M4 | Autonomous Vehicle & Parking | Vehicle physics, lane tracking, sign handling, MQTT subscription, color parking bay alignment & stop | M1, M3 | PLANNED |
| M5 | E2E Integration & Verification | Single launcher (`run_simulator.py`), 100% E2E test pass across RED/GREEN/BLUE, E-Stop audit, Tier 5 hardening | M1, M2, M3, M4, E2E | PLANNED |

## Interface Contracts

### M1 World / Cameras ↔ M2 PLC / Conveyor
- `world.conveyor`: `ConveyorBelt(x=120, y=100, length=260, speed=80)` with properties `has_cube_at_entry -> bool`, `has_cube_at_exit -> bool`, `active_cube -> Cube`.
- `plc_engine.update(dt)`: Reads `world.conveyor` sensors, updates internal digital I/O `%I` and `%Q`, controls belt motor `conveyor.is_running = %Q0.0`.

### M2 PLC ↔ M3 Robot Arm
- `plc_engine.robot_trigger (%Q0.4)`: Active-high boolean indicating cube is settled at exit sensor and vehicle is docked.
- `robot_arm_sim.step(dt)`: When in `D_BASLA_BEK`, monitors `plc_engine.robot_trigger == True` to transition into `D_RENK` and `D_AL`.

### M3 Robot Arm / Vision ↔ M1 Virtual Camera
- `virtual_cameras.get_arm_frame() -> np.ndarray (640, 480, 3)`: Top-down BGR image of conveyor exit.
- `color_detector.detect(frame) -> RenkSonuc(renk="RED"|"GREEN"|"BLUE"|"UNKNOWN", confidence=float)` using exact calibrated HSV ranges.

### M3 Robot Arm ↔ M4 Autonomous Vehicle via MQTT
- Topic `arac/yuk`: Payload `"RED"`, `"GREEN"`, or `"BLUE"` (QoS 1).
- Topic `robot/basla`: Payload `"BASLA"` (QoS 1).
- Vehicle `ColorLink`: Transitions to `hazir = True` when both payload color and start command are received.

### M4 Autonomous Vehicle ↔ M1 Virtual Camera
- `virtual_cameras.get_vehicle_frame(pose=(x, y, heading)) -> (np.ndarray(640, 480, 3), np.ndarray(640, 480, uint16))`: Returns perspective BGR frame + aligned millimeter depth array.

### Safety E-Stop Interlock (Global)
- `plc_engine.estop_active`: When `True`, all subsystems (`conveyor.speed = 0`, `robot_arm.freeze()`, `vehicle.estop()`) halt immediately within the current simulation step ($<16\text{ ms}$).

## Code Layout
```
c:\Users\user\OneDrive\Desktop\TEKNOFEST MESLEKİ YETENEK YARIŞMASI-AKILLI FABRİKA\
├── run_simulator.py                    # Root single-command entry point (CLI/GUI/Headless)
├── simulator/
│   ├── __init__.py
│   ├── config.py                       # Global dimensions, coordinates, HSV ranges, MQTT topics
│   ├── core/
│   │   ├── __init__.py
│   │   ├── factory_world.py            # 2D environment, kinematics, conveyor, cube entities
│   │   ├── plc_engine.py               # Siemens S7-1200 discrete state machine, I/O, lamps, safety
│   │   ├── virtual_cameras.py          # Synthetic RealSense D455 BGR + Depth generators
│   │   ├── robot_arm_sim.py            # 4-DOF articulated manipulator, waypoints, pick/place logic
│   │   ├── color_detector_sim.py       # Classical OpenCV HSV detector (matches renk_algila.py)
│   │   ├── vehicle_sim.py              # Autonomous vehicle kinematics, PID lane keep, color parking
│   │   └── mqtt_broker.py              # Lightweight embedded MQTT message broker & client bridge
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── renderer.py                 # Pygame factory arena birds-eye renderer
│   │   ├── camera_view.py              # Dual RealSense OpenCV camera HUD panels
│   │   └── hmi_panel.py                # Industrial HMI buttons, stack tower monitor, telemetry
│   ├── sim_app.py                      # Main application coordinating GUI, physics, and headless modes
│   └── tests/
│       ├── __init__.py
│       ├── test_runner.py              # Opaque-box E2E test runner
│       ├── test_tier1_features.py      # Tier 1: Feature coverage tests (>=5 per feature)
│       ├── test_tier2_boundaries.py    # Tier 2: Boundary & corner cases
│       ├── test_tier3_pairwise.py      # Tier 3: Cross-feature combinations
│       └── test_tier4_applications.py  # Tier 4: Real-world end-to-end multi-color & safety scenarios
```
