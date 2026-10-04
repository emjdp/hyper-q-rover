// =====================================================
//  Q-ROVER 3차시 / P제어 - MCU 쪽 기초 코드
//  보드 : Arduino UNO Q (Zephyr core)
//
//  Python이 보내 주는 조향 오차(-100 ~ +100)를 보고
//  목표가 화면 가운데에 오도록 방향을 틀며 다가갑니다.
//
//  이미 들어 있는 것 : 모터(1차시) · 거리센서(2차시) · 명령 받기 · 안전장치 2개
//  여러분이 할 것   : ★ 미션 ② ③ + 튜닝 값   (자료 STEP 6 · 7 · 8)
//  이 상태로도 업로드·실행은 됩니다. 바퀴만 안 돕니다.
// =====================================================

#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <Arduino_RouterBridge.h>

// 바퀴 두 개 값을 한 번에 돌려주려고 묶은 것.
// 함수보다 먼저 적어 둬야 합니다 (Arduino가 함수 선언을 맨 위 함수 앞에 자동으로 끼워 넣기 때문).
struct Wheels {
  int left;    // -255 ~ 255, + = 앞으로
  int right;
};

// ─────────────────────────────────────────────────────
//  1차시 그대로 : 모터
// ─────────────────────────────────────────────────────
const int AIN1 = 5;   // 왼쪽 모터
const int AIN2 = 3;
const int BIN1 = 6;   // 오른쪽 모터
const int BIN2 = 9;

void wheel(int in1, int in2, int speed) {
  speed = constrain(speed, -255, 255);
  if (speed > 0) {
    analogWrite(in1, 255);
    analogWrite(in2, 255 - speed);   // 반전 PWM (slow decay)
  } else if (speed < 0) {
    analogWrite(in2, 255);
    analogWrite(in1, 255 + speed);
  } else {
    analogWrite(in1, 0);
    analogWrite(in2, 0);
  }
}

void drive(int left, int right) {
  wheel(AIN1, AIN2, left);
  wheel(BIN1, BIN2, right);
}

void coast() {
  drive(0, 0);
}

void brake() {
  analogWrite(AIN1, 255);
  analogWrite(AIN2, 255);
  analogWrite(BIN1, 255);
  analogWrite(BIN2, 255);
  delay(100);
  coast();
}

// 멈춰 있던 바퀴는 정지 마찰 때문에 낮은 PWM으로 출발하지 못한다.
int kickOf(int v) {
  return (v > 0) ? 255 : ((v < 0) ? -255 : 0);
}

void startDrive(int left, int right) {
  drive(kickOf(left), kickOf(right));
  delay(120);
  drive(left, right);
}

// ─────────────────────────────────────────────────────
//  3차시 : 튜닝하는 값
// ─────────────────────────────────────────────────────
const int BASE_PWM   = 90;    // 목표를 향해 갈 때 기본 전진 속도   ← STEP 8-1
const float KP_STEER = 0.2;   // 조향 오차 1당 좌우 PWM 차이       ← STEP 8-2에서 바꿔 가며 실험
const int MAX_TURN   = 40;    // 좌우 차이 상한                     ← STEP 8-1
const int STOP_MM    = 150;   // 목표 앞 이 거리에서 멈춤           ← ★ 미션 ③

// ─────────────────────────────────────────────────────
//  안전장치 - 고치지 않아도 됩니다
// ─────────────────────────────────────────────────────
const int EMERGENCY_MM = 80;              // 무엇을 하든 앞 8cm 안에 뭔가 있으면 정지
const unsigned long WATCHDOG_MS = 1000;   // Python 명령이 1초 넘게 끊기면 정지

Adafruit_VL53L0X distanceSensor;

// Python이 Bridge.notify("set_target", seen, err) 로 부르는 함수
// volatile - loop()와 다른 스레드에서 바뀌는 변수 (2차시와 같은 이유)
volatile int cmdSeen = 0;                 // 1 = 목표 보임 · 0 = 안 보임
volatile int cmdErr = 0;                  // -100(화면 왼쪽 끝) ~ 0(가운데) ~ +100(오른쪽 끝)
volatile unsigned long lastCmdMs = 0;

