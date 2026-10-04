#!/usr/bin/env python3
# Q-ROVER 3차시 — 팀 데이터로 YOLOX-Nano 추가 학습
import os

import torch.nn as nn

from yolox.data import COCODataset
from yolox.exp import Exp as MyExp

# 평가용 C++ 확장을 컴파일하지 않고 pycocotools로 평가합니다. (Colab 컴파일 오류 방지)
import yolox.layers as _layers

if hasattr(_layers, "COCOeval_opt"):
    del _layers.COCOeval_opt

DATA_DIR = os.environ.get("QROVER_DATA", "/content/YOLOX/datasets/qrover")


class RGBCOCODataset(COCODataset):
    """보드(Edge Impulse)는 사진을 RGB 순서로 넣어 줍니다.
    YOLOX는 cv2로 읽어 BGR 순서로 학습하므로, 그대로 두면 보드에서는 빨강과 파랑이 뒤바뀐 사진을 보게 됩니다.
    사진을 읽는 함수만 바꿔서 처음부터 RGB 순서로 배우게 합니다."""

    def load_image(self, index):
        return super().load_image(index)[:, :, ::-1].copy()  # BGR → RGB


class Exp(MyExp):
    def __init__(self):
        super().__init__()
        # 데이터 — prepare_dataset이 만든 폴더
        self.data_dir = DATA_DIR
        self.train_ann = "instances_train2017.json"
        self.val_ann = "instances_val2017.json"
        with open(os.path.join(DATA_DIR, "labels.txt"), encoding="utf-8") as f:
            self.num_classes = len([l for l in f if l.strip()])

        # 모델 크기 — 보드에 기본으로 들어 있던 YOLOX-Nano와 같습니다
        self.depth = 0.33
        self.width = 0.25
        self.input_size = (416, 416)
        self.test_size = (416, 416)
        self.random_size = (10, 20)    # 학습 중 320~640 크기를 섞어 가며 학습
        self.mosaic_scale = (0.5, 1.5)
        self.mosaic_prob = 0.5
        self.enable_mixup = False
        self.flip_prob = 0.5           # 좌/우 화살표처럼 방향이 의미 있는 클래스가 있으면 0.0

        # 학습 일정 — 사진 200장 안팎 기준
        self.max_epoch = 100
        self.warmup_epochs = 5
        self.no_aug_epochs = 15
        self.eval_interval = 5
        self.print_interval = 5
        self.data_num_workers = 2
        self.save_history_ckpt = False  # 에폭마다 체크포인트를 남기지 않음 (용량 절약)

        self.exp_name = "qrover_nano"

    def get_dataset(self, cache: bool = False, cache_type: str = "ram"):
        from yolox.data import TrainTransform

        return RGBCOCODataset(
            data_dir=self.data_dir,
            json_file=self.train_ann,
            img_size=self.input_size,
            preproc=TrainTransform(max_labels=50, flip_prob=self.flip_prob, hsv_prob=self.hsv_prob),
            cache=cache,
            cache_type=cache_type,
        )

    def get_eval_dataset(self, **kwargs):
        from yolox.data import ValTransform

        return RGBCOCODataset(
            data_dir=self.data_dir,
            json_file=self.val_ann,
            name="val2017",
            img_size=self.test_size,
            preproc=ValTransform(legacy=kwargs.get("legacy", False)),
        )

    def get_model(self, sublinear=False):
        def init_yolo(M):
            for m in M.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eps = 1e-3
                    m.momentum = 0.03

        if "model" not in self.__dict__:
            from yolox.models import YOLOX, YOLOPAFPN, YOLOXHead
            in_channels = [256, 512, 1024]
            backbone = YOLOPAFPN(self.depth, self.width, in_channels=in_channels, act=self.act, depthwise=True)
            head = YOLOXHead(self.num_classes, self.width, in_channels=in_channels, act=self.act, depthwise=True)
            self.model = YOLOX(backbone, head)

        self.model.apply(init_yolo)
        self.model.head.initialize_biases(1e-2)
        return self.model
