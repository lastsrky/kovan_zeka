/*
 * Robot kolun Arduino firmware'i - kolu fiziksel olarak hareket ettiren kod.
 *
 * Arduino'ya yuklenir (Jetson bu dosyayi okumaz). Step motorlari, limit
 * switch'leri, gripper servosunu ve acil durdurmayi yonetir.
 *
 * Jetson ile seri protokol (robot_link.py ile birebir eslesir):
 *   Jetson -> Arduino : PING | S spd accel | D mask | H mask | C s0..s3
 *                       M s0..s3 | J j1 delta | G angle | P | R | X
 *   Arduino -> Jetson : STA s0 s1 s2 s3 grip moving homed limits basla (~50ms)
 *                       EVT MOVE_DONE | HOME_DONE | HOME_FAIL <j> | ESTOP
 *                       OK <komut> | ERR <aciklama> | READY | PONG
 *
 * Eklem sirasi: 0=Taban 1=Omuz 2=Dirsek 3=Bilek
 * Pin haritasi asagidaki #define satirlarindadir.
 */

#include <AccelStepper.h>
#include <Servo.h>


#define PUL_BASE      2
#define DIR_BASE      3
#define PUL_SHOULDER  4
#define DIR_SHOULDER  5
#define PUL_ELBOW     6
#define DIR_ELBOW     7
#define PUL_WRIST     8
#define DIR_WRIST     9

#define SERVO_PIN     A1

#define SW_BASE       A0
#define SW_SHOULDER   11
#define SW_ELBOW      12
#define SW_WRIST      13

#define SINYAL_PIN    A5


AccelStepper stepBase    (AccelStepper::DRIVER, PUL_BASE,     DIR_BASE);
AccelStepper stepShoulder(AccelStepper::DRIVER, PUL_SHOULDER, DIR_SHOULDER);
AccelStepper stepElbow   (AccelStepper::DRIVER, PUL_ELBOW,    DIR_ELBOW);
AccelStepper stepWrist   (AccelStepper::DRIVER, PUL_WRIST,    DIR_WRIST);

AccelStepper* steppers[4] = { &stepBase, &stepShoulder, &stepElbow, &stepWrist };
const int     swPins[4]   = { SW_BASE,   SW_SHOULDER,   SW_ELBOW,   SW_WRIST   };

Servo gripper;


int      homingDir[4] = { -1, +1, -1, +1 };
uint8_t  homedMask    = 0;

bool     isMoving     = false;
bool     isHoming     = false;
bool     isPaused     = false;
bool     estop        = false;

int      gripperAngle = 0;

unsigned long lastStaTime = 0;
const  unsigned long STA_INTERVAL_MS = 50;

String inLine;


bool anyStepperBusy() {
  for (int i = 0; i < 4; i++) if (steppers[i]->distanceToGo() != 0) return true;
  return false;
}


bool readSwitchDebounced(int pin) {
  int low_count = 0;
  for (int k = 0; k < 5; k++) {
    if (digitalRead(pin) == LOW) low_count++;
    delayMicroseconds(120);
  }
  return low_count >= 3;
}

uint8_t readLimitsMask() {
  uint8_t m = 0;
  for (int i = 0; i < 4; i++) {
    if (readSwitchDebounced(swPins[i])) m |= (1 << i);
  }
  return m;
}


uint8_t readBaslaSinyali() {
  return readSwitchDebounced(SINYAL_PIN) ? 1 : 0;
}

void sendStatus() {
  Serial.print(F("STA "));
  for (int i = 0; i < 4; i++) {
    Serial.print(steppers[i]->currentPosition());
    Serial.print(' ');
  }
  Serial.print(gripperAngle); Serial.print(' ');
  Serial.print((isMoving || isHoming) ? 1 : 0); Serial.print(' ');
  Serial.print(homedMask); Serial.print(' ');
  Serial.print(readLimitsMask()); Serial.print(' ');
  Serial.println(readBaslaSinyali());
}

