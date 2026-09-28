"""R5 diem 7: cham thiet ke CUOI CUNG cua MOI phuong phap bang MOT DES CHUNG.

Phan bien 5, diem 7 vong 1:
    "the main results appear to use the analytic M/M/c//N delay rather than evaluating
     every final design with a near-deterministic DES ... a single common DES applied
     to the final design of EVERY method ... comparison of the design chosen by the
     analytic model against the DES-preferred design ... Without these, the paper only
     shows that the method wins under its own analytic surrogate."

Loi buoc toi nay dung va no la lo ngai nang nhat trong ca vong. Bai chon thiet ke bang
cong thuc hang doi nguon huu han, roi bao thu hang cung bang chinh cong thuc do. Neu
cong thuc ay lech he thong theo huong co loi cho mot kieu thiet ke thi ca bang ket qua
chi chung minh duoc mot dieu: phuong phap thang duoi dai dien giai tich cua chinh no.

CACH LAM. Voi moi hat giong va moi phuong phap:
  1. lay THIET KE CUOI (vi tri tram, chia cong, phep gan) dung bang chinh cac ham bo giai;
  2. voi TUNG tram mo: chay DES gan tat dinh (operating=det, service=det) voi N_s UAV
     duoc gan va c_s cong, lay thoi gian cho THAT;
  3. tinh lai AoI dinh bang cong thuc (14) nhung THAY thoi gian cho giai tich bang thoi
     gian cho cua DES;
  4. so THU HANG duoi hai thuoc do.

Day la MOT DES duy nhat, cung tham so, cham moi phuong phap nhu nhau. Khong phuong phap
nao duoc cham bang mo hinh rieng cua no.

⛔ Ket qua co the bat loi. Neu thu hang doi thi phai bao thang va thu hep tuyen bo.

TU KIEM:
  - doi chung DUONG: chay lai buoc 3 voi thoi gian cho GIAI TICH phai tai lap dung AoI ma
    bo giai bao. Neu khong trung thi buoc tinh lai cua toi sai, chu khong phai DES sai.
  - moi tram mo phai co it nhat mot UAV va it nhat mot cong.
"""
import csv
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
from scenario import DEFAULTS, tau_charge_of                         # noqa: E402
from energy import propulsion_power                                  # noqa: E402
from queue_model import finite_source_wq                             # noqa: E402
from solver import (uav_states, candidate_sites, strategy_traffic,   # noqa: E402
                    strategy_coverage, peak_aoi)
from des_validation import simulate                                  # noqa: E402

SEEDS = list(range(20))
M, S_MAX, C_TOT, L = 12, 2, 4, 15000.0
DES_SEEDS = list(range(4))
METHODS = ["proposed", "no_cetsp", "coverage", "roundrobin", "single_station"]
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def thiet_ke(sc, sd, method, cands, mu, tau, V, reach):
    """Tra ve (states, sites, ports, assign) cua thiet ke CUOI cung."""
    traj = "nn" if method == "no_cetsp" else "cetsp"
    states = uav_states(sc, M, sd, trajectory=traj)
    if method in ("proposed", "no_cetsp"):
        r = strategy_traffic(states, cands, S_MAX, C_TOT, mu, tau, V, reach)
        return states, r["sites"], r["ports"], r["assign"]
    if method == "coverage":
        r = strategy_coverage(states, cands, S_MAX, C_TOT, mu, tau, V, reach)
        return states, r["sites"], r["ports"], r["assign"]
    if method == "single_station":
        return states, [(sc["L"] / 2.0, sc["L"] / 2.0)], [C_TOT], [0] * len(states)
    if method == "roundrobin":
        r = strategy_coverage(states, cands, S_MAX, C_TOT, mu, tau, V, reach)
        return states, r["sites"], r["ports"], [i % S_MAX for i in range(len(states))]
    raise ValueError(method)


def aoi_voi_wait(states, sites, ports, assign, V, tau, wait_fn):
    """Cong thuc (14) nhung thoi gian cho do wait_fn cung cap cho tung tram."""
    peak = 0.0
    for s in range(len(sites)):
        idx = [i for i, a in enumerate(assign) if a == s]
        if not idx:
            continue
        tau_fly_mean = st.mean(states[i]["tau_fly"] for i in idx)
        mean_travel = st.mean(2.0 * math.dist(states[i]["centroid"], sites[s]) / V
                              for i in idx)
        w = wait_fn(len(idx), ports[s], tau_fly_mean, mean_travel)
        for i in idx:
            d = math.dist(states[i]["centroid"], sites[s])
            peak = max(peak, states[i]["t_loop"] + 2.0 * d / V + w + tau)
    return peak


