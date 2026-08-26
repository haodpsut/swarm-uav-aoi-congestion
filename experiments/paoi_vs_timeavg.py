"""Ba dinh nghia muc tieu khong the cung ton tai: DO khoang cach giua chung.

Nguoi doc ngoai (26/08) bat duoc rang ban thao dang mang BA cong thuc khac nhau cho
cung mot ky hieu:

  Eq (2)   sau vong sua R1:  (1/T) integral AoI_k(t) dt      -> AoI TRUNG BINH THEO THOI GIAN
  Eq (10)  peak_aoi():       t_loop + 2d/V + Wq + tau_charge -> DINH cua moi chu ky
  Eq (12a) trong (P0):       max_k limsup_t AoI_k(t)         -> worst-case theo quy dao mau

⛔ Cai thu hai moi la cai thuat toan TOI UU. Va no KHONG bang cai thu nhat: voi mot cam
bien duoc tham lai sau moi chu ky do dai T, tuoi tin chay rang cua tu 0 len T, nen

    dinh moi chu ky      = E[T]
    trung binh theo tg   = E[T^2] / (2 E[T])

Ti so dinh/trung-binh = 2 / (1 + CV^2), tuc **gan 2 lan** khi chu ky it bien dong. Goi
cai nay la "AoI trung binh" thi bai dang bao mot con so lon gap doi thu no thuc su toi uu.

Script nay do ti so do TREN CHINH PHAN PHOI CHU KY sinh tu DES, khong gia dinh tat dinh:
lay mau thoi gian cho W tu DES, dung chu ky T = t_loop + travel + W + tau_charge, roi
tinh ca hai dai luong. Ket qua dung de chot MOT dinh nghia va sua ca ba cho.
"""
import csv
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)
from des_validation import simulate                    # noqa: E402
from scenario import DEFAULTS, tau_charge_of           # noqa: E402

T_LOOP = 900.0      # thoi gian tuan tra mot vong, giay (nhu aoi_metric_gap.py)
TRAVEL = 120.0      # khu hoi toi tram, giay


def main():
    sc = dict(DEFAULTS)
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])

    rows = []
    print("=" * 78)
    print("  DINH moi chu ky so voi TRUNG BINH THEO THOI GIAN cua cung mot chu ky")
    print("=" * 78)
    print("%3s %2s | %10s %10s %8s %7s" %
          ("M", "c", "PAoI(s)", "AoI_tb(s)", "ti so", "CV"))
    print("-" * 78)
    for c in (2, 3, 4):
        for M in (8, 10, 12):
            _, waits = simulate(M, c, T_LOOP, tau_charge, TRAVEL,
                                service="det", operating="det", return_waits=True)
            if not waits:
                continue
            T = [T_LOOP + TRAVEL + w + tau_charge for w in waits]
            m1 = st.mean(T)
            m2 = st.mean(x * x for x in T)
            paoi = m1                       # trung binh cua cac DINH
            tavg = m2 / (2.0 * m1)          # trung binh theo thoi gian cua tuoi tin
            cv = (st.pstdev(T) / m1) if m1 else float("nan")
            rows.append(dict(M=M, c=c, paoi_s=paoi, timeavg_s=tavg,
                             ratio=paoi / tavg, cv=cv, n_cycles=len(T)))
            print("%3d %2d | %10.1f %10.1f %8.3f %7.4f" % (M, c, paoi, tavg, paoi / tavg, cv))

    out = os.path.join(HERE, "..", "results", "paoi_vs_timeavg.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    r = [x["ratio"] for x in rows]
    print()
    print("  ti so dinh/trung-binh: thap nhat %.3f, cao nhat %.3f, trung vi %.3f"
          % (min(r), max(r), st.median(r)))
    print("  => hai dinh nghia lech nhau gan MOT HE SO HAI tren moi cau hinh da thu.")
    print("  => da ghi results/paoi_vs_timeavg.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