void maybeSendStatus() {
  unsigned long now = millis();
  if (now - lastStaTime >= STA_INTERVAL_MS) {
    sendStatus();
    lastStaTime = now;
  }
}

void hardStopAll() {
  for (int i = 0; i < 4; i++) {
    long cur = steppers[i]->currentPosition();
    steppers[i]->setCurrentPosition(cur);
    steppers[i]->moveTo(cur);
  }
}

void doEstop() {
  estop = true;
  isMoving = false;
  isHoming = false;
  hardStopAll();
  Serial.println(F("EVT ESTOP"));
}


bool homingSeriKontrol() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == 'X' || c == 'x') {
      doEstop();
      return true;
    }
  }
  return false;
}


bool parse4Long(const String& body, long out[4]) {
  int idx = 0, start = 0;
  int len = body.length();
  for (int i = 0; i <= len && idx < 4; i++) {
    if (i == len || body.charAt(i) == ' ') {
      if (i == start) return false;
      out[idx++] = body.substring(start, i).toInt();
      start = i + 1;
    }
  }
  return idx == 4;
}


bool homeOneJoint(int j) {
  AccelStepper* st = steppers[j];
  int dir = homingDir[j];
  int sw  = swPins[j];

  st->setMaxSpeed(2000);
  st->setAcceleration(2000);


  if (readSwitchDebounced(sw)) {
    unsigned long t0 = millis();
    while (readSwitchDebounced(sw)) {
      if (homingSeriKontrol() || estop) return false;
      st->setSpeed(-dir * 300);
      st->runSpeed();
      maybeSendStatus();
      if (millis() - t0 > 3000UL) break;
    }
    delay(100);
  }


  unsigned long t0 = millis();
  float speed = 100.0;
  const float MAX_SPEED = 1500.0;
  const float RAMP_PER_ITER = 6.0;
  while (!readSwitchDebounced(sw)) {
    if (homingSeriKontrol() || estop) return false;
    if (millis() - t0 > 30000UL) return false;
    if (speed < MAX_SPEED) speed += RAMP_PER_ITER;
    st->setSpeed(dir * speed);
    st->runSpeed();
    maybeSendStatus();
  }
  st->setSpeed(0);
  delay(80);


  t0 = millis();
  while (readSwitchDebounced(sw)) {
    if (homingSeriKontrol() || estop) return false;
    if (millis() - t0 > 5000UL) break;
    st->setSpeed(-dir * 250);
    st->runSpeed();
    maybeSendStatus();
  }
  st->setSpeed(0);
  delay(120);


  t0 = millis();
  while (!readSwitchDebounced(sw)) {
    if (homingSeriKontrol() || estop) return false;
    if (millis() - t0 > 5000UL) return false;
    st->setSpeed(dir * 100);
    st->runSpeed();
    maybeSendStatus();
  }
  st->setSpeed(0);

  st->setCurrentPosition(0);
  homedMask |= (1 << j);
  return true;
}

void doHoming(uint8_t mask) {
  isHoming = true;
  isPaused = false;
  estop    = false;


  static const int HOME_ORDER[4] = { 0, 1, 3, 2 };
  int failed = -1;
  for (int k = 0; k < 4; k++) {
    int j = HOME_ORDER[k];
    if (!(mask & (1 << j))) continue;
    if (!homeOneJoint(j)) { failed = j; break; }
  }
  isHoming = false;

  if (failed >= 0) {
    Serial.print(F("EVT HOME_FAIL ")); Serial.println(failed);
  } else {
    Serial.println(F("EVT HOME_DONE"));
  }
}


