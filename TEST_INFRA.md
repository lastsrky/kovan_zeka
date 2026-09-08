# E2E Test Infra: TEKNOFEST 2026 Akıllı Fabrika Digital Twin SITL Simulator

## Test Philosophy
- Opaque-box, requirement-driven. Derived from `ORIGINAL_REQUEST.md` without dependency on internal private implementation details.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.
- Target Directory: `simulator/tests/`

## Feature Inventory Mapping
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | 2D Arena & Factory Layout | R1 | 5 | 5 | ✓ | ✓ |
| 2 | Virtual Arm RealSense Camera | R1, R3 | 5 | 5 | ✓ | ✓ |
| 3 | Virtual Vehicle RealSense D455 | R1, R4 | 5 | 5 | ✓ | ✓ |
| 4 | Dual OpenCV Camera HUD Viewports | R1 | 5 | 5 | ✓ | ✓ |
| 5 | S7-1200 Discrete State Machine | R2 | 5 | 5 | ✓ | ✓ |
| 6 | Stack Signal Tower Logic | R2 | 5 | 5 | ✓ | ✓ |
| 7 | Conveyor Belt Mechanics & Sensors | R2 | 5 | 5 | ✓ | ✓ |
| 8 | E-Stop Safety Freeze & Reset | R2, AC | 5 | 5 | ✓ | ✓ |
| 9 | Industrial HMI Pushbuttons | R1 | 5 | 5 | ✓ | ✓ |
| 10 | HMI Telemetry & Event Log | R1 | 5 | 5 | ✓ | ✓ |
| 11 | Classical HSV Color Detection | R3 | 5 | 5 | ✓ | ✓ |
| 12 | Color Confidence & Occupancy | R3 | 5 | 5 | ✓ | ✓ |
| 13 | 4-DOF Robot Arm Kinematics | R3 | 5 | 5 | ✓ | ✓ |
| 14 | Robot Arm State Machine | R3 | 5 | 5 | ✓ | ✓ |
| 15 | PLC Hardware Trigger A5 Emulation | R2, R3 | 5 | 5 | ✓ | ✓ |
| 16 | Embedded MQTT Broker & Bridge | R3 | 5 | 5 | ✓ | ✓ |
| 17 | Autonomous Vehicle Kinematics | R4 | 5 | 5 | ✓ | ✓ |
| 18 | Vision Lane Detection & Tracking | R4 | 5 | 5 | ✓ | ✓ |
| 19 | Traffic Sign & Pedestrian Stop | R4 | 5 | 5 | ✓ | ✓ |
| 20 | MQTT Color Subscription & Auto-Start | R4 | 5 | 5 | ✓ | ✓ |
| 21 | Ground Color Parking Bay Detection | R4 | 5 | 5 | ✓ | ✓ |
| 22 | Precision Bay Stop & Cycle Terminus | R4 | 5 | 5 | ✓ | ✓ |
| 23 | Single-Command Application Launcher | AC | 5 | 5 | ✓ | ✓ |
| 24 | Headless CI Multi-Color Verification | AC | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `simulator/tests/test_runner.py`
  - Command: `python run_simulator.py --headless --verify-all` or `python -m unittest discover -s simulator/tests`
  - Pass/Fail: Exit code 0 if all tests pass; JSON report generated at `.agents/e2e_test_report.json`.
- Test Directory Layout:
  - `simulator/tests/test_tier1_features.py`: Feature coverage (unit & component isolation)
  - `simulator/tests/test_tier2_boundaries.py`: Boundary and corner cases (empty belt, zero velocity, bad MQTT payloads, rapid E-stops)
  - `simulator/tests/test_tier3_pairwise.py`: Pairwise cross-feature interactions (PLC + Arm, Arm + MQTT, MQTT + Vehicle, E-stop + all states)
  - `simulator/tests/test_tier4_applications.py`: Full end-to-end automated multi-color production runs (RED, GREEN, BLUE) + mid-cycle E-stop injection and recovery

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|---|---|---|
| 1 | Automated Red Cube Production Cycle | F1, F2, F5, F6, F7, F11, F13, F14, F15, F16, F17, F18, F20, F21, F22 | Full cycle: Conveyor -> Exit -> Arm -> MQTT RED -> Car drives -> Red Bay Stop |
| 2 | Automated Green Cube Production Cycle | F1, F2, F5, F6, F7, F11, F13, F14, F15, F16, F17, F18, F20, F21, F22 | Full cycle: Conveyor -> Exit -> Arm -> MQTT GREEN -> Car drives -> Green Bay Stop |
| 3 | Automated Blue Cube Production Cycle | F1, F2, F5, F6, F7, F11, F13, F14, F15, F16, F17, F18, F20, F21, F22 | Full cycle: Conveyor -> Exit -> Arm -> MQTT BLUE -> Car drives -> Blue Bay Stop |
| 4 | Conveyor Mid-Transit E-Stop Freeze & Recovery | F5, F6, F7, F8, F9 | Instant belt halt within 1 frame (<16ms), latching, START blocked, Reset clears fault |
| 5 | Vehicle In-Transit E-Stop Freeze & Resume | F8, F17, F18, F22 | Vehicle cuts motor immediately on E-Stop, maintains heading upon Reset |
| 6 | Pedestrian Crossing Detection & Stop | F18, F19, F17 | Vehicle detects pedestrian sign/stripes, stops 3.0s, proceeds through crossing |
| 7 | Full 3-Cube Sequential Batch Production | All Features | Continuous batch execution of RED, GREEN, BLUE in one continuous session |

## Coverage Goals
- Tier 1: $\ge 5$ per feature ($24 \times 5 = 120$ test assertions)
- Tier 2: $\ge 5$ boundary/corner cases per feature area ($24 \times 5 = 120$ test assertions)
- Tier 3: $\ge 24$ pairwise interaction tests
- Tier 4: $\ge 7$ realistic end-to-end application scenarios
