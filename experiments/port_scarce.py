"""R3-2 (vong 1): quy mo lon voi SO CONG NHO CO DINH, khong cho cong tang theo doi.

Phan bien 3 vong 1:
    "In the large-scale M=60 experiment the number of charging ports grows linearly with
     the number of UAVs, one port per three UAVs, so the system is resource-rich, which
     contradicts the contention scenario the paper emphasizes. It is recommended to add
     an experiment with a small fixed number of ports to observe how performance degrades
     under extreme scarcity."

Ho dung. `scale.py` dat C_tot = round(M/3), tuc ty le cong tren UAV GIU NGUYEN khi doi
lon len, nen do khong phai thi nghiem ve tranh chap ma la thi nghiem ve mo rong can doi.
O day giu C_tot CO DINH va nho trong khi M tang, tuc ty le UAV tren cong tang tuyen tinh,
va do xem AoI dinh xuong cap the nao.

Day cung la che do ma Menh de 1 du doan: vuot nguong tac nghen thi them UAV lam AoI
TE DI. Neu so do khong thay dieu do o ngan sach cong co dinh thi chinh Menh de 1 co van de,
nen thi nghiem nay vua tra loi phan bien vua la mot phep thu co the BAC duoc ly thuyet.

TU KIEM:
  - doi chung DUONG: o C_tot lon (bang so UAV) thi khong duoc co tac nghen, tuc AoI phai
    GIAM don dieu theo M. Neu no van tang thi phep do sai chu khong phai he tac nghen.
  - moi cau hinh phai kha thi (AoI huu han).
"""
import csv
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scenario import DEFAULTS                                   # noqa: E402
from solver import solve, candidate_sites                       # noqa: E402

M_VALUES = [20, 30, 40, 50, 60]
CAP_FIXED = [4, 6]          # ngan sach cong CO DINH, nho
SEEDS = list(range(10))
S_MAX, L = 2, 20000.0
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def chay(M, C_tot, method, cands):
    sc = dict(DEFAULTS)
    sc["L"] = L
    sc["K"] = 8 * M
    v = [solve(sc, M, sd, method, cands=cands, S_max=S_MAX, C_tot=C_tot) for sd in SEEDS]
    return st.mean(v) / 60.0, st.pstdev(v) / 60.0, min(v) / 60.0, max(v) / 60.0


def main():
    cands = candidate_sites(L, n=4)
    print("Khan hiem cong: C_tot CO DINH trong khi M tang (L=%.0f km, K=8M, %d seed)\n"
          % (L / 1000, len(SEEDS)))
    rows = []
    for C_tot in CAP_FIXED:
        print("== C_tot = %d cong co dinh ==" % C_tot)
        print("%4s %5s %8s | %9s %8s | %9s | %s"
              % ("M", "K", "UAV/cong", "de xuat", "do lech", "tram gop", "AoI dinh xau nhat"))
        print("-" * 78)
        for M in M_VALUES:
            a, sd, lo, hi = chay(M, C_tot, "proposed", cands)
            b, _, _, _ = chay(M, C_tot, "single_station", cands)
            rows.append(dict(C_tot=C_tot, M=M, K=8 * M, uav_per_port=M / C_tot,
                             proposed_min=a, proposed_sd=sd, proposed_worst=hi,
                             single_min=b))
            print("%4d %5d %8.1f | %9.1f %8.2f | %9.1f | %9.1f"
                  % (M, 8 * M, M / C_tot, a, sd, b, hi))
        sub = [r for r in rows if r["C_tot"] == C_tot]
        d = sub[-1]["proposed_min"] / sub[0]["proposed_min"]
        print("   => tu M=%d len M=%d, AoI dinh nhan %.2f lan (ty le UAV/cong %.1f -> %.1f)\n"
              % (sub[0]["M"], sub[-1]["M"], d, sub[0]["uav_per_port"], sub[-1]["uav_per_port"]))

    # doi chung DUONG: ngan sach cong DOI DAO thi khong duoc co tac nghen
    print("== doi chung: C_tot = M, tuc moi UAV mot cong, khong the tac nghen ==")
    doi_dao = []
    for M in (20, 40, 60):
        a, _, _, _ = chay(M, M, "proposed", cands)
        doi_dao.append((M, a))
        print("   M=%2d  C_tot=%2d  AoI dinh %.1f phut" % (M, M, a))
    kiem(all(doi_dao[i + 1][1] <= doi_dao[i][1] + 1e-9 for i in range(len(doi_dao) - 1)),
         "doi chung: cong doi dao thi AoI GIAM don dieu theo M",
         " -> ".join("%.1f" % x[1] for x in doi_dao))
    kiem(all(r["proposed_min"] > 0 and r["single_min"] > 0 for r in rows),
         "moi cau hinh kha thi, AoI huu han")

    p = os.path.join(ROOT, "results", "port_scarce.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\n=> %s (%d loi). Da ghi results/port_scarce.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
