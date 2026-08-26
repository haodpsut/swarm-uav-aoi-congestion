"""Diem 5 cua phan bien R1: xap xi hang doi co doi THU HANG dat tram khong.

Phan bien khong hoi "mo hinh lech bao nhieu" -- bai da tra loi cau do (M/M finite-source
over-predict 4,5x so voi DES thuc; M/D siet con 2,3x). Cau ho dat la:

    "it would be useful to examine whether this approximation changes the RANKING of
     candidate placements or capacity decisions"

Nen phep nay chay LAI dung phep so dat tram cua Prop.2, mot lan voi hang doi M/M (nhu
bai dang dung) va mot lan voi xap xi dich vu TAT DINH M/D (finite_source_wq_md, cs2=0),
roi so THU TU chu khong so gia tri.

Nguong da chot TRUOC khi chay, o THIET-KE-TRUOC.md:
    thu hang giu nguyen tren moi seed        -> ket luan song
    doi o mot vai seed                       -> bao ti le, ha muc tuyen bo
    doi o > 10/20 seed                       -> khuyen nghi dat tram LAT, viet lai §VI
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import queue_model                                            # noqa: E402
from queue_model import finite_source_wq, finite_source_wq_md  # noqa: E402
import solver                                                  # noqa: E402
from scenario import DEFAULTS, tau_charge_of                    # noqa: E402
from solver import (uav_states, candidate_sites,                # noqa: E402
                    strategy_coverage, strategy_traffic)

_MM = finite_source_wq


def _md(N, c, up_time, tau_charge):
    """Cung chu ky voi finite_source_wq nhung dung dich vu TAT DINH (cs2=0)."""
    w_md, _ = finite_source_wq_md(N, c, up_time, tau_charge, cs2=0.0)
    w_mm, Lq, lam_eff, rho = _MM(N, c, up_time, tau_charge)
    return w_md, Lq, lam_eff, rho


def run(queue_fn):
    solver.finite_source_wq = queue_fn
    sc = dict(DEFAULTS)
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    out = []
    for sd in range(20):
        states = uav_states(sc, 12, sd)
        A = strategy_coverage(states, cands, 2, 4, mu, tau_charge, sc["V"])
        B = strategy_traffic(states, cands, 2, 4, mu, tau_charge, sc["V"])
        out.append((sd, A["aoi"], B["aoi"]))
    solver.finite_source_wq = _MM
    return out


def main():
    mm = run(_MM)
    md = run(_md)
    print("Diem 5: thu hang dat tram duoi HAI mo hinh hang doi\n")
    print("%4s | %-26s | %-26s | %s" % ("seed", "M/M (bai dang dung)",
                                        "M/D (dich vu tat dinh)", "thu hang"))
    print("%4s | %12s %12s | %12s %12s | %s"
          % ("", "AoI_cov", "AoI_traf", "AoI_cov", "AoI_traf", ""))
    print("-" * 92)
    flips, rows = 0, []
    for (sd, a1, b1), (_, a2, b2) in zip(mm, md):
        # ⛔ HOA PHAI DUOC DEM RIENG. Ban truoc viet `b <= a -> traf`, tuc gop HOA vao
        # phia thang cua ta. Hai seed co AoI bang nhau chinh xac, va gop chung vao
        # "traffic thang" la lam dep so cua chinh minh. Day dung lop loi bai IoT-J
        # FedKAN vua bi doc ngoai bat: khong khai cap hoa.
        eps = 1e-9
        r1 = "tie" if abs(b1 - a1) < eps else ("traf" if b1 < a1 else "cov")
        r2 = "tie" if abs(b2 - a2) < eps else ("traf" if b2 < a2 else "cov")
        same = (r1 == r2)
        flips += 0 if same else 1
        rows.append({"seed": sd, "aoi_cov_mm": a1, "aoi_traf_mm": b1,
                     "aoi_cov_md": a2, "aoi_traf_md": b2,
                     "winner_mm": r1, "winner_md": r2, "flipped": int(not same)})
        print("%4d | %12.2f %12.2f | %12.2f %12.2f | %-4s -> %-4s %s"
              % (sd, a1 / 60, b1 / 60, a2 / 60, b2 / 60, r1, r2,
                 "" if same else "⛔ DOI"))
    n = len(rows)
    nt = sum(1 for r in rows if r["winner_mm"] == "tie" or r["winner_md"] == "tie")
    print("\n  thu hang DOI o %d/%d seed  (trong do %d seed co HOA, AoI bang nhau)"
          % (flips, n, nt))
    if flips == 0:
        print("  => KET LUAN SONG: xap xi hang doi khong lam doi thu hang dat tram.")
    elif flips <= n // 2:
        print("  => nhay mot phan: phai bao ti le %d/%d va ha muc tuyen bo." % (flips, n))
    else:
        print("  => ⛔ KHUYEN NGHI DAT TRAM LAT: phai viet lai muc thuc nghiem.")
    p = os.path.join(HERE, "..", "results", "prop2_ranking_md.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\nSaved results/prop2_ranking_md.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
