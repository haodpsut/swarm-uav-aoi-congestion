"""9 km / 3 tram: 9 hat giong BI LOAI co khac he thong so voi 11 hat kia khong?

⛔ VI SAO CO TEP NAY. Nguoi doc ngoai 03/10/2026, tieu chi 2: "the 5.8% mean is
conditioned on the proposed method's own feasibility. Where the 9 excluded seeds
sit relative to the 11 matters: if feasibility correlates with easier geometry,
the conditional mean is optimistic."

Do dung hai cau hoi, vi chung KHAC nhau va chi cau thu hai moi de doa con so:

  (A) HINH HOC. Hat bi loai co that su kho phu hon khong? Thong ke: ban kinh phu
      BA tram tot nhat tren luoi ung vien (k-center, k = 3) cua 12 trong tam
      vung con, so voi ngan sach bay mot chieu. Cau nay gan nhu chac chan CO,
      vi kha thi DUOC DINH NGHIA bang ban kinh do: no chi noi cho ta biet huong
      khac nhau la hinh hoc thuan tuy, khong phai do kho cua bai toan AoI.

  (B) THIEN LECH CHON MAU. Day moi la cau an. Tat kiem kha thi di (che do ly
      tuong hoa) de MOI hat giong deu cho ra mot thiet ke, roi hoi: loi ich cua
      phuong phap de xuat so voi ablation tren 9 hat BI LOAI co khac tren 11 hat
      GIU LAI khong? Neu xap xi nhau thi 5,8% khong phai con so duoc loc cho dep.
      Neu 9 hat kia cho loi ich THAP hon nhieu thi phai khai rang 5,8% la lac quan.

Doi chung AM: tron nhan 11/9 ngau nhien 2000 lan va do lai chenh lech cua (B).
Neu chenh lech that nam gon trong phan bo tron thi khong co bang chung thien lech.

    python3 experiments/chan_doan_hat_bi_loai.py
"""
import itertools
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from scenario import DEFAULTS                                  # noqa: E402
from solver import solve, candidate_sites, uav_states          # noqa: E402
from energy import propulsion_power                            # noqa: E402

L_KM = 9.0
S_MAX = 3
C_TOT = 4
M = 12
SEEDS = list(range(20))
N_TRON = 2000


def ban_kinh_phu(centroids, cands, k):
    """Ban kinh k-center nho nhat tren luoi ung vien: min qua moi bo k site cua
    (max qua moi trong tam cua khoang cach toi site gan nhat)."""
    tot = float("inf")
    for bo in itertools.combinations(range(len(cands)), k):
        r = max(min(math.dist(c, cands[s]) for s in bo) for c in centroids)
        tot = min(tot, r)
    return tot


def tb(v):
    return sum(v) / len(v) if v else float("nan")


def main():
    sc = dict(DEFAULTS)
    sc["L"] = L_KM * 1000.0
    cands = candidate_sites(sc["L"], n=3)
    budget_s = sc["E_reserve"] * sc["E_max"] / propulsion_power(sc["V"])
    budget_m = budget_s * sc["V"]

    # ---- ai kha thi: chay dung cau hinh cua thi nghiem 9 km ----
    sc_kt = dict(sc, reachability=True)
    kha_thi = [sd for sd in SEEDS
               if math.isfinite(solve(sc_kt, M, sd, "proposed", cands=cands,
                                      S_max=S_MAX, C_tot=C_TOT))]
    bi_loai = [sd for sd in SEEDS if sd not in kha_thi]
    print("== 9 km / 3 tram: 9 hat bi loai co khac he thong khong? ==")
    print("   ngan sach bay mot chieu: %.0f s = %.2f km" % (budget_s, budget_m / 1000.0))
    print("   kha thi (%d): %s" % (len(kha_thi), kha_thi))
    print("   bi loai (%d): %s\n" % (len(bi_loai), bi_loai))

    # ---- (A) hinh hoc ----
    print("   (A) HINH HOC: ban kinh phu 3 tram tot nhat tren luoi ung vien")
    bk = {}
    for sd in SEEDS:
        st = uav_states(sc, M, sd, trajectory="cetsp")
        bk[sd] = ban_kinh_phu([s["centroid"] for s in st], cands, S_MAX)
    bk_kt = [bk[s] / 1000.0 for s in kha_thi]
    bk_bl = [bk[s] / 1000.0 for s in bi_loai]
    print("       kha thi : trung binh %.2f km, max %.2f km" % (tb(bk_kt), max(bk_kt)))
    print("       bi loai : trung binh %.2f km, min %.2f km" % (tb(bk_bl), min(bk_bl)))
    print("       nguong  : %.2f km" % (budget_m / 1000.0))
    tach = max(bk_kt) < budget_m / 1000.0 <= min(bk_bl)
    print("       tach sach boi nguong: %s" % ("CO" if tach else "KHONG"))

    # ---- (B) thien lech chon mau ----
    print("\n   (B) THIEN LECH: tat kiem kha thi, so loi ich tren hai nhom")
    sc_lt = dict(sc, reachability=False)
    loi = {}
    for sd in SEEDS:
        a = solve(sc_lt, M, sd, "proposed", cands=cands, S_max=S_MAX, C_tot=C_TOT)
        b = solve(sc_lt, M, sd, "no_cetsp", cands=cands, S_max=S_MAX, C_tot=C_TOT)
        if not (math.isfinite(a) and math.isfinite(b) and b > 0):
            print("       ⛔ hat %d van khong cho so o che do ly tuong hoa" % sd)
            return 1
        loi[sd] = 100.0 * (b - a) / b
    g_kt, g_bl = [loi[s] for s in kha_thi], [loi[s] for s in bi_loai]
    chenh = tb(g_kt) - tb(g_bl)
    print("       11 hat GIU LAI : loi ich trung binh %+.2f%%" % tb(g_kt))
    print("       9 hat BI LOAI  : loi ich trung binh %+.2f%%" % tb(g_bl))
    print("       chenh lech     : %+.2f diem phan tram" % chenh)

    # doi chung AM: tron nhan
    rng = random.Random(12345)
    tat = list(SEEDS)
    dem = 0
    for _ in range(N_TRON):
        rng.shuffle(tat)
        a = [loi[s] for s in tat[:len(kha_thi)]]
        b = [loi[s] for s in tat[len(kha_thi):]]
        if abs(tb(a) - tb(b)) >= abs(chenh):
            dem += 1
    p = (dem + 1) / (N_TRON + 1)
    print("       doi chung AM (tron nhan %d lan): p = %.3f" % (N_TRON, p))
    print("       => %s" % ("CO bang chung thien lech, phai khai 5,8%% la lac quan"
                            if p < 0.05 else
                            "KHONG co bang chung thien lech o muc 5%"))

    out = os.path.join(ROOT, "results", "chan_doan_9km_hat_bi_loai.txt")
    with open(out, "w") as f:
        f.write("kha_thi=%s\nbi_loai=%s\n" % (kha_thi, bi_loai))
        f.write("bk_kha_thi_max_km=%.4f\nbk_bi_loai_min_km=%.4f\nnguong_km=%.4f\n"
                % (max(bk_kt), min(bk_bl), budget_m / 1000.0))
        f.write("loi_kha_thi_pc=%.4f\nloi_bi_loai_pc=%.4f\nchenh_pp=%.4f\np_tron=%.4f\n"
                % (tb(g_kt), tb(g_bl), chenh, p))
    print("\n   da ghi %s" % os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
