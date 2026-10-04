"""Q-ROVER 3차시 / P제어 - MPU(Linux) 쪽 기초 코드

하는 일
    카메라 → 팀 물체 박스 → 조향 오차(-100 ~ +100) → MCU로
    바퀴를 얼마나 돌릴지(P제어)는 MCU(sketch.ino)가 정합니다.

이 상태로도 실행은 됩니다. steer_error()가 늘 0을 돌려주니 오차도 늘 0입니다.
여러분이 할 것 : ★ 설정 2곳 + ★ 미션 ①   (자료 STEP 6 · 7)
"""

import time
from datetime import datetime, UTC

from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection


# ★ 설정 - labels.txt에 적은 팀 물체 이름. 글자 하나까지 같게 (2차시 TODO ③과 같은 함정)
TARGET_LABEL = "???"

# ★ 설정 - 박스 좌표계의 화면 폭. STEP 5-3에서 잰 값 (416 또는 640)
FRAME_W = 416

START_DELAY = 3.0      # 앱을 켜고 이 시간 동안은 "안 보임"으로 보냄 (그동안 로버에서 손 떼기)
HOLD_SEC = 0.5         # 마지막으로 본 뒤 이 시간까지는 "보이는 중" (2차시 TODO ④)
HEARTBEAT_SEC = 0.3    # 바뀐 게 없어도 이 주기로 다시 보냄 (MCU watchdog용)
PRINT_BOX = True       # 팀 물체를 볼 때마다 박스와 오차를 로그에 찍음 (steer_error 확인용)


# ══════════════════════════════════════════════════════════
#  ★ 미션 ① 구현하세요 - 박스 → 조향 오차     (자료 STEP 6-2, 명세 7-6)
#
#    입력   box = (x1, y1, x2, y2)     FRAME_W 기준 픽셀
#    출력   정수.  화면 왼쪽 끝 -100 · 가운데 0 · 오른쪽 끝 +100
# ══════════════════════════════════════════════════════════
def steer_error(box):
    return 0


ui = WebUI()
detector = VideoObjectDetection(confidence=0.5, debounce_sec=0.0)

target_box = None      # 팀 물체 박스 - 한 화면에 여러 개면 가장 큰 것
target_t = 0.0         # 팀 물체를 마지막으로 본 시각
start_t = time.time()
last_sent, last_sent_t = None, 0.0
frames, last_fps_t = 0, time.time()


def area(box):
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


# ── 카메라 : 검출이 있는 프레임마다 ──────────────────────
#    콜백은 기록만 하고 바로 끝냅니다. MCU로 보내는 건 loop()가 합니다. (2차시와 같음)
def on_detections(detections: dict):
    global target_box, target_t, frames
    frames += 1
    items = detections.get(TARGET_LABEL)
    if items:
        target_box = max(items, key=lambda it: area(it["bounding_box_xyxy"]))["bounding_box_xyxy"]
        target_t = time.time()
        if PRINT_BOX:
            print(f"BOX,{target_box},err={steer_error(target_box)}", flush=True)

    for label, its in detections.items():          # 웹 화면 검출 목록 (2차시 그대로)
        for it in its:
            ui.send_message("detection", message={
                "content": label,
                "confidence": it["confidence"],
                "timestamp": datetime.now(UTC).isoformat(),
            })

detector.on_detect_all(on_detections)

# 브라우저 슬라이더 → 모델의 confidence 임계값
ui.on_message("override_th", lambda sid, th: detector.override_threshold(th))


# ── MCU : 거리 · 보임 · 오차 · 바퀴 값 보고 (10 Hz) ────────
#    TLM 줄을 grep으로 모으면 STEP 8의 그래프가 됩니다.
def on_telemetry(dist: int, seen: int, err: int, left: int, right: int):
    ui.send_message("distance", message={"distance_mm": dist})
    ui.send_message("steer", message={"seen": seen, "err": err, "left": left, "right": right})
    print(f"TLM,{time.time():.2f},{seen},{err},{dist},{left},{right}", flush=True)

Bridge.provide("telemetry", on_telemetry)


# ── 주기 루프 (10 Hz) : 오차 → MCU ────────────────────────
def loop():
    global last_sent, last_sent_t, frames, last_fps_t
    now = time.time()

    seen = (now - start_t >= START_DELAY
            and target_box is not None
            and now - target_t < HOLD_SEC)
    err = max(-100, min(100, int(steer_error(target_box)))) if seen else 0
    cmd = (int(seen), err)

    # 바뀌었을 때 + HEARTBEAT_SEC마다 보냅니다.
    # 2차시처럼 바뀔 때만 보내면, 목표가 가만히 가운데 있는 동안 아무 말이 없어서
    # MCU의 watchdog이 "Python이 죽었다"고 보고 멈춥니다.
    if cmd != last_sent or now - last_sent_t >= HEARTBEAT_SEC:
        Bridge.notify("set_target", cmd[0], cmd[1])
        last_sent, last_sent_t = cmd, now

    if now - last_fps_t >= 5:
        print(f"FPS={frames / (now - last_fps_t):.1f}  (검출이 있었던 프레임/초)", flush=True)
        frames, last_fps_t = 0, now

    time.sleep(0.1)


App.run(user_loop=loop)
