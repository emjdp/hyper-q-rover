"""학습된 체크포인트(.pth) → ONNX
YOLOX의 tools/export_onnx.py는 최신 PyTorch에서 동작하지 않아(torch.onnx._export 삭제) 같은 일을 하는 짧은 버전을 씁니다.

  python export_qrover.py exps/qrover_nano.py YOLOX_outputs/qrover_nano/best_ckpt.pth qrover_nano.onnx
"""
import sys

import torch
from torch import nn

from yolox.exp import get_exp
from yolox.models.network_blocks import SiLU
from yolox.utils import replace_module

exp_file, ckpt_file, out_file = sys.argv[1:4]
exp = get_exp(exp_file, None)
model = exp.get_model()

ckpt = torch.load(ckpt_file, map_location="cpu", weights_only=False)  # 직접 학습한 파일이라 믿고 엽니다
model.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
model.eval()
model = replace_module(model, nn.SiLU, SiLU)   # SiLU를 x*sigmoid(x)로 풀어서 내보냄
model.head.decode_in_inference = False         # 칸(grid) 좌표 그대로 내보냄 — Edge Impulse의 YOLOX 형식이 이것

dummy = torch.randn(1, 3, *exp.test_size)
kwargs = dict(input_names=["images"], output_names=["output"], opset_version=11)
try:
    torch.onnx.export(model, dummy, out_file, dynamo=False, **kwargs)   # PyTorch 2.5 이상
except TypeError:
    torch.onnx.export(model, dummy, out_file, **kwargs)                 # 그보다 오래된 PyTorch

with torch.no_grad():
    shape = tuple(model(dummy).shape)
print(f"저장: {out_file}  입력 (1, 3, {exp.test_size[0]}, {exp.test_size[1]})  출력 {shape}"
      f"  = (1, 칸 개수, 4+1+클래스 {exp.num_classes}개)")
