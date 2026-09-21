// =====================================================
//  Q-ROVER 2차시 / 실습 1·2 : VL53L0X 거리 센서
//  보드 : Arduino UNO Q (Zephyr core)
//
//  실습 1 - 시리얼 모니터에 거리값 출력
//  실습 2 - 맨 아래 Bridge.notify 주석을 풀어서 Python으로 전달
// =====================================================

#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <Arduino_RouterBridge.h>

Adafruit_VL53L0X distanceSensor;

void setup() {
  Monitor.begin();  // 시리얼 모니터 출력
  Bridge.begin();   // MPU(Python)와의 통신

  Wire.begin();
  Wire.setClock(100000);  // 400kHz에서는 begin()이 실패한다. 100kHz로 낮출 것.
  delay(200);             // 센서 부팅 대기

  // I2C 주소 0x29 = VL53L0X의 공장 출하 주소
  while (!distanceSensor.begin(0x29, false, &Wire)) {
    Monitor.println("VL53L0X not found - check wiring");
    delay(1000);
  }
  Monitor.println("VL53L0X ready");
}

void loop() {
  VL53L0X_RangingMeasurementData_t measurement;
  distanceSensor.rangingTest(&measurement, false);

  // RangeStatus 4 = 측정 범위 밖
  // (이때 RangeMilliMeter는 8191 같은 쓰레기값이 나오므로 반드시 걸러야 한다)
  int distance_mm = -1;
  if (measurement.RangeStatus != 4) {
    distance_mm = measurement.RangeMilliMeter;
  }

  // ─── 실습 1 : 시리얼 모니터로만 확인 ───
  if (distance_mm < 0) {
    Monitor.println("out of range");
  } else {
    Monitor.print("distance_mm=");
    Monitor.println(distance_mm);
  }

  // ─── 실습 2 : 아래 한 줄의 주석을 해제 ───
  // Python(main.py)의 on_distance()가 호출된다.
  // Bridge.notify("distance", distance_mm);

  delay(100);  // 약 10 Hz
}
