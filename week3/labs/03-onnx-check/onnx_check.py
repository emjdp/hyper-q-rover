"""같은 ONNX 모델을 노트북에서 돌려 봅니다. Brick도 Edge Impulse도 없이 numpy + OpenCV + onnxruntime만으로.

  python onnx_check.py qrover_nano.onnx labels.txt                      웹캠 (1 → 0 → 2번 순서로 자동, q로 종료)
  python onnx_check.py qrover_nano.onnx labels.txt --cam 0              웹캠 번호 지정
  python onnx_check.py qrover_nano.onnx labels.txt --images 폴더 --save 결과폴더
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


def preprocess(frame_bgr, size):
    img = cv2.resize(frame_bgr, (size, size))             # ① 비율 무시하고 늘려 맞춤 — 보드(EI)의 squash와 같음
    img = img[:, :, ::-1]                                 # ② BGR → RGB — 학습 때와 같은 순서
    x = img.transpose(2, 0, 1)[None].astype(np.float32)   # ③ (1, 3, H, W), 0~255 그대로 (정규화 없음)
    return np.ascontiguousarray(x)


def decode(out, size, strides=(8, 16, 32)):
    grids, steps = [], []
    for s in strides:
        n = size // s
        xv, yv = np.meshgrid(np.arange(n), np.arange(n))
        grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
        steps.append(np.full((n * n, 1), s))
    grids, steps = np.concatenate(grids), np.concatenate(steps)
    out[:, :2] = (out[:, :2] + grids) * steps   # 칸 번호 + 칸 안의 위치 → 픽셀 좌표
    out[:, 2:4] = np.exp(out[:, 2:4]) * steps   # log 크기 → 픽셀 크기
    return out


def detect(sess, frame_bgr, names, size, conf_th, nms_th=0.45):
    out = sess.run(None, {sess.get_inputs()[0].name: preprocess(frame_bgr, size)})[0][0]
    out = decode(out.copy(), size)
    scores = out[:, 4:5] * out[:, 5:]           # "뭔가 있다" 확률 × "그게 이 클래스다" 확률
    cls, conf = scores.argmax(1), scores.max(1)
    keep = conf >= conf_th
    boxes, cls, conf = out[keep, :4], cls[keep], conf[keep]

    h, w = frame_bgr.shape[:2]
    sx, sy = w / size, h / size                 # 416x416 좌표 → 원래 사진 좌표
    xywh = [[(b[0] - b[2] / 2) * sx, (b[1] - b[3] / 2) * sy, b[2] * sx, b[3] * sy] for b in boxes]
    result = {}
    for i in np.array(cv2.dnn.NMSBoxes(xywh, conf.tolist(), conf_th, nms_th)).flatten():
        x, y, bw, bh = xywh[i]
        result.setdefault(names[cls[i]], []).append(
            {"confidence": round(float(conf[i]), 2),
             "bounding_box_xyxy": (int(x), int(y), int(x + bw), int(y + bh))})
    return result                               # 보드의 on_detect_all 콜백이 받는 것과 같은 모양


def draw(frame, result):
    for label, items in result.items():
        for it in items:
            x1, y1, x2, y2 = it["bounding_box_xyxy"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {it['confidence']:.2f}", (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame


def open_camera(index):
    # Windows 기본(MSMF)은 C270을 여는 데 30초 넘게 걸림 → DirectShow로 엶. 맥·리눅스는 기본값
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if cap.isOpened() and cap.read()[0]:
        return cap
    cap.release()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("labels")
    ap.add_argument("--cam", type=int, default=None, help="생략하면 1 → 0 → 2 순서로 열리는 카메라를 씀")
    ap.add_argument("--images", default=None)
    ap.add_argument("--save", default=None)
    ap.add_argument("--conf", type=float, default=0.5)
    args = ap.parse_args()

    names = [l.strip() for l in Path(args.labels).read_text(encoding="utf-8").splitlines() if l.strip()]
    sess = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    size = sess.get_inputs()[0].shape[2]
    print("입력", sess.get_inputs()[0].shape, "/ 출력", sess.get_outputs()[0].shape, "/ 클래스", names)

    if args.images:
        save = Path(args.save) if args.save else None
        if save:
            save.mkdir(parents=True, exist_ok=True)
        times = []
        for p in sorted(Path(args.images).glob("*.jpg")):
            frame = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)   # 한글 경로에서도 읽힘
            t0 = time.perf_counter()
            result = detect(sess, frame, names, size, args.conf)
            times.append(time.perf_counter() - t0)
            print(p.name, result)
            if save:
                cv2.imencode(".jpg", draw(frame, result))[1].tofile(str(save / p.name))   # 한글 경로에서도 써짐
        if times:
            print(f"평균 추론 시간 {1000 * np.mean(times):.1f} ms  (약 {1 / np.mean(times):.1f} FPS)")
        return

    cap, cam = None, None
    for i in ([args.cam] if args.cam is not None else [1, 0, 2]):
        cap = open_camera(i)
        if cap:
            cam = i
            break
    if cap is None:
        raise SystemExit("카메라를 열 수 없습니다. C270 연결을 확인하고, 다른 프로그램(줌, 카메라 앱)이 쓰고 있지 않은지 보세요.")
    print(f"카메라 {cam}번 · q로 종료. 내장 카메라 화면이 뜨면 --cam 번호를 바꿔 다시 실행하세요.")
    fps = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t0 = time.perf_counter()
        result = detect(sess, frame, names, size, args.conf)
        fps = 0.9 * fps + 0.1 / (time.perf_counter() - t0)
        draw(frame, result)
        cv2.putText(frame, f"{fps:.1f} FPS", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("onnx_check", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
