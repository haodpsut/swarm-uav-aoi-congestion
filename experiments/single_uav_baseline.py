"""Duong co so MOT UAV: bai HUA no o phan dong gop nhung ket qua KHONG he co.

Nguoi doc ngoai (26/08): *"The single-UAV comparison promised in contributions is
entirely absent from results tables and figures."* Doc lai Intro thi dung: cau ve dong
gop liet ke bon duong co so **single-UAV**, single-station, coverage-optimal,
round-robin, va bang ablation chi co bon cai sau.

⛔ Lop loi: MAT TIEN hua mot dang, THAN BAI giao mot dang khac. Cung ho voi ca da ghi o
[[feedback-mat-tien-khong-ai-soi]]. Khong cong nao bat duoc vi ca hai cho deu dung cu
phap, chi khac NOI DUNG.

Phep do o day chay dung cung ham `solve` va cung bo seed nhu bang ablation, chi khac
$M=1$: mot UAV tuan tra CA canh dong. No la moc quy chieu cho cau mo dau cua bai
(*"mot UAV chi giu tuoi tin cho mot vung nho"*), va no cho biet ca dan mua duoc bao
nhieu so voi mot chiec.
"""
import csv
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scenario import DEFAULTS                    # noqa: E402
from solver import solve, candidate_sites        # noqa: E402

L = 15000.0          # cung canh dong voi bang ablation
M_SWARM = 12         # cung co dan voi bang ablation
SEEDS = list(range(20))


def run(M, method, sc, cands):
    out = []
    for sd in SEEDS:
        v = solve(sc, M, sd, method, cands=cands)
        out.append(v / 60.0 if math.isfinite(v) else math.nan)
    return out


def main():
    sc = dict(DEFAULTS)
    sc["L"] = L
    cands = candidate_sites(sc["L"], n=3)

    one = run(1, "proposed", sc, cands)
    swarm = run(M_SWARM, "proposed", sc, cands)

    ok = [(a, b) for a, b in zip(one, swarm)
          if not math.isnan(a) and not math.isnan(b)]
    gains = [100.0 * (a - b) / a for a, b in ok]

    rows = [dict(seed=sd, single_uav_min=a, swarm_min=b,
                 gain_pct=100.0 * (a - b) / a)
            for sd, (a, b) in zip(SEEDS, ok)]
    with open(os.path.join(ROOT, "results", "single_uav_baseline.csv"), "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("=" * 74)
    print("  DUONG CO SO MOT UAV (L=%.0f km, %d seed)" % (L / 1000, len(ok)))
    print("=" * 74)
    print("  mot UAV      : %8.1f phut  (do lech chuan %.1f)"
          % (st.mean([a for a, _ in ok]), st.pstdev([a for a, _ in ok])))
    print("  dan %2d UAV   : %8.1f phut  (do lech chuan %.1f)"
          % (M_SWARM, st.mean([b for _, b in ok]), st.pstdev([b for _, b in ok])))
    print("  dan giam AoI : %8.1f%%  (trung vi %.1f%%, thap nhat %.1f%%)"
          % (st.mean(gains), st.median(gains), min(gains)))
    print("  seed ma dan THUA: %d/%d" % (sum(1 for g in gains if g < 0), len(gains)))
    print("  => da ghi results/single_uav_baseline.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
