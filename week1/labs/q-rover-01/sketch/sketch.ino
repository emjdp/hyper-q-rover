// =====================================================
//  Q-ROVER 1차시 : DRV8833으로 바퀴 굴리기
//  보드 : Arduino UNO Q (Zephyr core)
// =====================================================

//#include "Arduino_RouterBridge.h"   // App Lab 콘솔(Monitor)을 쓰기 위해 필요
                                    // 리눅스와 통신하는 Bridge는 2차시부터 씁니다

// DRV8833은 핀 4개로 모터 2개를 굴린다.
// 한 모터당 2핀(IN1/IN2)을 쓰고, 네 핀 모두에서 PWM이 나가야 한다.
// UNO Q에서 analogWrite()가 되는 핀은 3, 5, 6, 9 — 딱 네 개다.
const int AIN1 = 5;   // 왼쪽 모터
const int AIN2 = 3;
const int BIN1 = 6;   // 오른쪽 모터
const int BIN2 = 9;
// 방향이 안맞으면 핀 번호끼리 바꿔보기!

const int SPEED = 100;   // 0 ~ 255

// -----------------------------------------------------
// 바퀴 하나 굴리기
//   speed > 0 : 앞으로
//   speed < 0 : 뒤로
//   speed = 0 : 힘 빼기 (coast)
// -----------------------------------------------------
void wheel(int in1, int in2, int speed) {
  speed = constrain(speed, -255, 255);

  if (speed > 0) {
    analogWrite(in1, 255);
    analogWrite(in2, 255 - speed);   // 반전 PWM (slow decay) — 슬라이드 12 참고
  } else if (speed < 0) {
    analogWrite(in2, 255);
    analogWrite(in1, 255 + speed);
  } else {
    analogWrite(in1, 0);
    analogWrite(in2, 0);
  }
}

// 양쪽 바퀴를 한 번에
void drive(int left, int right) {
  wheel(AIN1, AIN2, left);
  wheel(BIN1, BIN2, right);
}

// 힘 빼기 (그대로 굴러감)
void coast() {
  drive(0, 0);
}

// 급제동 : 네 핀 모두 HIGH
void brake() {
  analogWrite(AIN1, 255);
  analogWrite(AIN2, 255);
  analogWrite(BIN1, 255);
  analogWrite(BIN2, 255);
  delay(100);
  coast();
}

// 멈춰 있던 바퀴는 정지 마찰 때문에 낮은 PWM으로 출발하지 못한다.
// 출발 순간에만 잠깐 최대 출력으로 툭 쳐준다.
int kickOf(int v) {
  return (v > 0) ? 255 : ((v < 0) ? -255 : 0);
}

void startDrive(int left, int right) {
  drive(kickOf(left), kickOf(right));
  delay(120);
  drive(left, right);
}

void setup() {
  Monitor.begin(115200);
  
  coast();
  delay(1000);

  Monitor.println("Q-ROVER ready");
}

void loop() {

  // 1) 전진 1초
  startDrive(SPEED, SPEED);
  delay(1000);

  // 2) 급정지
  brake();
  delay(1000);

  // =====================================================
  // 3) TODO : 제자리에서 한 바퀴 돌기
  //
  //    힌트 - 왼쪽과 오른쪽을 서로 반대 방향으로 돌리면
  //           로버는 제자리에서 회전한다.
  //
  //    startDrive( ???, ??? );
  //    delay( ??? );     // 한 바퀴가 되는 시간을 직접 찾으세요
  // =====================================================

  brake();
  delay(2000);
}