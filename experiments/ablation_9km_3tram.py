"""So sanh chinh o L = 9 km voi BA tram: che do THAT SU BAY DUOC.

⛔ VI SAO CO TEP NAY. Nguoi doc ngoai 03/10/2026 chi ra mot dieu dung va nang:
moi con so headline cua bai deu do o cho thiet ke KHONG BAY DUOC. Ngan sach mot
chieu la 282 s; Bang V cho thay o 9, 15 va 20 km thi 0/20 hat giong kha thi, voi
muc vuot 371, 806 va 1168 s. Ablation, kiem dinh Wilcoxon va Bang VI deu chay o
15 km, con "up to 12,7%" trong abstract den tu 20 km. Vung kha thi that chi la
5 va 6 km.

Nhung chinh Bang V cung noi: o 9 km, BA tram khoi phuc duoc kha thi. Nen thi
nghiem nay chay lai so sanh chinh o L = 9 km voi S_max = 3, de bai co mot ket qua
o giua mien va BAY DUOC, thay vi mot ket qua ly tuong hoa.

In ra:
  - AoI tung phuong phap, trung binh va do lech chuan tren 20 hat giong
  - loi ich cua phuong phap de xuat so voi moc manh nhat
  - va QUAN TRONG NHAT: so hat giong KHA THI, vi neu lai 0/20 thi thi nghiem nay
    khong cuu duoc gi va phai noi that nhu vay

    python experiments/ablation_9km_3tram.py
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from scenario import DEFAULTS                       # noqa: E402
from solver import solve, candidate_sites           # noqa: E402
from energy import propulsion_power                 # noqa: E402

L_KM = 9.0
S_MAX = 3
C_TOT = 4
M = 12
SEEDS = list(range(20))

METHODS = [
    ("proposed", "CETSP traj + traffic-optimal placement"),
    ("no_cetsp", "NN traj + traffic-optimal (ablate trajectory)"),
    ("coverage", "CETSP traj + coverage placement (ablate contention)"),
    ("roundrobin", "CETSP traj + coverage sites + round-robin"),
    ("single_station", "CETSP traj + one pooled station (Wei-style)"),
]


def tb_dlc(v):
    w = [x / 60.0 for x in v if math.isfinite(x)]
    if not w:
        return float("nan"), float("nan"), 0
    m = sum(w) / len(w)
    sd = (sum((x - m) ** 2 for x in w) / len(w)) ** 0.5
    return m, sd, len(w)


def main():
    sc = dict(DEFAULTS)
    sc["L"] = L_KM * 1000.0
    sc["reachability"] = True          # BAT kiem kha thi, day la diem cua thi nghiem
    cands = candidate_sites(sc["L"], n=3)
    budget = sc["E_reserve"] * sc["E_max"] / propulsion_power(sc["V"])

    print("== So sanh chinh o L = %.0f km, S_max = %d, C_tot = %d, M = %d =="
          % (L_KM, S_MAX, C_TOT, M))
    print("   ngan sach bay mot chieu: %.0f s (%.2f km o %.0f m/s)\n"
          % (budget, budget * sc["V"] / 1000.0, sc["V"]))

    res = {}
    print("   %-16s %9s %7s %9s | %s" % ("phuong phap", "AoI(min)", "std", "kha thi", "mo ta"))
    print("   " + "-" * 86)
    for m, desc in METHODS:
        v = [solve(sc, M, sd, m, cands=cands, S_max=S_MAX, C_tot=C_TOT) for sd in SEEDS]
        res[m] = v
        tb, sd, n = tb_dlc(v)
        print("   %-16s %9.2f %7.2f %6d/%-3d | %s" % (m, tb, sd, n, len(SEEDS), desc))

    # ⛔ Neu khong hat giong nao kha thi thi thi nghiem nay KHONG cuu duoc gi.
    n_kt = sum(1 for x in res["proposed"] if math.isfinite(x))
    print()
    if n_kt == 0:
        print("   ⛔ 0/%d hat giong kha thi: BA TRAM VAN KHONG DU o %.0f km." % (len(SEEDS), L_KM))
        print("      Phai bao that nhu vay, khong duoc lay ket qua nay lam headline.")
    else:
        ten = [m for m, _ in METHODS if m != "proposed"]
        manh = min(ten, key=lambda m: tb_dlc(res[m])[0])
        cap = [(a, b) for a, b in zip(res["proposed"], res[manh])
               if math.isfinite(a) and math.isfinite(b)]
        if cap:
            loi = 100.0 * (sum(b for _, b in cap) - sum(a for a, _ in cap)) / sum(b for _, b in cap)
            xau = min(100.0 * (b - a) / b for a, b in cap)
            thang = sum(1 for a, b in cap if a < b)
            print("   moc manh nhat: %s" % manh)
            print("   loi ich trung binh: %+.1f%% | hat giong xau nhat: %+.1f%% | thang %d/%d cap"
                  % (loi, xau, thang, len(cap)))
        don = [(a, b) for a, b in zip(res["proposed"], res["single_station"])
               if math.isfinite(a) and math.isfinite(b)]
        if don:
            l2 = 100.0 * (sum(b for _, b in don) - sum(a for a, _ in don)) / sum(b for _, b in don)
            x2 = min(100.0 * (b - a) / b for a, b in don)
            print("   so voi tram gop don: trung binh %+.1f%%, xau nhat %+.1f%%" % (l2, x2))

    out = os.path.join(ROOT, "results", "ablation_9km_3st.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed"] + [m for m, _ in METHODS])
        for i, sd in enumerate(SEEDS):
            w.writerow([sd] + [res[m][i] for m, _ in METHODS])
    print("\n   da ghi %s" % os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