void handleCommand(const String& cmd) {
  if (cmd.length() == 0) return;

  if (cmd == "PING")  { Serial.println(F("PONG")); return; }


  if (cmd == "X") { doEstop();                       Serial.println(F("OK X")); return; }
  if (cmd == "P") { isPaused = true;                 Serial.println(F("OK P")); return; }
  if (cmd == "R") { isPaused = false; estop = false; Serial.println(F("OK R")); return; }

  if (estop) {
    Serial.print(F("ERR ESTOP_ACTIVE: ")); Serial.println(cmd);
    return;
  }


  if (cmd.startsWith("S ")) {
    int sp = cmd.indexOf(' ', 2);
    if (sp < 0) { Serial.println(F("ERR S_FORMAT")); return; }
    long spd   = cmd.substring(2, sp).toInt();
    long accel = cmd.substring(sp + 1).toInt();
    if (spd <= 0)   spd   = 1;
    if (accel <= 0) accel = 1;
    for (int i = 0; i < 4; i++) {
      steppers[i]->setMaxSpeed((float)spd);
      steppers[i]->setAcceleration((float)accel);
    }
    Serial.println(F("OK S"));
    return;
  }


  if (cmd.startsWith("D ")) {
    uint8_t mask = (uint8_t)cmd.substring(2).toInt();
    for (int i = 0; i < 4; i++) homingDir[i] = (mask & (1 << i)) ? +1 : -1;
    Serial.println(F("OK D"));
    return;
  }


  if (cmd.startsWith("C ")) {
    long s[4];
    if (!parse4Long(cmd.substring(2), s)) { Serial.println(F("ERR C_FORMAT")); return; }
    for (int i = 0; i < 4; i++) steppers[i]->setCurrentPosition(s[i]);
    Serial.println(F("OK C"));
    return;
  }


  if (cmd.startsWith("M ")) {
    long s[4];
    if (!parse4Long(cmd.substring(2), s)) { Serial.println(F("ERR M_FORMAT")); return; }
    for (int i = 0; i < 4; i++) steppers[i]->moveTo(s[i]);
    isMoving = true;
    isPaused = false;
    Serial.println(F("OK M"));
    return;
  }


  if (cmd.startsWith("J ")) {
    int sp = cmd.indexOf(' ', 2);
    if (sp < 0) { Serial.println(F("ERR J_FORMAT")); return; }
    int  j1    = cmd.substring(2, sp).toInt();
    long delta = cmd.substring(sp + 1).toInt();
    int  j     = j1 - 1;
    if (j < 0 || j > 3) { Serial.println(F("ERR J_RANGE")); return; }
    long target = steppers[j]->currentPosition() + delta;
    steppers[j]->moveTo(target);
    isMoving = true;
    isPaused = false;
    Serial.println(F("OK J"));
    return;
  }


  if (cmd.startsWith("H ")) {
    uint8_t mask = (uint8_t)cmd.substring(2).toInt();
    Serial.println(F("OK H"));
    doHoming(mask);
    return;
  }


  if (cmd.startsWith("G ")) {
    int a = cmd.substring(2).toInt();
    if (a < 0)  a = 0;
    if (a > 74) a = 74;
    gripperAngle = a;
    gripper.write(a);
    Serial.println(F("OK G"));
    return;
  }

  Serial.print(F("ERR UNKNOWN ")); Serial.println(cmd);
}


void setup() {
  Serial.begin(115200);

  for (int i = 0; i < 4; i++) {
    pinMode(swPins[i], INPUT_PULLUP);
    steppers[i]->setMaxSpeed(3000.0);
    steppers[i]->setAcceleration(2000.0);
  }

  pinMode(SINYAL_PIN, INPUT_PULLUP);

  gripper.attach(SERVO_PIN);
  gripper.write(gripperAngle);

  inLine.reserve(64);
  Serial.println(F("READY"));
}

void loop() {

  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (inLine.length() > 0) {
        inLine.trim();
        handleCommand(inLine);
        inLine = "";
      }
    } else {
      inLine += c;
      if (inLine.length() > 200) inLine = "";
    }
  }


  if (isMoving && !isPaused && !estop) {
    for (int i = 0; i < 4; i++) steppers[i]->run();
    if (!anyStepperBusy()) {
      isMoving = false;
      Serial.println(F("EVT MOVE_DONE"));
    }
  }


  maybeSendStatus();
}
