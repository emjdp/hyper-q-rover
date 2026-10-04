"""TLM 로그(csv) 여러 개를 겹쳐 그리기 - KP_STEER 비교용

  python plot_runs.py kp03.csv kp06.csv kp12.csv

로그 한 줄 = TLM,시각,보임(0/1),조향오차,거리mm,왼쪽PWM,오른쪽PWM   (main.py의 on_telemetry가 찍음)
목표를 처음 본 순간(보임=1)을 0초로 맞춰 겹칩니다.
"""
import sys

import matplotlib.pyplot as plt
import pandas as pd

TOL = 10   # |오차|가 이 안이면 "가운데"로 봄 (표의 "가운데까지" 기준)
cols = ["tag", "t", "seen", "err", "dist", "left", "right"]

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6))
print(f"{'파일':<12}{'시작 오차':>8}{'가운데까지(s)':>14}{'반대쪽 최대':>11}{'좌우 바뀜':>9}{'마지막 오차':>11}{'마지막 거리':>11}")

for f in sys.argv[1:]:
    d = pd.read_csv(f, names=cols)
    on = d.index[d.seen == 1]
    if len(on) == 0:
        print(f"{f}: 목표를 본 구간(보임=1)이 없습니다")
        continue
    d = d.loc[on[0]:].reset_index(drop=True)
    t = d.t - d.t.iloc[0]
    e = d.err.where(d.seen == 1)

    ax1.plot(t, e, marker=".", label=f)
    ax2.plot(t, d.dist.where(d.dist >= 0), label=f)

    e0 = int(d.err.iloc[0])
    side = 1 if e0 >= 0 else -1
    inside = d.index[(d.seen == 1) & (d.err.abs() <= TOL)]
    t_center = f"{t[inside[0]]:.1f}" if len(inside) else "-"
    over = max(0, int((-side * e).max()))            # 시작과 반대쪽으로 넘어간 최대 오차
    big = e[e.abs() > TOL].dropna()
    flips = int((big.apply(lambda v: v > 0).astype(int).diff().abs() == 1).sum())   # 가운데 밖에서 좌우가 바뀐 횟수
    last_e = d.err[d.seen == 1].iloc[-1]
    valid = d.dist[d.dist >= 0]
    last_d = int(valid.iloc[-1]) if len(valid) else "-"
    print(f"{f:<12}{e0:>8}{t_center:>14}{over:>11}{flips:>9}{last_e:>11}{last_d:>11}")

ax1.axhline(0, ls="--", c="gray")
ax1.axhspan(-TOL, TOL, color="gray", alpha=0.15)
ax1.set_ylabel("steer error [-100~100]")
ax1.legend()
ax2.set_ylabel("ToF distance [mm]")
ax2.set_xlabel("time since target first seen [s]")
plt.tight_layout()
plt.savefig("approach.png", dpi=150)
print("저장: approach.png")
