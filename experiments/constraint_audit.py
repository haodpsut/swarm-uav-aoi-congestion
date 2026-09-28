"""R5 diem 3: bao MUC VI PHAM LON NHAT cua MOI rang buoc lien quan.

Phan bien 5, diem 3 vong 1:
    "The paper does not show that Algorithm 1 returns a feasible solution to P0.
     Distinguish the original problem from the surrogate and REPORT THE MAXIMUM
     VIOLATION of every relevant constraint."

Doi hoi nay dung va re: neu bo giai tra ve loi giai kha thi thi con so phai bang 0, con
neu khong thi con so do chinh la thu phai khai. Script kiem TUNG rang buoc cua (P0) tren
cau hinh CUOI CUNG cua moi hat giong:

  (a) ban kinh thu thap r_c        : max_k [ d_min(k) - r_c ]_+      met
  (b) kha dat tram (12c)           : max_m [ d(m,s)/V - reach ]_+    giay
  (c) ngan sach tram (12e)         : so tram mo tru S_max            dem
  (d) ngan sach cong (12f)         : tong cong tru C_tot             dem
  (e) gan vao tram DA MO (12h)     : so UAV gan vao tram dong        dem
  (f) gian cach giua UAV (12i)     : KHONG kiem duoc o muc truu tuong nay, xem
                                     separation_check.py; bao la NOI LONG, khong bao 0.

⛔ Khong duoc bao 0 cho (f). Mot bang toan so 0 trong khi mot rang buoc thuc ra khong
duoc ep la kieu bao cao de doc thanh "moi thu kha thi", va do la noi doi bang cach im
lang. Xem [[feedback-kiem-0-don-vi-khong-phai-sach]].

TU KIEM (doi chung DUONG): tiem mot cau hinh CO LOI (ngan sach cong bi vuot va mot tram
dong duoc gan UAV) va doi ham kiem phai bat ca hai.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scenario import DEFAULTS, tau_charge_of                    # noqa: E402
from energy import propulsion_power                             # noqa: E402
from field import partition_field                               # noqa: E402
from trajectory import optimize_trajectories                    # noqa: E402
from solver import (uav_states, candidate_sites,                # noqa: E402
                    strategy_traffic)

SEEDS = list(range(20))
M, S_MAX, C_TOT, R_C, L = 12, 2, 4, 200.0, 15000.0
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def audit(states, sites, ports, assign, V, reach, cov_viol):
    mo = [s for s in range(len(sites)) if ports[s] > 0]
    v_reach = max((math.dist(states[i]["centroid"], sites[assign[i]]) / V - reach
                   for i in range(len(states))), default=0.0)
    return dict(cov_m=max(0.0, cov_viol),
                reach_s=max(0.0, v_reach),
                stations=max(0, len(mo) - S_MAX),
                ports=max(0, sum(ports) - C_TOT),
                closed_assign=sum(1 for i in range(len(states)) if ports[assign[i]] <= 0))


def main():
    sc = dict(DEFAULTS); sc["L"] = L; sc["reachability"] = True
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau = tau_charge_of(sc["E_max"], sc["charge_power"])
    V = sc["V"]
    reach = sc["E_reserve"] * sc["E_max"] / propulsion_power(V)
    cands = candidate_sites(sc["L"], n=3)

    print("Muc vi pham LON NHAT tren cau hinh cuoi (%d seed, M=%d, L=%.0f km)\n"
          % (len(SEEDS), M, L / 1000))
    print("%5s | %10s %10s %9s %7s %9s" % ("seed", "phu (m)", "kha dat (s)",
                                           "so tram", "so cong", "tram dong"))
    print("-" * 62)
    rows = []
    for sd in SEEDS:
        _, groups = partition_field(sc["K"], sc["L"], M, sd,
                                    clustered=sc.get("clustered", False))
        _, cov_viol = optimize_trajectories(groups, R_C, V, seed=sd)
        states = uav_states(sc, M, sd)
        r = strategy_traffic(states, cands, S_MAX, C_TOT, mu, tau, V, reach)
        a = audit(states, r["sites"], r["ports"], r["assign"], V, reach, cov_viol)
        a["seed"] = sd
        rows.append(a)
        print("%5d | %10.4f %10.4f %9d %7d %9d"
              % (sd, a["cov_m"], a["reach_s"], a["stations"], a["ports"], a["closed_assign"]))

    print("\n  ⭐ LON NHAT tren moi hat giong:")
    for k, nhan, don in (("cov_m", "ban kinh thu thap r_c", "m"),
                         ("reach_s", "kha dat tram (12c)", "s"),
                         ("stations", "ngan sach tram (12e)", "tram"),
                         ("ports", "ngan sach cong (12f)", "cong"),
                         ("closed_assign", "gan vao tram dong (12h)", "UAV")):
        print("     %-28s %12.4f %s" % (nhan, max(r[k] for r in rows), don))
    print("     %-28s %12s    xem separation_check.py"
          % ("gian cach (12i)", "NOI LONG"))

    print("\n== TU KIEM (doi chung DUONG: tiem cau hinh co loi) ==")
    states = uav_states(sc, M, 0)
    xau = audit(states, [(0.0, 0.0), (1.0, 1.0)], [3, 3], [0] * M, V, reach, 0.0)
    kiem(xau["ports"] == 2, "bat duoc vuot ngan sach cong", "thua %d" % xau["ports"])
    xau2 = audit(states, [(0.0, 0.0), (1.0, 1.0)], [4, 0], [1] * M, V, reach, 0.0)
    kiem(xau2["closed_assign"] == M, "bat duoc gan vao tram DONG",
         "%d UAV" % xau2["closed_assign"])
    kiem(all(r["stations"] == 0 and r["ports"] == 0 and r["closed_assign"] == 0
             for r in rows), "cau hinh that: khong vi pham ngan sach hay tram dong")

    p = os.path.join(ROOT, "results", "constraint_audit.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["seed", "cov_m", "reach_s", "stations",
                                          "ports", "closed_assign"])
        w.writeheader()
        w.writerows([{k: r[k] for k in w.fieldnames} for r in rows])
    print("\n=> %s (%d loi). Da ghi results/constraint_audit.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
