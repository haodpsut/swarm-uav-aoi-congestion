"""(12i): rang buoc gian cach giua UAV duoc ep o dau. Cau tra loi trung thuc la: KHONG.

BA nguoi hoi cung mot chuyen:
  R1 diem 3 (vong 1): "how does the solver enforce the feasibility constraints in (12),
      in particular ... inter-UAV separation (12i)?"
  R6 diem 5 (vong 1): "explain how ... the UAV separation constraint (12i) [is] checked
      for each candidate ... If it is not rechecked after the outer placement search,
      describe the method as a heuristic for a relaxed problem rather than a joint
      solver for P0."
  R3 (vong 2): "Please briefly clarify where and how (12i) is checked or enforced."

⛔ SU THAT, doc tu ma: khong co dong nao trong src/ ep gian cach. Khong kiem va cham,
khong khoang cach toi thieu, khong phan tang do cao. (12i) bi NOI LONG hoan toan.

Vi sao no khong the ep duoc o muc truu tuong nay: bo hoach dinh lam viec tren THOI GIAN
CHU KY (t_loop, tau_fly, thoi gian cho sac), khong phan giai vi tri cua tung UAV theo
thoi gian. Hai UAV o hai vung con ke nhau co the o gan nhau tai mot thoi diem nao do ma
mo hinh nay khong nhin thay, vi no khong co truc thoi gian trong chu ky.

Nen script nay KHONG di chung minh (12i) duoc thoa. No do thu do duoc va bao thang:
  - khoang cach NHO NHAT giua diem dung cua hai UAV KHAC NHAU, tren moi seed;
  - bao nhieu cap UAV co diem dung gan hon mot nguong an toan gia dinh;
  - va ghi ro day la khoang cach KHONG GIAN giua duong tuan tra, khong phai kiem va cham
    theo thoi gian.

Con so nay cho phan bien thay chinh xac phep nói lỏng ton bao nhieu, thay vi mot cau
khang dinh khong kiem duoc. Xem [[feedback-tuyen-bo-khong-co-chu-so]].

TU KIEM:
  - doi chung DUONG: khoang cach cua mot UAV voi CHINH NO phai bang 0, neu khong thi
    ham do khoang cach sai.
  - so cap phai dung M(M-1)/2.
"""
import csv
import itertools
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scenario import DEFAULTS                                   # noqa: E402
from field import partition_field                               # noqa: E402
from trajectory import optimize_trajectories                    # noqa: E402

SEEDS = list(range(20))
M = 12
R_C = 200.0
NGUONG = [50.0, 100.0, 200.0]      # nguong an toan gia dinh, met
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def min_giua(a, b):
    return min(math.dist(p, q) for p in a for q in b)


def main():
    sc = dict(DEFAULTS)
    print("Gian cach (12i): do khoang cach KHONG GIAN giua diem dung cua cac UAV\n")
    print("  M = %d, %d seed, ban kinh thu thap r_c = %.0f m" % (M, len(SEEDS), R_C))
    print("  ⛔ (12i) KHONG duoc ep trong bo giai; day la phep do HAU NGHIEM.\n")
    print("%5s | %12s %12s | %s" % ("seed", "min (m)", "trung vi (m)",
                                    "so cap duoi nguong 50/100/200 m"))
    print("-" * 74)
    rows = []
    for sd in SEEDS:
        _, groups = partition_field(sc["K"], sc["L"], M, sd,
                                    clustered=sc.get("clustered", False))
        _, _, wps = optimize_trajectories(groups, R_C, sc["V"], seed=sd,
                                          return_waypoints=True)
        cap = list(itertools.combinations(range(len(wps)), 2))
        d = [min_giua(wps[u], wps[v]) for u, v in cap]
        duoi = [sum(1 for x in d if x < t) for t in NGUONG]
        rows.append(dict(seed=sd, n_pairs=len(cap), min_m=min(d), med_m=st.median(d),
                         mean_m=st.mean(d),
                         **{("n_below_%dm" % int(t)): n for t, n in zip(NGUONG, duoi)}))
        print("%5d | %12.1f %12.1f | %d / %d / %d"
              % (sd, min(d), st.median(d), duoi[0], duoi[1], duoi[2]))

    gmin = min(r["min_m"] for r in rows)
    tong_cap = sum(r["n_pairs"] for r in rows)
    print("\n  ⭐ khoang cach nho nhat tren %d seed x %d cap = %.1f m"
          % (len(rows), rows[0]["n_pairs"], gmin))
    for t in NGUONG:
        n = sum(r["n_below_%dm" % int(t)] for r in rows)
        print("     duoi %3.0f m: %4d / %4d cap  (%.1f%%)" % (t, n, tong_cap,
                                                              100.0 * n / tong_cap))

    print("\n== TU KIEM ==")
    _, groups = partition_field(sc["K"], sc["L"], M, 0,
                                clustered=sc.get("clustered", False))
    _, _, w0 = optimize_trajectories(groups, R_C, sc["V"], seed=0, return_waypoints=True)
    kiem(abs(min_giua(w0[0], w0[0])) < 1e-9,
         "doi chung DUONG: khoang cach mot UAV voi chinh no bang 0")
    kiem(all(r["n_pairs"] == M * (M - 1) // 2 for r in rows),
         "so cap = M(M-1)/2 = %d o moi seed" % (M * (M - 1) // 2))
    kiem(all(r["min_m"] >= 0 for r in rows), "moi khoang cach khong am")

    p = os.path.join(ROOT, "results", "separation_check.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\n=> %s (%d loi). Da ghi results/separation_check.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
