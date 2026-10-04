// MIN_PWM 찾기 - 로버를 바닥에 놓고 실행. 1초마다 PWM을 5씩 올립니다.
//   1) FWD  : 두 바퀴 앞으로        → 처음 굴러가는 값 = 직진 MIN_PWM
//   2) SPIN : 왼쪽 앞, 오른쪽 뒤로  → 처음 도는 값    = 제자리 회전 MIN_PWM (보통 더 큼)
// 시리얼 모니터(arduino-app-cli monitor) 숫자를 보다가 처음 움직이는 값 + 5를 적으세요.
#include <Arduino_RouterBridge.h>

const int AIN1 = 5, AIN2 = 3, BIN1 = 6, BIN2 = 9;

void wheel(int in1, int in2, int speed) {
  speed = constrain(speed, -255, 255);
  if (speed > 0)      { analogWrite(in1, 255); analogWrite(in2, 255 - speed); }
  else if (speed < 0) { analogWrite(in2, 255); analogWrite(in1, 255 + speed); }
  else                { analogWrite(in1, 0);   analogWrite(in2, 0); }
}
void drive(int l, int r) { wheel(AIN1, AIN2, l); wheel(BIN1, BIN2, r); }
void coast() { drive(0, 0); }

void ramp(const char *name, int dirL, int dirR) {
  Monitor.println(name);
  for (int p = 30; p <= 160; p += 5) {
    Monitor.println(p);
    drive(dirL * p, dirR * p);
    delay(1000);
  }
  coast();
  delay(3000);
}

void setup() {
  Bridge.begin();
  Monitor.begin(115200);
  coast();
  delay(3000);
}

void loop() {
  ramp("FWD", 1, 1);
  ramp("SPIN", 1, -1);
  delay(5000);
}
