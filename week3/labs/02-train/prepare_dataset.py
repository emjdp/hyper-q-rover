"""팀 데이터(YOLO 형식) → YOLOX 학습용(COCO 형식)

입력 (SRC)
  images/s01_0001.jpg ...      파일 이름 앞부분(_ 앞)이 촬영 세션
  labels/s01_0001.txt ...      YOLO 형식: 클래스번호 cx cy w h (0~1)
  labels.txt                   클래스 이름, 한 줄에 하나. 순서 = 클래스 번호
출력 (DST)
  train2017/, val2017/         416x416으로 늘려 맞춘 사진 (squash)
  annotations/instances_train2017.json, instances_val2017.json
  labels.txt
"""
import json
import os
import random
import shutil
from collections import Counter
from pathlib import Path

import cv2

SRC = Path(os.environ.get("QROVER_SRC", "/content/qrover_data"))
DST = Path(os.environ.get("QROVER_DATA", "/content/YOLOX/datasets/qrover"))
SIZE = 416
VAL_SESSIONS = []      # 예: ["s05"]. 비워 두면 세션 단위로 약 20%를 자동으로 고릅니다
SEED = 0

names = [l.strip() for l in (SRC / "labels.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
images = sorted(p for p in (SRC / "images").iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def session_of(p):
    return p.stem.split("_")[0]


sessions = sorted({session_of(p) for p in images})
assert len(sessions) >= 2, "촬영 세션이 1개뿐입니다. 파일 이름을 s01_..., s02_... 처럼 2개 이상으로 나눠 찍으세요."

if VAL_SESSIONS:
    val_sessions = set(VAL_SESSIONS)
else:
    order = sessions[:]
    random.Random(SEED).shuffle(order)
    count = Counter(session_of(p) for p in images)
    val_sessions, n = set(), 0
    for s in order:
        if n >= 0.2 * len(images):
            break
        if n + count[s] <= 0.35 * len(images):    # 너무 큰 세션은 검증으로 빼지 않음 (학습할 사진이 모자라짐)
            val_sessions.add(s)
            n += count[s]
    if not val_sessions:                          # 세션이 전부 크면 가장 작은 세션 하나
        val_sessions = {min(sessions, key=count.get)}
assert len(val_sessions) < len(sessions), "모든 세션이 검증용이 되었습니다. VAL_SESSIONS를 확인하세요."


def build(split, files):
    out = DST / f"{split}2017"
    out.mkdir(parents=True, exist_ok=True)
    coco = {
        "info": {}, "licenses": [],
        "images": [], "annotations": [],
        "categories": [{"id": i + 1, "name": n} for i, n in enumerate(names)],
    }
    boxes, background = Counter(), 0
    for img_id, p in enumerate(files, 1):
        img = cv2.imread(str(p))
        if img is None:
            print("  읽기 실패, 건너뜀:", p.name)
            continue
        img = cv2.resize(img, (SIZE, SIZE), interpolation=cv2.INTER_AREA)  # 비율 무시하고 늘려 맞춤
        cv2.imwrite(str(out / f"{p.stem}.jpg"), img)
        coco["images"].append({"id": img_id, "file_name": f"{p.stem}.jpg", "width": SIZE, "height": SIZE})

        txt = SRC / "labels" / f"{p.stem}.txt"
        lines = txt.read_text().split("\n") if txt.exists() else []
        n_obj = 0
        for line in lines:
            v = line.split()
            if len(v) != 5:
                continue
            c = int(v[0])
            assert 0 <= c < len(names), f"{txt.name}: 클래스 번호 {c}가 labels.txt 범위 밖입니다"
            cx, cy, w, h = (float(x) * SIZE for x in v[1:])
            coco["annotations"].append({
                "id": len(coco["annotations"]) + 1, "image_id": img_id, "category_id": c + 1,
                "bbox": [cx - w / 2, cy - h / 2, w, h], "area": w * h, "iscrowd": 0,
            })
            boxes[names[c]] += 1
            n_obj += 1
        background += n_obj == 0

    (DST / "annotations").mkdir(parents=True, exist_ok=True)
    with open(DST / "annotations" / f"instances_{split}2017.json", "w", encoding="utf-8") as f:
        json.dump(coco, f, ensure_ascii=False)
    print(f"[{split}] 사진 {len(coco['images'])}장 (배경 {background}장) / 박스", dict(boxes))


if DST.exists():
    shutil.rmtree(DST)
build("train", [p for p in images if session_of(p) not in val_sessions])
build("val", [p for p in images if session_of(p) in val_sessions])
shutil.copy(SRC / "labels.txt", DST / "labels.txt")
print("검증 세션:", sorted(val_sessions), "/ 클래스:", names)
