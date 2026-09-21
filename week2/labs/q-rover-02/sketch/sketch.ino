// =====================================================
//  Q-ROVER 2차시 / 통합 미션
//  보드 : Arduino UNO Q (Zephyr core)
//
//  직진하다가 -
//    (가) 앞 20cm 안에 뭔가 있으면 정지        ← 거리센서, MCU가 판단
//    (나) 카메라에 bottle 이 보이면 정지        ← AI, MPU(Python)가 판단
//    치우면 다시 출발
//
//  채울 곳 : TODO ① , TODO ②      (아래로 스크롤)
// =====================================================

#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <Arduino_RouterBridge.h>

// ─────────────────────────────────────────────────────
//  1차시 그대로 : 모터
// ─────────────────────────────────────────────────────
const int AIN1 = 5;   // 왼쪽 모터
const int AIN2 = 3;
const int BIN1 = 6;   // 오른쪽 모터
const int BIN2 = 9;

const int SPEED = 100;   // 0 ~ 255

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
//  2차시 신규 : 거리센서 + MPU와의 통신
// ─────────────────────────────────────────────────────
Adafruit_VL53L0X distanceSensor;

const int STOP_MM = 200;   // 20 cm 안에 뭔가 있으면 장애물로 본다

// MPU(Python)가 내려주는 판단.
// volatile - set_vision_block()은 loop()와 "다른 스레드"에서 실행되기 때문에,
//            이게 없으면 컴파일러가 "이 변수 안 변하네" 하고 최적화로 날려버릴 수 있다.
volatile bool visionBlocked = false;

// Python이 Bridge.notify("set_vision_block", ...) 로 이 함수를 호출한다.
void set_vision_block(bool blocked) {
  visionBlocked = blocked;
}

// 지금 굴러가고 있나? (상태가 바뀌는 순간에만 brake()/startDrive()를 부르려고 둔다)
bool wasMoving = false;


void setup() {
  Monitor.begin(115200);
  Bridge.begin();

  // 내 함수를 "set_vision_block" 이라는 이름으로 등록한다.
  // 이 문자열이 Python 쪽과 정확히 같아야 한다.  ← RPC에서 제일 많이 나는 실수
  Bridge.provide("set_vision_block", set_vision_block);

  Wire.begin();
  Wire.setClock(100000);   // 400kHz에서는 begin()이 실패한다
  delay(200);

  while (!distanceSensor.begin(0x29, false, &Wire)) {
    Monitor.println("VL53L0X not found - check wiring");
    delay(1000);
  }

  coast();
  delay(1000);
  Monitor.println("Q-ROVER ready");
}


void loop() {
  VL53L0X_RangingMeasurementData_t m;
  distanceSensor.rangingTest(&m, false);

  // RangeStatus 4 = 측정 범위 밖  →  -1
  int distance_mm = (m.RangeStatus != 4) ? m.RangeMilliMeter : -1;

  // 거리값은 화면에 뿌리라고 Python으로도 보낸다
  Bridge.notify("distance", distance_mm);

  // ══════════════════════════════════════════════════════════
  //  TODO ① : 거리센서가 "막혔다"고 볼 조건은?
  //
  //    힌트 - distance_mm 가 -1 이면 "너무 멀다"는 뜻입니다.
  //           그건 막힌 게 아닙니다.
  //
  //    bool tofBlocked = ( ??? ) && ( ??? );
  //    정지 거리는 위에서 정의 해둔 STOP_MM 를 사용하면 됩니다. 현재 거리는 distance_mm
  // ══════════════════════════════════════════════════════════
  bool tofBlocked = false;   // ← 고치세요

  // ══════════════════════════════════════════════════════════
  //  TODO ② : 최종 판단. 둘 중 하나라도 막혔으면 정지.
  //    or 기호는 || 위에 코드를 보고 뭐가 들어갈지 생각해보면 됩니다.
  //
  //    bool blocked = ??? ;
  // ══════════════════════════════════════════════════════════
  bool blocked = false;      // ← 고치세요


  // 상태가 바뀌는 순간에만 brake() / startDrive() 를 부른다.
  // (brake() 안에는 delay(100)이 있어서 매 루프마다 부르면 센서를 제때 못 읽는다)
  if (blocked) {
    if (wasMoving) {
      brake();
      wasMoving = false;
    }
  } else {
    if (!wasMoving) {
      startDrive(SPEED, SPEED);
      wasMoving = true;
    } else {
      drive(SPEED, SPEED);
    }
  }

  delay(50);   // 20 Hz
}
