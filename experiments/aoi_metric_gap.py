"""Diem 1 cua phan bien R1: Eq (2) la WORST-CASE, Eq (11) dung TRUNG BINH.

Phan bien viet:
    "please explain under what assumptions the mean charging delay in Eq. (10) can be
     used in the worst-case/peak AoI expression in Eq. (11). Alternatively, if the
     intended performance metric is an expected peak AoI, the corresponding definition
     could be stated more explicitly."

Day KHONG phai chi la mot quyet dinh viet lach. No DO DUOC: chay DES, lay CA PHAN PHOI
thoi gian cho, roi so AoI tinh bang cho TRUNG BINH voi AoI tinh bang cho o cac PHAN VI
cao. Khoang cach do chinh la cai gia cua viec thay worst-case bang trung binh.

    AoI = t_patrol + travel + W + tau_charge

nen chenh lech AoI bang dung chenh lech W. Bao ca hai de nguoi doc tu thay.

Ket qua dung de chon MOT trong hai duong da chot o THIET-KE-TRUOC.md:
  1. giu worst-case, neu chung minh duoc dieu kien thay the
  2. doi muc tieu thanh EXPECTED peak AoI va noi thang  <- mac dinh
"""
import csv
import math
import os
import sys
import statistics as st

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)
from des_validation import simulate                    # noqa: E402
from scenario import DEFAULTS, tau_charge_of           # noqa: E402
from queue_model import finite_source_wq               # noqa: E402


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))
    return xs[k]


def main():
    sc = dict(DEFAULTS)
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    travel = 120.0
    print("Diem 1: thay cho WORST-CASE bang cho TRUNG BINH ton bao nhieu?\n")
    print("  DES o che do van hanh + sac GAN TAT DINH (che do bai nham toi).")
    print("  W la thoi gian cho tram; AoI = t_patrol + travel + W + tau_charge,")
    print("  nen chenh lech AoI bang dung chenh lech W.\n")
    print("%3s %2s | %9s %9s %9s %9s | %8s %8s" %
          ("M", "c", "W_tb(DES)", "W_p90", "W_p95", "W_max", "p95/tb", "max/tb"))
    print("-" * 74)
    rows = []
    for c in (2, 3, 4):
        for M in (8, 10, 12):
            tau_fly = 900.0
            mean_w, waits = simulate(M, c, tau_fly, tau_charge, travel,
                                     service="det", operating="det",
                                     return_waits=True)
            if not waits:
                continue
            p90, p95, mx = q(waits, .90), q(waits, .95), max(waits)
            r95 = p95 / mean_w if mean_w > 0 else float("nan")
            rmx = mx / mean_w if mean_w > 0 else float("nan")
            rows.append(dict(M=M, c=c, w_mean=mean_w, w_p90=p90, w_p95=p95, w_max=mx,
                             ratio_p95=r95, ratio_max=rmx, n_waits=len(waits)))
            print("%3d %2d | %9.1f %9.1f %9.1f %9.1f | %8.2f %8.2f"
                  % (M, c, mean_w, p90, p95, mx, r95, rmx))

    r95 = [r["ratio_p95"] for r in rows if math.isfinite(r["ratio_p95"])]
    rmx = [r["ratio_max"] for r in rows if math.isfinite(r["ratio_max"])]
    print("\n  ti so p95 / trung binh : trung vi %.2f  (khoang %.2f - %.2f)"
          % (st.median(r95), min(r95), max(r95)))
    print("  ti so max / trung binh : trung vi %.2f  (khoang %.2f - %.2f)"
          % (st.median(rmx), min(rmx), max(rmx)))
    print("\n  DOC THE NAO:")
    print("  - ti so gan 1  => cho gan tat dinh, trung binh la dai dien tot, GIU worst-case")
    print("                    va noi ro dieu kien do.")
    print("  - ti so lon    => trung binh KHONG dai dien cho worst-case, phai DOI dinh")
    print("                    nghia muc tieu thanh EXPECTED peak AoI.")
    p = os.path.join(HERE, "..", "results", "aoi_metric_gap.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\nSaved results/aoi_metric_gap.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
