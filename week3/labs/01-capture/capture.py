"""C270으로 학습용 사진 찍기 (노트북에서 실행)

  python capture.py                      세션 번호·카메라 자동
  python capture.py --cam 1 --session s03
  스페이스: 1장 저장 · a: 자동 촬영 켜기/끄기 · q: 종료
"""
import argparse
import re
import sys
import time
from pathlib import Path

import cv2

ap = argparse.ArgumentParser()
ap.add_argument("--cam", type=int, default=None, help="생략하면 1 → 0 → 2 순서로 열리는 카메라를 씀")
ap.add_argument("--session", default=None, help="생략하면 다음 번호(s01, s02 ...)를 자동으로 씀")
ap.add_argument("--out", default=str(Path(__file__).parent / "qrover_data" / "images"))
ap.add_argument("--interval", type=float, default=0.5, help="자동 촬영 간격(초)")
args = ap.parse_args()

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)

# 세션: 장소나 조명이 바뀌면 새 세션. 생략하면 이미 있는 것 다음 번호
if args.session is None:
    used = [int(m.group(1)) for p in out.glob("s*_*.jpg") if (m := re.match(r"s(\d+)_", p.name))]
    args.session = f"s{max(used, default=0) + 1:02d}"
assert "_" not in args.session, "세션 이름에 _ 를 쓰지 마세요 (파일 이름 구분자로 씁니다)"


def open_camera(index):
    # Windows 기본(MSMF)은 C270을 여는 데 30초 넘게 걸림 → DirectShow로 엶. 맥·리눅스는 기본값
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)               # 보드 카메라 기본값과 같은 640x480
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if cap.isOpened() and cap.read()[0]:
        return cap
    cap.release()
    return None


cap, cam = None, None
for i in ([args.cam] if args.cam is not None else [1, 0, 2]):
    cap = open_camera(i)
    if cap:
        cam = i
        break
if cap is None:
    raise SystemExit("카메라를 열 수 없습니다. C270 연결을 확인하고, 다른 프로그램(줌, 카메라 앱)이 쓰고 있지 않은지 보세요.")

n = len(list(out.glob(f"{args.session}_*.jpg")))
print(f"카메라 {cam}번 · 세션 {args.session} · 저장 위치 {out.resolve()}")
print("내장 카메라 화면이 뜨면 q로 끄고 --cam 번호를 바꿔 다시 실행하세요.")
auto, last = False, 0.0


def save(frame):
    global n
    # cv2.imwrite는 Windows에서 한글이 들어간 경로에 조용히 실패합니다 → 인코딩 후 직접 씀
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        print("저장 실패")
        return
    buf.tofile(str(out / f"{args.session}_{n:04d}.jpg"))
    n += 1


while True:
    ok, frame = cap.read()
    if not ok:
        print("카메라 연결이 끊겼습니다.")
        break
    if auto and time.time() - last >= args.interval:
        save(frame)
        last = time.time()

    view = frame.copy()
    cv2.putText(view, f"cam{cam}  {args.session}  saved {n}  {'AUTO' if auto else ''}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if auto else (0, 255, 0), 2)
    cv2.imshow("capture (space: save / a: auto / q: quit)", view)
    k = cv2.waitKey(1) & 0xFF
    if k == ord(" "):
        save(frame)
    elif k == ord("a"):
        auto = not auto
    elif k == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print(f"{args.session}: 총 {n}장 → {out.resolve()}")
