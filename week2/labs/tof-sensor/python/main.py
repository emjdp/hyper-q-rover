"""Q-ROVER 2차시 / 실습 2 : MCU가 보낸 거리값 받기

스케치의 Bridge.notify("distance", ...) 가 아래 on_distance() 를 호출한다.
스케치에서 그 줄의 주석을 해제해야 동작한다.
"""

from arduino.app_utils import *


def on_distance(distance_mm: int):
    if distance_mm < 0:
        # -1 은 "너무 멀다"는 뜻이다. "너무 가깝다"가 아니다.
        print("distance_mm=out of range", flush=True)
    else:
        print(f"distance_mm={distance_mm}", flush=True)


# 내 함수를 "distance" 라는 이름으로 등록한다.
# 이 문자열이 스케치의 Bridge.notify("distance", ...) 와 정확히 같아야 한다.
Bridge.provide("distance", on_distance)

App.run()
