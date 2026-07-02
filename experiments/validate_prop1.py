"""
Prop. 1 validation (server-ready, CPU-only, conda).

Extends the make-or-break gate into a full sweep that produces the paper's
first result: peak AoI(M) for several charging-capacity budgets, the optimal
swarm size M*(c), and the provisioning law (M* grows with capacity).

All assignment is the OPTIMAL (pooled M/M/c) upper bound, so any U-shape here
is fundamental (capacity-limited), not an assignment artifact.

Outputs:
  results/prop1_curves.csv   # regime,c,M,aoi_mean,aoi_std,rho,unstable_frac
  results/prop1_mstar.csv    # c,M_star,aoi_at_mstar,capacity(c*mu)

Run:  python experiments/validate_prop1.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from queue_model import peak_aoi          # noqa: E402
from field import patrol_time             # noqa: E402


def sweep_curve(M_values, c, mu, tau_fly, tau_charge, K, L, V, travel, seeds):
    rows = []
    for M in M_values:
        vals, rhos = [], []
        for sd in seeds:
            tp = patrol_time(K, L, M, V, sd)
            aoi, det = peak_aoi(M, c, mu, tau_fly, tau_charge, tp, travel)
            vals.append(aoi)
            rhos.append(det["rho"])
        finite = [v for v in vals if math.isfinite(v)]
        if finite:
            mean = sum(finite) / len(finite)
            std = math.sqrt(sum((v - mean) ** 2 for v in finite) / len(finite))
        else:
            mean, std = math.inf, 0.0
        rows.append(dict(c=c, M=M, aoi_mean=mean, aoi_std=std,
                         rho=sum(rhos) / len(rhos),
                         unstable_frac=sum(1 for v in vals if not math.isfinite(v)) / len(vals)))
    return rows


def find_mstar(rows):
    finite = [r for r in rows if math.isfinite(r["aoi_mean"])]
    if not finite:
        return None
    best = min(finite, key=lambda r: r["aoi_mean"])
    return best


def main():
    # Fixed scenario (same as the gate).
    K, L, V = 60, 5.0, 1.0
    tau_fly, tau_charge = 20.0, 10.0
    mu = 1.0 / tau_charge
    travel = 4.0
    M_values = list(range(1, 21))
    seeds = list(range(30))                 # 30 seeds for publication-grade std
    capacities = [1, 2, 3, 4, 6, 8, 12]     # total ports (pooled)

    all_rows, mstar_rows = [], []
    print(f"{'c':>3} {'cap=c*mu':>9} | {'M*':>3} {'AoI@M*':>8}")
    for c in capacities:
        rows = sweep_curve(M_values, c, mu, tau_fly, tau_charge, K, L, V, travel, seeds)
        all_rows.extend(rows)
        best = find_mstar(rows)
        cap = c * mu
        if best:
            mstar_rows.append(dict(c=c, capacity=cap, M_star=best["M"],
                                   aoi_at_mstar=best["aoi_mean"]))
            print(f"{c:>3} {cap:>9.2f} | {best['M']:>3} {best['aoi_mean']:>8.2f}")

    # Provisioning law check: M* should be non-decreasing in capacity.
    ms = [r["M_star"] for r in mstar_rows]
    mono = all(ms[i] <= ms[i + 1] for i in range(len(ms) - 1))
    print(f"\nProvisioning law (M* non-decreasing in capacity): {'HOLDS' if mono else 'VIOLATED'}")
    print(f"  capacities c={[r['c'] for r in mstar_rows]}  ->  M*={ms}")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "prop1_curves.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["c", "M", "aoi_mean", "aoi_std", "rho", "unstable_frac"])
        for r in all_rows:
            w.writerow([r["c"], r["M"], r["aoi_mean"], r["aoi_std"], r["rho"], r["unstable_frac"]])
    with open(os.path.join(out, "prop1_mstar.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["c", "capacity", "M_star", "aoi_at_mstar"])
        for r in mstar_rows:
            w.writerow([r["c"], r["capacity"], r["M_star"], r["aoi_at_mstar"]])
    print(f"\nSaved results/prop1_curves.csv and results/prop1_mstar.csv")


if __name__ == "__main__":
    main()
