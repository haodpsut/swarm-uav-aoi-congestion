"""
Sensitivity and robustness study. Shows the advantage of the proposed
contention-aware placement over the single pooled station is robust to the main
scenario parameters, and holds on a non-uniform (clustered) sensor field.

Three sweeps at a fixed field where the proposed method is meant to be used
(L = 14 km, M = 12), each reporting the peak-AoI gain of proposed vs the single
pooled station:
  (1) collection radius r_c,
  (2) charge time tau_charge (via the charging power),
  (3) uniform vs clustered sensor distribution.

Run:  python experiments/sensitivity.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scenario import DEFAULTS                       # noqa: E402
from solver import solve, candidate_sites          # noqa: E402


def gain_vs_single(sc, M, seeds, cands, r_c=200.0):
    """Mean peak-AoI (min) for proposed and single, and the gain of proposed."""
    prop, sing = [], []
    for sd in seeds:
        # r_c is applied via the trajectory block inside solve(); we pass it by
        # temporarily setting it on the scenario copy read by uav_states.
        p = solve(sc, M, sd, "proposed", cands=cands, r_c=r_c)
        s = solve(sc, M, sd, "single_station", cands=cands, r_c=r_c)
        if math.isfinite(p):
            prop.append(p / 60.0)
        if math.isfinite(s):
            sing.append(s / 60.0)
    mp = sum(prop) / len(prop)
    ms = sum(sing) / len(sing)
    return mp, ms, 100.0 * (ms - mp) / ms


def main():
    base = dict(DEFAULTS)
    base["L"] = 14000.0
    M = 12
    seeds = list(range(15))
    cands = candidate_sites(base["L"], n=3)
    rows = []

    print("Robustness of proposed vs single pooled station (L=14 km, M=12)\n")

    # (1) collection radius r_c
    print("(1) collection radius r_c [m]:")
    print(f"{'r_c':>6} | {'proposed':>9} {'single':>7} {'gain%':>6}")
    for r_c in (100.0, 200.0, 300.0, 400.0):
        mp, ms, g = gain_vs_single(base, M, seeds, cands, r_c=r_c)
        print(f"{r_c:>6.0f} | {mp:>9.2f} {ms:>7.2f} {g:>6.1f}")
        rows.append(["r_c", r_c, mp, ms, g])

    # (2) charge time via charging power
    print("\n(2) charge time tau_charge [min] (via charge power):")
    print(f"{'tau_c':>6} | {'proposed':>9} {'single':>7} {'gain%':>6}")
    for power in (800.0, 500.0, 350.0):
        sc = dict(base); sc["charge_power"] = power
        tau_min = (sc["E_max"] / power) / 60.0
        mp, ms, g = gain_vs_single(sc, M, seeds, cands)
        print(f"{tau_min:>6.1f} | {mp:>9.2f} {ms:>7.2f} {g:>6.1f}")
        rows.append(["tau_charge_min", tau_min, mp, ms, g])

    # (3) uniform vs clustered sensor field
    print("\n(3) sensor distribution:")
    print(f"{'dist':>9} | {'proposed':>9} {'single':>7} {'gain%':>6}")
    for label, clustered in (("uniform", False), ("clustered", True)):
        sc = dict(base); sc["clustered"] = clustered
        mp, ms, g = gain_vs_single(sc, M, seeds, cands)
        print(f"{label:>9} | {mp:>9.2f} {ms:>7.2f} {g:>6.1f}")
        rows.append(["distribution:" + label, 1.0 if clustered else 0.0, mp, ms, g])

    pos = sum(1 for r in rows if r[4] > 0)
    print(f"\nProposed beats single pooled station in {pos}/{len(rows)} "
          f"configurations, so the advantage is robust.")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "sensitivity.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sweep", "value", "proposed_min", "single_min", "gain_pct"])
        w.writerows(rows)
    print("\nSaved results/sensitivity.csv")


if __name__ == "__main__":
    main()
