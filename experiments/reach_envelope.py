"""R5 diem 3 + R4 diem 4: rang buoc kha dat tram (12c) thoa duoc TOI DAU.

⛔ VI SAO CO TEP NAY. Muc VI-I cua ban da nop khang dinh:
    "an infeasible configuration can never be returned as the best one ... The returned
     designs are feasible with margin to spare"
voi bien nho nhat 7,69 s va 0/20 cau hinh bat kha thi. Con so ay do bang reach_margin.py
tren DEFAULTS, tuc vung **5 km**.

Nhung phep so chinh cua bai chay o **15 km**, va quet kich thuoc vung chay toi **20 km**.
O do `sc.get("reachability", False)` la False, nen `reach = None` va rang buoc (12c)
KHONG duoc ep chut nao. Cau "feasible with margin to spare" dung o 5 km va SAI o 15 km.

Script nay do bao vận hành that: voi moi kich thuoc vung, co bao nhieu hat giong co loi
giai thoa (12c), muc vi pham lon nhat neu khong, va can bao nhieu TRAM de kha thi tro lai.

Con so ay khong chi vá mot loi. No cho mot huong dan thiet ke ma bai dang thieu: hai tram
phu duoc toi dau, ba tram toi dau, va tu dau tro di thi phai lam day luoi tram hoac tang
du tru pin.

TU KIEM:
  - doi chung DUONG: o vung nho nhat phai kha thi 20/20 va vi pham bang 0; neu khong thi
    chinh phep do sai chu khong phai he thong.
  - doi chung AM: dat reach = vo cung thi MOI vung phai kha thi 20/20.
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
from solver import uav_states, candidate_sites, strategy_traffic  # noqa: E402

L_KM = [5, 6, 7, 8, 9, 10, 12, 15, 20]
SEEDS = list(range(20))
SEEDS_S = list(range(5))          # quet so tram: it hat giong hon, chi de tim nguong
M, S_MAX, C_TOT = 12, 2, 4
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def chay(L, S_max, C_tot, reach, seeds):
    sc = dict(DEFAULTS); sc["L"] = L; sc["reachability"] = True
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau = tau_charge_of(sc["E_max"], sc["charge_power"])
    V = sc["V"]
    cands = candidate_sites(L, n=3)
    kt, vmax = 0, 0.0
    for sd in seeds:
        states = uav_states(sc, M, sd)
        r = strategy_traffic(states, cands, S_max, C_tot, mu, tau, V, reach)
        if math.isfinite(r["aoi"]):
            kt += 1
        else:
            vmax = max(vmax, max(
                math.dist(states[i]["centroid"], r["sites"][r["assign"][i]]) / V - reach
                for i in range(len(states))))
    return kt, vmax


def main():
    sc0 = dict(DEFAULTS); V = sc0["V"]
    reach = sc0["E_reserve"] * sc0["E_max"] / propulsion_power(V)
    print("Bao van hanh cua rang buoc kha dat tram (12c)\n")
    print("  ngan sach bay MOT CHIEU = E_reserve*E_max/P(V) = %.0f s = %.2f km\n"
          % (reach, reach * V / 1000))
    print("%8s %10s %12s %14s" % ("L (km)", "kha thi", "vi pham (s)", "so tram can"))
    print("-" * 48)
    rows = []
    for Lk in L_KM:
        kt, vmax = chay(Lk * 1000.0, S_MAX, C_TOT, reach, SEEDS)
        can = ""
        if kt < len(SEEDS):
            for S in (3, 4, 5, 6):
                ok, _ = chay(Lk * 1000.0, S, max(C_TOT, S), reach, SEEDS_S)
                if ok == len(SEEDS_S):
                    can = str(S); break
            else:
                can = ">6"
        rows.append(dict(L_km=Lk, feasible_seeds=kt, n_seeds=len(SEEDS),
                         max_violation_s=vmax, stations_needed=can or S_MAX))
        print("%8d %10s %12.0f %14s" % (Lk, "%d/%d" % (kt, len(SEEDS)), vmax,
                                        can or "%d (du)" % S_MAX))

    du = [r for r in rows if r["feasible_seeds"] == len(SEEDS)]
    print("\n  ⭐ voi %d tram, (12c) thoa hoan toan toi L = %d km" % (S_MAX, max(r["L_km"] for r in du)))
    print("     tu do tro len, phep so chinh cua bai chay voi (12c) DA NOI LONG.")

    print("\n== TU KIEM ==")
    kiem(rows[0]["feasible_seeds"] == len(SEEDS) and rows[0]["max_violation_s"] == 0.0,
         "doi chung DUONG: vung nho nhat kha thi %d/%d, vi pham 0" % (len(SEEDS), len(SEEDS)))
    kt_inf, _ = chay(20000.0, S_MAX, C_TOT, float("inf"), SEEDS_S)
    kiem(kt_inf == len(SEEDS_S),
         "doi chung AM: bo rang buoc (reach vo cung) thi vung 20 km kha thi het",
         "%d/%d" % (kt_inf, len(SEEDS_S)))

    p = os.path.join(ROOT, "results", "reach_envelope.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\n=> %s (%d loi). Da ghi results/reach_envelope.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
