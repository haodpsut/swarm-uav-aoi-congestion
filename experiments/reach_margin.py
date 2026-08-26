"""Diem 4 cua phan bien R1: rang buoc (12b)-(12c) ep o dau, va bien con lai bao nhieu.

Phan bien viet:
    "Since the station assignment a_m changes during the placement and assignment
     search, it is not fully clear from Algorithm 1 where this constraint is checked
     after a UAV is reassigned ... Reporting the minimum energy or reachability margin
     observed in the experiments would also provide useful confirmation."

TRA LOI NUA DAU, doc tu ma (src/solver.py):
    peak_aoi() tra ve +inf neu BAT KY UAV nao co d/V > reach_budget, va greedy_balance()
    goi lai peak_aoi() sau MOI lan doi gan. Nen rang buoc duoc ep lai o TUNG phuong an,
    khong phai kiem mot lan roi thoi. Cau nay chi can noi ro trong bai.

TRA LOI NUA SAU la phep do nay: voi cau hinh CUOI CUNG cua tung seed, in
    margin_m = reach_budget - d(centroid_m, station(a_m)) / V      [giay]
va bao con so NHO NHAT tren toan bo seed. Duong = con du bao nhieu giay bay.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from scenario import DEFAULTS, tau_charge_of                      # noqa: E402
from energy import propulsion_power                               # noqa: E402
from solver import uav_states, candidate_sites, strategy_traffic  # noqa: E402


def main():
    sc = dict(DEFAULTS)
    sc["reachability"] = True          # bat rang buoc de do bien
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    V, S_max, C_tot, M = sc["V"], 2, 4, 12
    reach = sc["E_reserve"] * sc["E_max"] / propulsion_power(V)

    print("Diem 4: bien kha dat tram cua cau hinh CUOI CUNG\n")
    print("  ngan sach mot chieu reach = E_reserve * E_max / P_cruise = %.1f s bay" % reach)
    print("  margin_m = reach - d(m, tram cua m)/V   (duong = con du)\n")
    print("%4s | %10s %10s %10s | %s" % ("seed", "min (s)", "TB (s)", "max (s)", "kha thi"))
    print("-" * 58)
    rows, allmin = [], []
    for sd in range(20):
        states = uav_states(sc, M, sd)
        r = strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V, reach)
        if not math.isfinite(r["aoi"]):
            print("%4d | %s" % (sd, "KHONG co phuong an kha thi"))
            continue
        mg = [reach - math.dist(s["centroid"], r["sites"][r["assign"][i]]) / V
              for i, s in enumerate(states)]
        allmin.append(min(mg))
        rows.append(dict(seed=sd, margin_min=min(mg), margin_mean=sum(mg) / len(mg),
                         margin_max=max(mg), feasible=int(min(mg) >= 0)))
        print("%4d | %10.1f %10.1f %10.1f | %s"
              % (sd, min(mg), sum(mg) / len(mg), max(mg), "co" if min(mg) >= 0 else "⛔ KHONG"))

    gmin = min(allmin)
    print("\n  ⭐ BIEN NHO NHAT tren %d seed x %d UAV: %.1f s bay" % (len(rows), M, gmin))
    print("     tuc %.1f%% ngan sach mot chieu (%.1f s) van con du."
          % (100.0 * gmin / reach, reach))
    print("  => moi cau hinh cuoi %s"
          % ("KHA THI, khong ca nao sat bien." if gmin > 0 else "⛔ CO ca cham bien."))
    p = os.path.join(HERE, "..", "results", "reach_margin.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\nSaved results/reach_margin.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