def main():
    sc = dict(DEFAULTS); sc["L"] = L
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau = tau_charge_of(sc["E_max"], sc["charge_power"])
    V = sc["V"]
    reach = None
    cands = candidate_sites(sc["L"], n=3)

    def w_giai_tich(n, c, tau_fly_mean, mean_travel):
        w, _, _, _ = finite_source_wq(n, c, tau_fly_mean + mean_travel, tau)
        return w

    def w_des(n, c, tau_fly_mean, mean_travel):
        # MOT DES chung: gan tat dinh ca van hanh lan sac, trung binh tren DES_SEEDS.
        return st.mean(simulate(n, c, tau_fly_mean, tau, mean_travel / 2.0,
                                service="det", operating="det", seed=ds)
                       for ds in DES_SEEDS)

    print("MOT DES CHUNG cham thiet ke cuoi cua %d phuong phap (L=%.0f km, M=%d, %d seed)\n"
          % (len(METHODS), L / 1000, M, len(SEEDS)))
    rows = []
    for sd in SEEDS:
        for m in METHODS:
            states, sites, ports, assign = thiet_ke(sc, sd, m, cands, mu, tau, V, reach)
            a_ana = aoi_voi_wait(states, sites, ports, assign, V, tau, w_giai_tich)
            a_des = aoi_voi_wait(states, sites, ports, assign, V, tau, w_des)
            a_sol = peak_aoi(states, sites, ports, assign, mu, tau, V, reach)
            rows.append(dict(seed=sd, method=m, aoi_analytic_s=a_ana,
                             aoi_des_s=a_des, aoi_solver_s=a_sol))
        print("\r  seed %2d/%d" % (sd + 1, len(SEEDS)), end="", flush=True)
    print("")

    print("\n%-18s %12s %12s %10s" % ("phuong phap", "giai tich", "DES chung", "chenh"))
    print("-" * 56)
    tb = {}
    for m in METHODS:
        sub = [r for r in rows if r["method"] == m]
        a = st.mean(r["aoi_analytic_s"] for r in sub) / 60.0
        d = st.mean(r["aoi_des_s"] for r in sub) / 60.0
        tb[m] = (a, d)
        print("%-18s %12.2f %12.2f %9.1f%%" % (m, a, d, 100.0 * (a - d) / d))

    xh_ana = sorted(METHODS, key=lambda m: tb[m][0])
    xh_des = sorted(METHODS, key=lambda m: tb[m][1])
    print("\n  thu hang duoi GIAI TICH : %s" % " < ".join(xh_ana))
    print("  thu hang duoi DES CHUNG : %s" % " < ".join(xh_des))
    print("  => thu hang %s" % ("GIU NGUYEN" if xh_ana == xh_des else "⛔ DA DOI"))

    # thang thua theo tung hat giong, duoi DES
    thang = 0
    for sd in SEEDS:
        sub = {r["method"]: r["aoi_des_s"] for r in rows if r["seed"] == sd}
        if min(sub, key=sub.get) == "proposed":
            thang += 1
    print("  duoi DES chung, de xuat tot nhat o %d/%d hat giong" % (thang, len(SEEDS)))

    print("\n== TU KIEM ==")
    lech = [abs(r["aoi_analytic_s"] - r["aoi_solver_s"]) for r in rows]
    kiem(max(lech) < 1e-6,
         "doi chung DUONG: tinh lai bang thoi gian cho GIAI TICH tai lap dung AoI cua bo giai",
         "lech lon nhat %.2e s" % max(lech))
    kiem(all(r["aoi_des_s"] > 0 for r in rows), "moi AoI duoi DES deu duong")
    kiem(len(rows) == len(SEEDS) * len(METHODS),
         "du %d dong" % (len(SEEDS) * len(METHODS)))

    p = os.path.join(ROOT, "results", "common_des.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    q = os.path.join(ROOT, "results", "common_des_summary.csv")
    with open(q, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "aoi_analytic_min", "aoi_des_min", "rank_analytic",
                    "rank_des", "proposed_wins_des"])
        for m in METHODS:
            w.writerow([m, "%.6f" % tb[m][0], "%.6f" % tb[m][1],
                        xh_ana.index(m) + 1, xh_des.index(m) + 1,
                        thang if m == "proposed" else ""])
    print("\n=> %s (%d loi). Da ghi results/common_des.csv va _summary.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
