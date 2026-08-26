"""Con so mang tuyen bo la HIEU UNG, khong phai p-value. Va p-value cua bai la SAN.

Nguoi doc ngoai (26/08) chi ra: bai in $p = 1.9\\times10^{-6}$ cho phep so proposed voi
no-CETSP tren 20 cap. Con so do bang **dung** $2/2^{20} = 1{,}907\\times10^{-6}$, tuc
**san duoi tuyet doi** cua kiem dinh dau hai phia voi 20 cap. Dat duoc san nghia la ca
20 cap cung dau, khong hon. No **khong** noi gi ve DO LON, va do lon moi la thu bai
dang tuyen bo.

⛔ Day la lop loi da ghi trong so: [[feedback-p-value-do-lap-lai]] va
[[feedback-null-condition-cho-so-headline]]. Xuat xu dung khong co nghia uoc luong dung,
va mot p-value nho khong co nghia hieu ung lon.

Script nay in ra thu dung dan duoc:
  - so cap, so cap thang, va SAN cua kiem dinh o co mau do
  - hieu ung tuong doi: trung binh, trung vi, khoang gia tri
  - khoang tin cay 95% bootstrap phan vi cho trung binh
"""
import csv
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
B = 20000
SEED = 12345          # co dinh: bootstrap phai tai tao duoc


def main():
    r = list(csv.DictReader(open(os.path.join(RES, "joint_ablation.csv"))))
    prop = [float(x["proposed"]) for x in r]
    base = [float(x["no_cetsp"]) for x in r]
    n = len(r)
    wins = sum(1 for a, b in zip(prop, base) if b > a)
    rel = [100.0 * (b - a) / b for a, b in zip(prop, base)]

    rng = random.Random(SEED)
    bs = sorted(st.mean(rng.choices(rel, k=n)) for _ in range(B))
    lo, hi = bs[int(0.025 * B)], bs[int(0.975 * B)]
    floor = 2.0 / 2 ** n

    rows = [dict(pairs=n, wins=wins, effect_mean_pct=st.mean(rel),
                 effect_median_pct=st.median(rel), effect_min_pct=min(rel),
                 effect_max_pct=max(rel), ci_lo_pct=lo, ci_hi_pct=hi,
                 sign_test_floor=floor, bootstrap_B=B, bootstrap_seed=SEED)]
    with open(os.path.join(RES, "ablation_effect.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("=" * 74)
    print("  CETSP so voi no-CETSP: hieu ung, khong phai p-value")
    print("=" * 74)
    print("  cap        : %d, trong do proposed thang %d" % (n, wins))
    print("  hieu ung   : trung binh %.2f%%  trung vi %.2f%%  khoang [%.2f, %.2f]"
          % (st.mean(rel), st.median(rel), min(rel), max(rel)))
    print("  CI 95%%     : [%.2f%%, %.2f%%]  (bootstrap phan vi, B=%d, seed=%d)"
          % (lo, hi, B, SEED))
    print()
    print("  ⛔ san cua kiem dinh dau hai phia voi %d cap = 2/2^%d = %.3e" % (n, n, floor))
    print("     Bai tung in p = 1.9e-6, tuc DUNG BANG san. Dat san = ca %d cap cung dau." % n)
    print("     No chung nhan CHIEU, khong chung nhan DO LON.")
    print("  => da ghi results/ablation_effect.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
