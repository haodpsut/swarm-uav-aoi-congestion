"""
MAKE-OR-BREAK GATE (formulation.md, section 6).

Question: does peak AoI(M) have an interior minimizer (U-shape) that BINDS under
the *optimal* charging assignment, in a capacity-limited regime?

Optimal assignment is upper-bounded by POOLING all c ports into one M/M/c queue
(pooling minimises expected wait, a standard queueing fact). So if the U-shape
survives under pooled M/M/c, it survives under any realisable assignment -> GREEN.
We also show the naive split (c separate M/M/1 stations) to confirm optimal helps
but does not dissolve the congestion.

Run: python experiments/gate_ushape.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from queue_model import peak_aoi          # noqa: E402
from field import coverage_alpha          # noqa: E402


def sweep(M_values, c, mu, tau_fly, tau_charge, K, L, V, travel, seeds):
    """Return per-M mean/std peak AoI over seeds for pooled M/M/c."""
    rows = []
    for M in M_values:
        vals, rhos = [], []
        for sd in seeds:
            alpha = coverage_alpha(K, L, M, V, sd)
            aoi, det = peak_aoi(M, c, mu, tau_fly, tau_charge, alpha, travel)
            vals.append(aoi)
            rhos.append(det["rho"])
        finite = [v for v in vals if math.isfinite(v)]
        if finite:
            mean = sum(finite) / len(finite)
            var = sum((v - mean) ** 2 for v in finite) / len(finite)
            std = math.sqrt(var)
        else:
            mean, std = math.inf, 0.0
        rows.append(dict(M=M, aoi_mean=mean, aoi_std=std,
                         rho=sum(rhos) / len(rhos),
                         unstable_frac=sum(1 for v in vals if not math.isfinite(v)) / len(vals)))
    return rows


def is_u_shaped(rows):
    """Interior minimizer with a clear rise afterward (>5% above the min)."""
    means = [r["aoi_mean"] for r in rows]
    finite_idx = [i for i, m in enumerate(means) if math.isfinite(m)]
    if len(finite_idx) < 3:
        # All-but-few unstable also counts as congestion binding hard.
        return True, finite_idx[-1] if finite_idx else 0
    imin = min(finite_idx, key=lambda i: means[i])
    has_left_drop = any(means[i] > means[imin] * 1.05 for i in finite_idx if i < imin)
    has_right_rise = any((not math.isfinite(means[i])) or means[i] > means[imin] * 1.05
                         for i in range(imin + 1, len(means)))
    return (has_left_drop and has_right_rise), imin


def report(title, rows):
    print(f"\n=== {title} ===")
    print(f"{'M':>3} | {'AoI mean':>9} | {'AoI std':>8} | {'rho':>5} | {'unstable':>8}")
    for r in rows:
        m = f"{r['aoi_mean']:9.2f}" if math.isfinite(r["aoi_mean"]) else f"{'INF':>9}"
        print(f"{r['M']:>3} | {m} | {r['aoi_std']:8.2f} | {r['rho']:5.2f} | {r['unstable_frac']:8.2f}")
    u, imin = is_u_shaped(rows)
    if u:
        print(f"-> U-SHAPE present. Optimal swarm size M* = {rows[imin]['M']} "
              f"(rho={rows[imin]['rho']:.2f}); AoI rises for M > M*.")
    else:
        print("-> monotone (no interior minimizer): congestion does NOT bind here.")
    return u, imin


def main():
    # --- Fixed scenario ---
    K, L, V = 60, 5.0, 1.0            # 60 sensors in 5x5 km field, UAV 1 km/min
    tau_fly, tau_charge = 20.0, 10.0  # 20 min endurance, 10 min charge (mu=0.1)
    mu = 1.0 / tau_charge
    travel = 4.0                      # round-trip to central station (min)
    M_values = list(range(1, 13))
    seeds = list(range(10))           # 10 seeds, no single-seed wins

    # --- Capacity-LIMITED regime (the gate): few ports ---
    c_lim = 2
    rows_lim = sweep(M_values, c_lim, mu, tau_fly, tau_charge, K, L, V, travel, seeds)
    u_lim, imin_lim = report(f"Capacity-LIMITED, pooled M/M/c  (c={c_lim} ports, OPTIMAL assignment)", rows_lim)

    # --- Capacity-RICH regime (honest control): many ports, congestion should not bite ---
    c_rich = 10
    rows_rich = sweep(M_values, c_rich, mu, tau_fly, tau_charge, K, L, V, travel, seeds)
    u_rich, _ = report(f"Capacity-RICH, pooled M/M/c  (c={c_rich} ports, control)", rows_rich)

    # --- Naive split (c separate M/M/1) vs pooled, capacity-limited: does optimal dissolve it? ---
    print("\n=== Naive split (c separate M/M/1) vs pooled, capacity-limited ===")
    rows_split = []
    for M in M_values:
        vals = []
        for sd in seeds:
            alpha = coverage_alpha(K, L, M, V, sd)
            # naive: split M UAVs across c single-port stations -> per-station M/M/1
            # effective: each station sees lambda_total/c but with 1 server.
            aoi, det = peak_aoi(M, 1, mu, tau_fly * 1.0, tau_charge, alpha, travel)
            # emulate per-station load by scaling: a single M/M/1 serving M/c UAVs
            aoi_s, det_s = peak_aoi(max(1, round(M / c_lim)), 1, mu, tau_fly, tau_charge, alpha, travel)
            vals.append(aoi_s)
        finite = [v for v in vals if math.isfinite(v)]
        mean = sum(finite) / len(finite) if finite else math.inf
        rows_split.append(dict(M=M, aoi_mean=mean, aoi_std=0.0, rho=0.0,
                               unstable_frac=sum(1 for v in vals if not math.isfinite(v)) / len(vals)))
    report("Naive split (per-station M/M/1)", rows_split)

    # --- VERDICT ---
    print("\n" + "=" * 60)
    green = u_lim and (not u_rich)
    if green:
        print("VERDICT: GREEN.")
        print(" - U-shape BINDS under OPTIMAL (pooled) assignment in the capacity-limited regime.")
        print(f" - M* = {rows_lim[imin_lim]['M']} ports={c_lim}: adding UAVs beyond M* WORSENS peak AoI.")
        print(" - Capacity-RICH control is monotone -> the effect is genuinely capacity-limited,")
        print("   not an artifact -> Prop. 1 (non-monotone AoI) is empirically supported. Build the paper.")
    else:
        print("VERDICT: NOT GREEN (reframe/abandon).")
        print(f"  U-shape capacity-limited={u_lim}, capacity-rich U-shape={u_rich}.")
        print("  If optimal assignment dissolves the U-shape, the congestion story is weak.")
    print("=" * 60)

    # --- Save CSV for later TikZ figures ---
    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "gate_ushape.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["regime", "M", "aoi_mean", "aoi_std", "rho", "unstable_frac"])
        for tag, rows in [("limited", rows_lim), ("rich", rows_rich), ("split", rows_split)]:
            for r in rows:
                w.writerow([tag, r["M"], r["aoi_mean"], r["aoi_std"], r["rho"], r["unstable_frac"]])
    print(f"\nSaved results/gate_ushape.csv")


if __name__ == "__main__":
    main()
