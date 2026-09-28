"""R6-7(d): bao HO so sanh dung cach, khong chi mot p-value.

Phan bien 6, diem 7(d) vong 1:
    "report confidence intervals or error bars, effect sizes, whether Wilcoxon is one-
     or two-sided, and a multiple-comparison correction; p-values alone are insufficient"

VI SAO CAN. Bang II so phuong phap de xuat voi NAM moc cung mot luc (no-CETSP, coverage,
round-robin, single-station, single-UAV). Kiem dinh tung cap roi bao tung p-value la bo
qua chuyen da so sanh: voi nam phep thu o muc 0.05, xac suat co it nhat mot duong tinh
gia da la 1-(0.95)^5 = 23%. Nen phai hieu chinh theo HO. Dung Holm vi no chat hon
Bonferroni ma khong can gia thiet doc lap.

VA p-value KHONG PHAI thu quan trong nhat. Voi 20 cap, kiem dinh dau hai phia co SAN
2/2^20 = 1.9e-6; cham san chi co nghia ca 20 cap cung dau, khong noi gi ve DO LON. Nen
moi dong deu bao kem: hieu ung trung binh va trung vi, khoang tin cay bootstrap, so cap
thang/thua/hoa, va HAT GIONG XAU NHAT. Xem [[feedback-p-value-do-lap-lai]].

R5 diem 7 cung doi "mean, standard deviation, confidence interval and WORST-SEED result",
nen cot worst_seed o day tra loi ca hai nguoi.

TU KIEM (doi chung duong + am):
  - doi chung AM: so phuong phap de xuat voi CHINH NO phai cho hieu ung 0 va p = 1.
  - doi chung DUONG: mot cot gia bang chinh no cong mot hang so duong phai bi bat.
  - p sau Holm phai LON HON HOAC BANG p tho, voi moi dong.
"""
import csv
import math
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from scipy.stats import wilcoxon                                    # noqa: E402

B_BOOT, SEED_BOOT = 20000, 12345
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def doc(ten):
    with open(os.path.join(ROOT, "results", ten)) as f:
        return list(csv.DictReader(f))


def boot_ci(v, B=B_BOOT, seed=SEED_BOOT, a=0.05):
    rng = random.Random(seed)
    n = len(v)
    m = sorted(st.mean(rng.choices(v, k=n)) for _ in range(B))
    return m[int(a / 2 * B)], m[int((1 - a / 2) * B)]


def so_sanh(ten, de_xuat, moc):
    """Mot dong cua ho: de_xuat so voi moc, ghep cap theo hat giong."""
    assert len(de_xuat) == len(moc)
    # hieu ung = phan tram AoI GIAM duoc so voi moc (duong = de xuat tot hon)
    eff = [100.0 * (b - a) / b for a, b in zip(de_xuat, moc)]
    d = [b - a for a, b in zip(de_xuat, moc)]
    if all(abs(x) < 1e-12 for x in d):
        p = 1.0
    else:
        try:
            p = float(wilcoxon(de_xuat, moc, alternative="two-sided", method="exact").pvalue)
        except Exception:
            p = float(wilcoxon(de_xuat, moc, alternative="two-sided").pvalue)
    lo, hi = boot_ci(eff)
    i_xau = min(range(len(eff)), key=lambda i: eff[i])
    return dict(moc=ten, n=len(eff), thang=sum(1 for x in d if x > 1e-12),
                hoa=sum(1 for x in d if abs(x) <= 1e-12),
                thua=sum(1 for x in d if x < -1e-12),
                eff_mean=st.mean(eff), eff_med=st.median(eff),
                eff_sd=st.pstdev(eff), ci_lo=lo, ci_hi=hi,
                worst_seed=i_xau, worst_eff=eff[i_xau], p_raw=p)


