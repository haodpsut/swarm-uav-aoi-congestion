"""Diem 2 cua phan bien: M* co DUY NHAT khong, va gia thiet loi roi rac co dung khong.

Phan bien viet: mot day loi roi rac VAN co the co nhieu nghiem nguyen neu sai phan tien
bang 0 dung tai diem chuyen. Chung minh cu ket luan "unique interior minimizer" ma khong
loai truong hop do.

Script nay KHONG chay mo phong moi. No doc lai duong cong da co
(results/prop1_phys_curves.csv, AoI trung binh theo M cho tung so cong c) va DO ba thu:

  1. so cau hinh c co NHIEU hon mot nghiem nguyen (hoa dung bang) -> tinh duy nhat
  2. khoang cach % tu M* toi lang gieng gan nhat -> hoa co "gan xay ra" khong
  3. so sai phan tien bi GIAM (vi pham loi roi rac), va trong so do bao nhieu cai
     VUOT sai so Monte Carlo -> gia thiet 2 co bi du lieu bac khong

⛔ Diem 3 la cho de tu lua nhat. Duong cong sinh tu mo phong nen sai phan co nhieu.
Dem tran so lan vi pham thi bao gio cung ra vai cai, va noi "co vi pham" cung sai nhu
noi "khong co". Phai so muc vi pham voi sai so chuan cua chinh phep do.
"""
import csv
import math
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")

# So lan lap Monte Carlo cua prop1_phys_curves.csv. Doc tu chinh script sinh ra no
# thay vi go tay, de neu ai doi so lan lap thi sai so chuan o day doi theo.
N_REP_DEFAULT = 20


def n_rep():
    """Boc so lan lap tu prop1_physical.py; that bai thi bao loi chu khong doan."""
    for name in ("prop1_physical.py", "prop1_phys.py"):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        for line in open(p):
            s = line.strip().replace(" ", "")
            for key in ("N_REP=", "N_SEEDS=", "REPS=", "N_TRIALS="):
                if s.startswith(key):
                    try:
                        return int(s[len(key):].split("#")[0])
                    except ValueError:
                        pass
    return N_REP_DEFAULT


def main():
    p = os.path.join(RES, "prop1_phys_curves.csv")
    rows = list(csv.DictReader(open(p)))
    rep = n_rep()

    aoi, sd = defaultdict(dict), defaultdict(dict)
    for x in rows:
        c, M = int(x["c"]), int(x["M"])
        aoi[c][M] = float(x["aoi_mean_s"])
        sd[c][M] = float(x["aoi_std_s"])

    out = []
    for c in sorted(aoi):
        cur = aoi[c]
        Ms = sorted(cur)
        best = min(cur.values())
        arg = [m for m in Ms if abs(cur[m] - best) <= 1e-12]
        mstar = arg[0]
        interior = mstar not in (Ms[0], Ms[-1])

        # khoang cach tuong doi toi lang gieng gan nhat cua M*
        nb = [cur[m] for m in (mstar - 1, mstar + 1) if m in cur]
        sep = min(100.0 * (v - best) / best for v in nb)

        # vi pham loi roi rac, va vi pham VUOT nhieu Monte Carlo
        d = [cur[Ms[i + 1]] - cur[Ms[i]] for i in range(len(Ms) - 1)]
        viol = big = 0
        for i in range(len(d) - 1):
            drop = d[i] - d[i + 1]
            if drop <= 0:
                continue
            viol += 1
            # sai so chuan cua sai phan bac hai: bon so hang doc lap
            se2 = math.sqrt(sum(sd[c][Ms[j]] ** 2 for j in (i, i + 1, i + 2))) / math.sqrt(rep)
            if drop > 2.0 * se2:
                big += 1

        out.append(dict(c=c, M_star=mstar, n_argmin=len(arg), interior=int(interior),
                        sep_pct=sep, n_diff=len(d) - 1, n_violations=viol,
                        n_violations_beyond_mc=big))

    q = os.path.join(RES, "prop1_uniqueness.csv")
    with open(q, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    ties = sum(1 for x in out if x["n_argmin"] > 1)
    inter = sum(x["interior"] for x in out)
    print("=" * 74)
    print("  DIEM 2 — tinh duy nhat cua M* va gia thiet loi roi rac")
    print("=" * 74)
    print("  so lan lap Monte Carlo cua duong cong: %d" % rep)
    for x in out:
        print("   c=%-3d M*=%-3d nghiem=%d %-9s cach lang gieng %.2f%%  "
              "vi pham loi %d/%d (vuot nhieu MC: %d)"
              % (x["c"], x["M_star"], x["n_argmin"],
                 "trong" if x["interior"] else "BIEN", x["sep_pct"],
                 x["n_violations"], x["n_diff"], x["n_violations_beyond_mc"]))
    print()
    print("  cau hinh co nhieu nghiem nguyen : %d/%d" % (ties, len(out)))
    print("  cau hinh co M* NAM TRONG khoang : %d/%d" % (inter, len(out)))
    print("  khoang cach nho nhat toi lang gieng: %.2f%%"
          % min(x["sep_pct"] for x in out))
    print("  vi pham loi VUOT nhieu Monte Carlo : %d tren toan bo %d sai phan bac hai"
          % (sum(x["n_violations_beyond_mc"] for x in out),
             sum(x["n_diff"] for x in out)))
    print("  => da ghi results/prop1_uniqueness.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
