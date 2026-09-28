"""R2-3 (vong 1): cho MOI phuong phap tu chon co doi cua no, roi moi so.

Phan bien 2 vong 1:
    "The fairness of fixing the swarm size at M=12 deserves further discussion. The
     authors choose M=12 because it is the optimal swarm size under their own allocation
     model with four charging ports. The optimal swarm size may differ across schemes;
     each method should be allowed to optimize its own swarm size."

Lo ngai nay dung ve nguyen tac: so hai phuong phap tai MOT co doi do CHINH MINH chon la
cho doi thu chay o diem khong toi uu cua no. Phep do dung la: quet M cho TUNG phuong phap,
lay M* rieng cua no, roi so MOI phuong phap tai M* CUA NO.

⛔ Ket qua co the BAT LOI cho bai, va neu vay thi phai bao nguyen ven. Neu mot moc chuan
o M* rieng thu hep duoc khoang cach, con so 'up to X%' trong bai phai thu hep theo.
Xem [[feedback-headline-tinh-tren-mot-phan-doi-thu]].

TU KIEM:
  - moi phuong phap phai co M* NAM TRONG luoi, khong cham bien. Cham bien nghia la cuc tri
    bi kiem duyet va khong duoc doc nhu cuc tri trong (dung loi R6-7a da canh bao).
  - so sanh tai M* rieng va tai M=12 phai cung dau ve nguoi thang, neu khac thi phai bao.
"""
import csv
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scenario import DEFAULTS, tau_charge_of                    # noqa: E402
from solver import solve, candidate_sites                       # noqa: E402

# ⛔ Ban dau toi dat luoi nay tren DEFAULTS, tuc L = 5 km. SAI: phep so chinh cua bai
# (bang ablation) chay o L = 15 km, M = 12. Do o 5 km thi khong noi duoc gi ve lua chon
# M = 12 cua bai. Phai do DUNG cau hinh minh dang tuyen bo.
# Luoi cung mo rong xuong 4 vi lan chay dau M* cua round-robin cham bien duoi (M=6),
# tuc cuc tri bi kiem duyet, dung loi R6-7a canh bao.
L_SO_SANH = 15000.0            # giong ablation() trong joint_solver.py
M_GRID = [4, 6, 8, 10, 12, 14, 16, 20]
SEEDS = list(range(20))
METHODS = ["proposed", "no_cetsp", "coverage", "roundrobin", "single_station"]
M_BAI = 12                     # co doi bai dang dung cho MOI phuong phap
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def main():
    sc = dict(DEFAULTS)
    sc["L"] = L_SO_SANH
    cands = candidate_sites(sc["L"], n=3)
    print("Moi phuong phap tu chon co doi (L = %.0f km, luoi M = %s, %d seed)\n"
          % (L_SO_SANH/1000, M_GRID, len(SEEDS)))
    bang = {}
    rows = []
    for m in METHODS:
        print("  %-16s" % m, end="", flush=True)
        cot = {}
        for M in M_GRID:
            v = [solve(sc, M, sd, m, cands=cands, S_max=2, C_tot=4) for sd in SEEDS]
            cot[M] = st.mean(v) / 60.0
            rows.append(dict(method=m, M=M, aoi_min=cot[M], sd_min=st.pstdev(v) / 60.0))
            print(" %6.1f" % cot[M], end="", flush=True)
        bang[m] = cot
        print("")
    print("  %-16s %s" % ("", " ".join("%6d" % M for M in M_GRID)))

    print("\n%-18s %8s %10s %10s %12s" % ("phuong phap", "M* rieng", "AoI tai M*",
                                          "AoI tai M=%d" % M_BAI, "M* cham bien?"))
    print("-" * 64)
    tom = {}
    for m in METHODS:
        Ms = min(bang[m], key=lambda M: bang[m][M])
        bien = Ms in (M_GRID[0], M_GRID[-1])
        tom[m] = dict(mstar=Ms, aoi_star=bang[m][Ms], aoi_bai=bang[m][M_BAI], bien=bien)
        print("%-18s %8d %10.1f %10.1f %12s"
              % (m, Ms, bang[m][Ms], bang[m][M_BAI], "⛔ CO" if bien else "khong"))

    p0, p1 = tom["proposed"]["aoi_star"], tom["proposed"]["aoi_bai"]
    print("\n%-26s %12s %12s" % ("so voi de xuat", "tai M* rieng", "tai M=%d" % M_BAI))
    print("-" * 52)
    for m in METHODS:
        if m == "proposed":
            continue
        g_star = 100.0 * (tom[m]["aoi_star"] - p0) / tom[m]["aoi_star"]
        g_bai = 100.0 * (tom[m]["aoi_bai"] - p1) / tom[m]["aoi_bai"]
        tom[m]["gain_star"], tom[m]["gain_bai"] = g_star, g_bai
        print("%-26s %11.1f%% %11.1f%%   %s"
              % (m, g_star, g_bai, "loi the GIU" if g_star > 0 else "⛔ loi the MAT"))

    print("\n== TU KIEM ==")
    cham = [m for m in METHODS if tom[m]["bien"]]
    kiem(not cham, "khong phuong phap nao co M* cham bien luoi",
         "cham bien: " + ", ".join(cham) if cham else "")
    doi_dau = [m for m in METHODS if m != "proposed"
               and (tom[m]["gain_star"] > 0) != (tom[m]["gain_bai"] > 0)]
    kiem(not doi_dau, "nguoi thang khong doi khi cho moi ben tu chon co doi",
         "doi dau: " + ", ".join(doi_dau) if doi_dau else "")

    q = os.path.join(ROOT, "results", "per_method_mstar.csv")
    with open(q, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    q2 = os.path.join(ROOT, "results", "per_method_mstar_summary.csv")
    with open(q2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "mstar", "aoi_at_mstar_min", "aoi_at_M%d_min" % M_BAI,
                    "gain_vs_proposed_at_mstar_pct", "gain_vs_proposed_at_M%d_pct" % M_BAI])
        for m in METHODS:
            t = tom[m]
            w.writerow([m, t["mstar"], "%.6f" % t["aoi_star"], "%.6f" % t["aoi_bai"],
                        "" if m == "proposed" else "%.6f" % t["gain_star"],
                        "" if m == "proposed" else "%.6f" % t["gain_bai"]])
    print("\n=> %s (%d loi). Da ghi results/per_method_mstar.csv va _summary.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