void set_target(int seen, int err) {
  cmdSeen = seen;
  cmdErr = err;
  lastCmdMs = millis();
}


// ══════════════════════════════════════════════════════════
//  ★ 미션 ② 구현하세요 - 조향 오차 → 좌우 바퀴       (자료 STEP 6-3 ~ 6-5, 명세 7-6)
//
//    입력   err   -100 ~ +100   (+ = 목표가 화면 오른쪽)
//    출력   {왼쪽, 오른쪽}   -255 ~ 255   (+ = 앞으로)
//
//    들어가야 하는 것
//      · 비례     오차에 KP_STEER를 곱한 만큼 좌우 바퀴에 차이를 둔다
//      · 방향     목표가 오른쪽이면 오른쪽으로 꺾인다
//      · 상한     좌우 차이는 MAX_TURN을 넘지 않는다
//      · 전진     BASE_PWM으로 앞으로 가면서 꺾는다
// ══════════════════════════════════════════════════════════
Wheels steerToWheels(int err) {
  return {0, 0};   // ← 지금은 항상 정지
}


// 바퀴 값이 바뀌는 순간에만 brake() / startDrive() (2차시 wasMoving과 같은 이유)
int prevL = 0, prevR = 0;

void setWheels(int l, int r) {
  bool wasStopped = (prevL == 0 && prevR == 0);
  bool stopNow = (l == 0 && r == 0);
  if (stopNow) {
    if (!wasStopped) brake();
  } else if (wasStopped) {
    startDrive(l, r);
  } else {
    drive(l, r);
  }
  prevL = l;
  prevR = r;
}

unsigned long lastTlmMs = 0;


void setup() {
  Monitor.begin(115200);
  Bridge.begin();

  // 이 문자열이 main.py의 Bridge.notify("set_target", ...)와 정확히 같아야 한다
  Bridge.provide("set_target", set_target);

  Wire.begin();
  Wire.setClock(100000);   // 400kHz에서는 begin()이 실패한다
  delay(200);

  while (!distanceSensor.begin(0x29, false, &Wire)) {
    Monitor.println("VL53L0X not found - check wiring");
    delay(1000);
  }

  coast();
  delay(1000);
  Monitor.println("Q-ROVER 03 ready");
}


void loop() {
  VL53L0X_RangingMeasurementData_t m;
  distanceSensor.rangingTest(&m, false);
  int distance_mm = (m.RangeStatus != 4) ? m.RangeMilliMeter : -1;   // -1 = 범위 밖

  // 안전장치 ① watchdog - 마지막 명령이 WATCHDOG_MS보다 오래됐으면 "안 보임"으로 본다
  bool fresh = (millis() - lastCmdMs) < WATCHDOG_MS;
  int seen = fresh ? cmdSeen : 0;
  int err = cmdErr;

  Wheels w = {0, 0};               // 목표가 안 보이면 정지
  if (seen) {
    w = steerToWheels(err);
  }

  // ══════════════════════════════════════════════════════
  //  ★ 미션 ③ - 목표 앞 STOP_MM에서 멈추기       (자료 명세 7-6, 2차시 TODO ①)
  //     지금은 아래 비상정지(80mm)에 와서야 멈춥니다.
  // ══════════════════════════════════════════════════════


  // 안전장치 ② 비상정지 - 위에서 무엇을 정했든 앞 EMERGENCY_MM 안에 뭔가 있으면 정지
  if (distance_mm >= 0 && distance_mm < EMERGENCY_MM) {
    w = {0, 0};
  }

  w.left = constrain(w.left, -255, 255);
  w.right = constrain(w.right, -255, 255);
  setWheels(w.left, w.right);

  if (millis() - lastTlmMs >= 100) {   // 10 Hz로 Python에 보고 → 웹 화면 · 로그 · 그래프
    lastTlmMs = millis();
    Bridge.notify("telemetry", distance_mm, seen, err, w.left, w.right);
  }

  delay(20);
}
