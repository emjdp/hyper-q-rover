"""Q-ROVER 2차시 / 통합 미션 - MPU(Linux) 쪽

역할 분담
    MCU  : 거리 읽기(20Hz) → 자기가 판단 → 즉시 정지      [빠르고 확실]
    MPU  : 영상 추론(수 Hz) → bottle 있나? → true/false만  [느리고 똑똑]
    MCU  : (거리로 막힘) OR (영상으로 막힘) → 최종 정지

    안전에 관한 판단은 가장 단순하고 가장 확실한 쪽(MCU)에 둔다.
    와이파이가 끊겨도 벽에는 안 박아야 하니까.

채울 곳 : TODO ③ , TODO ④
"""

import time
from datetime import datetime, UTC

from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection


# ══════════════════════════════════════════════════════════
#  TODO ③ : COCO 80종 중 어떤 라벨을 감시할까?
#
#    힌트 - 03-object-detection/README.md 의 COCO 목록을 보세요.
#           대소문자까지 정확히 같아야 합니다.
# ══════════════════════════════════════════════════════════
WATCH_LABEL = "???"        # ← 고치세요


# ══════════════════════════════════════════════════════════
#  TODO ④ : 마지막으로 본 지 몇 초까지 "아직 있다"고 볼까?
#
#    이 브릭에는 "사라졌다"는 콜백이 없습니다.
#    병이 치워지면 그냥 아무 연락이 없습니다.
#    그래서 "마지막으로 본 시각"으로부터 얼마나 지났는지로 판단합니다.
#
#    너무 짧으면 → 한 프레임 놓칠 때마다 로버가 덜컥거림
#    너무 길면   → 병을 치웠는데 한참 서 있음
#    직접 굴려보면서 찾으세요. 1차시에 delay 값 찾던 것과 같습니다.
# ══════════════════════════════════════════════════════════
HOLD_SEC = 0.0             # ← 고치세요


ui = WebUI()
detector = VideoObjectDetection(confidence=0.5, debounce_sec=0.0)

last_seen = 0.0            # 감시 대상을 마지막으로 본 시각
vision_blocked = False     # 지금 MCU에 알려 둔 상태


# ── 카메라 : 감시 대상을 봤을 때 ──────────────────────────
def on_target(detection: dict):
    # detection = {"confidence": 0.87, "bounding_box_xyxy": (x1, y1, x2, y2)}
    global last_seen
    last_seen = time.time()          # 본 시각만 기록하고 바로 끝낸다

detector.on_detect(WATCH_LABEL, on_target)


# ── 카메라 : 모든 검출을 웹 화면으로 ─────────────────────
def send_to_ui(detections: dict):
    # detections = {"bottle": [{"confidence": .., "bounding_box_xyxy": ..}], ...}
    for label, items in detections.items():
        for it in items:
            ui.send_message("detection", message={
                "content": label,
                "confidence": it.get("confidence"),
                "timestamp": datetime.now(UTC).isoformat(),
            })

detector.on_detect_all(send_to_ui)

# 브라우저 슬라이더 → 모델의 confidence 임계값
ui.on_message("override_th", lambda sid, th: detector.override_threshold(th))


# ── MCU가 보내주는 거리값 → 웹 화면으로 ──────────────────
def on_distance(distance_mm: int):
    ui.send_message("distance", message={"distance_mm": distance_mm})

Bridge.provide("distance", on_distance)


# ── 주기 루프 : 판단 결과를 MCU로 ────────────────────────
def loop():
    global vision_blocked

    blocked = (time.time() - last_seen) < HOLD_SEC

    # 값이 바뀐 순간에만 보낸다 (edge-triggered).
    # 0.1초마다 매번 보내면 초당 10번이고, MCU가 그걸 처리하느라 센서를 못 읽는다.
    if blocked != vision_blocked:
        vision_blocked = blocked
        Bridge.notify("set_vision_block", blocked)
        ui.send_message("vision", message={"blocked": blocked})
        print(f"vision_blocked={blocked}", flush=True)

    time.sleep(0.1)


App.run(user_loop=loop)
