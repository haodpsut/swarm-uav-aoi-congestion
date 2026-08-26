"""Diem 3 cua phan bien R1: "joint" den muc nao, va co dinh sub-field ton bao nhieu.

Phan bien viet:
    "the sensor field is first partitioned among the UAVs and the trajectory block is
     solved once before the placement and assignment search ... an additional experiment
     comparing this decoupled implementation with a limited joint re-optimization would
     help quantify this effect."

Doc ma: uav_states() goi partition_field(seed) roi optimize_trajectories(groups), CA HAI
deu KHONG biet tram o dau. Tram chi vao o buoc tinh duong vong di sac trong peak_aoi.
Nen khop noi that su nam o cho: UAV nao nhan sub-field nao, khi da biet tram o dau.

PHEP DO (limited joint re-optimization, dung nghia phan bien xin):
  vong 0 : partition -> trajectory -> placement            <- bai dang lam
  vong 1 : GIU nguyen sub-field va quy dao, nhung GAN LAI UAV vao sub-field de giam
           duong vong di tram, roi dat tram lai. So AoI cuoi.

Neu cai thien nho thi viec co dinh sub-field la RE, va bai duoc quyen noi vay KEM SO.
Neu lon thi phai ha chu "joint" xuong, hoac dua vong lap nay vao thuat toan.

⚠ Day la mot vong tai toi uu HAN CHE, khong phai giai bai toan joint day du. Bai phai
noi dung nhu vay.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from scenario import DEFAULTS, tau_charge_of                       # noqa: E402
from solver import (uav_states, candidate_sites, strategy_traffic)  # noqa: E402


def _reassign(states, sites, ports, assign):
    """Gan lai UAV <-> sub-field de giam tong duong bay toi tram da chon.

    Giu NGUYEN tap sub-field va quy dao (nen t_loop, tau_fly khong doi); chi hoan vi
    xem UAV nao phu trach sub-field nao. Dung Hungarian neu co scipy, khong thi greedy.
    """
    n = len(states)
    cost = [[math.dist(states[j]["centroid"], sites[assign[i]]) for j in range(n)]
            for i in range(n)]
    try:
        from scipy.optimize import linear_sum_assignment
        import numpy as np
        r, c = linear_sum_assignment(np.array(cost))
        perm = {int(i): int(j) for i, j in zip(r, c)}
    except Exception:
        perm, used = {}, set()
        for i in sorted(range(n), key=lambda i: min(cost[i])):
            j = min((j for j in range(n) if j not in used), key=lambda j: cost[i][j])
            perm[i], _ = j, used.add(j)
    return [states[perm[i]] for i in range(n)]


def main():
    sc = dict(DEFAULTS)
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    V, S_max, C_tot, M = sc["V"], 2, 4, 12

    print("Diem 3: co dinh sub-field truoc khi dat tram ton bao nhieu?\n")
    print("%4s | %12s %12s | %8s" % ("seed", "vong 0 (bai)", "vong 1 (tai gan)", "cai thien"))
    print("-" * 52)
    rows, gains = [], []
    for sd in range(20):
        st = uav_states(sc, M, sd)
        r0 = strategy_traffic(st, cands, S_max, C_tot, mu, tau_charge, V)
        st1 = _reassign(st, r0["sites"], r0["ports"], r0["assign"])
        r1 = strategy_traffic(st1, cands, S_max, C_tot, mu, tau_charge, V)
        a0, a1 = r0["aoi"], r1["aoi"]
        g = 100.0 * (a0 - a1) / a0 if math.isfinite(a0) and a0 > 0 else float("nan")
        gains.append(g)
        rows.append(dict(seed=sd, aoi_round0=a0, aoi_round1=a1, gain_pct=g))
        print("%4d | %12.2f %12.2f | %7.2f%%" % (sd, a0 / 60, a1 / 60, g))

    ok = [g for g in gains if math.isfinite(g)]
    mean = sum(ok) / len(ok)
    better = sum(1 for g in ok if g > 0.05)
    print("\n  cai thien trung binh: %.2f%% | lon nhat: %.2f%% | >0,05%% o %d/%d seed"
          % (mean, max(ok), better, len(ok)))
    if mean < 1.0:
        print("  => Co dinh sub-field la RE (<1%%). Bai duoc quyen noi vay, KEM SO NAY.")
    elif mean < 5.0:
        print("  => Ton %.2f%%: phai bao cao, va noi ro 'joint' la o PHAT BIEU chu khong"
              " o cach giai." % mean)
    else:
        print("  => ⛔ Ton nhieu: phai ha chu 'joint' hoac dua vong lap vao thuat toan.")
    p = os.path.join(HERE, "..", "results", "joint_reopt_check.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\nSaved results/joint_reopt_check.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