def holm(rows):
    """Holm-Bonferroni tren ho. p_holm khong giam theo thu tu tang cua p_raw."""
    idx = sorted(range(len(rows)), key=lambda i: rows[i]["p_raw"])
    m = len(rows)
    truoc = 0.0
    for r, i in enumerate(idx):
        adj = min(1.0, (m - r) * rows[i]["p_raw"])
        adj = max(adj, truoc)          # ep khong giam, dung dinh nghia Holm
        rows[i]["p_holm"] = adj
        truoc = adj
    return rows


def main():
    ab = doc("joint_ablation.csv")
    su = doc("single_uav_baseline.csv")
    prop = [float(x["proposed"]) for x in ab]
    ho = [("No CETSP (nearest-neighbour patrol)", [float(x["no_cetsp"]) for x in ab]),
          ("Single pooled station", [float(x["single_station"]) for x in ab]),
          ("Coverage-optimal placement", [float(x["coverage"]) for x in ab]),
          ("Round-robin assignment", [float(x["roundrobin"]) for x in ab])]
    # single-UAV o tep khac, don vi PHUT; quy ve cung don vi bang ty le, khong tron
    if len(su) == len(ab):
        ho.append(("Single UAV", [float(x["single_uav_min"]) for x in su]))
        prop_su = [float(x["swarm_min"]) for x in su]
    else:
        prop_su = None

    rows = []
    for ten, moc in ho:
        p = prop_su if ten == "Single UAV" and prop_su else prop
        rows.append(so_sanh(ten, p, moc))
    rows = holm(rows)

    print("== HO %d PHEP SO SANH GHEP CAP, hieu chinh Holm ==\n" % len(rows))
    print("%-36s %5s %8s %8s %16s %10s %10s %8s"
          % ("moc so sanh", "n", "hieu %", "trung vi", "KTC 95%", "p tho", "p Holm", "xau nhat"))
    print("-" * 112)
    for r in rows:
        print("%-36s %5d %8.2f %8.2f  [%6.2f,%6.2f] %10.2g %10.2g %7.2f%% (seed %d)"
              % (r["moc"], r["n"], r["eff_mean"], r["eff_med"], r["ci_lo"], r["ci_hi"],
                 r["p_raw"], r["p_holm"], r["worst_eff"], r["worst_seed"]))
    print("\n   kiem dinh: Wilcoxon signed-rank GHEP CAP, HAI PHIA, dang chinh xac;")
    print("   khoang tin cay: bootstrap phan vi %d lan, hat giong %d;" % (B_BOOT, SEED_BOOT))
    print("   hieu chinh: Holm-Bonferroni tren ho %d phep." % len(rows))

    # ---- tu kiem ----
    print("\n== TU KIEM ==")
    kiem(all(r["p_holm"] >= r["p_raw"] - 1e-15 for r in rows),
         "p sau Holm >= p tho o moi dong")
    am = so_sanh("doi chung AM: chinh no", prop, prop)
    kiem(abs(am["eff_mean"]) < 1e-12 and am["p_raw"] == 1.0,
         "doi chung AM: so voi chinh no cho hieu ung 0 va p=1",
         "eff=%.2g p=%.3g" % (am["eff_mean"], am["p_raw"]))
    gia = [x * 1.10 for x in prop]
    duong = so_sanh("doi chung DUONG: +10%", prop, gia)
    kiem(duong["p_raw"] < 0.01 and abs(duong["eff_mean"] - 100 * (1 - 1 / 1.10)) < 0.01,
         "doi chung DUONG: chenh 10% bi bat dung do lon",
         "eff=%.3f%% p=%.2g" % (duong["eff_mean"], duong["p_raw"]))
    kiem(all(r["n"] == 20 for r in rows), "moi dong du 20 cap")
    kiem(all(r["thang"] + r["hoa"] + r["thua"] == r["n"] for r in rows),
         "thang + hoa + thua = n o moi dong")

    p = os.path.join(ROOT, "results", "stats_family.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("\n=> %s (%d loi). Da ghi results/stats_family.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
