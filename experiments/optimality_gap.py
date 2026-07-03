"""
Optimality-gap study: how far is the block-coordinate solver from the true
optimum? On small instances we can enumerate the exact optimum (every open-site
subset, every integer port split, and EVERY UAV-to-station assignment) and
compare it against the greedy placement/assignment used by the proposed solver.

Both use the SAME per-UAV states (same trajectory), so the gap isolates the
combinatorial placement + port + assignment heuristic, not the trajectory block.
This answers the reviewer question "is the greedy assignment near-optimal?".

Run:  python experiments/optimality_gap.py
"""

import csv
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scenario import DEFAULTS, tau_charge_of                      # noqa: E402
from solver import (uav_states, candidate_sites, peak_aoi,        # noqa: E402
                    strategy_traffic, _port_splits)


def exhaustive_optimum(states, cands, S_max, C_tot, mu, tau_charge, V):
    """True minimum peak AoI over all (sites, port split, assignment)."""
    best = math.inf
    M = len(states)
    for combo in itertools.combinations(range(len(cands)), S_max):
        sites = [cands[j] for j in combo]
        for ports in _port_splits(C_tot, S_max):
            # every assignment of M UAVs to the S_max open stations
            for assign in itertools.product(range(S_max), repeat=M):
                val = peak_aoi(states, sites, list(ports), list(assign),
                               mu, tau_charge, V)
                if val < best:
                    best = val
    return best


def main():
    sc = dict(DEFAULTS)
    sc["L"] = 8000.0                 # small field so exhaustive is affordable
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    V = sc["V"]
    cands = candidate_sites(sc["L"], n=3)      # 9 candidate sites
    S_max, C_tot = 2, 4
    M_values = [3, 4, 5, 6, 7, 8]
    seeds = list(range(15))

    print(f"Optimality gap: greedy solver vs exhaustive optimum "
          f"(S_max={S_max}, C_tot={C_tot}, {len(seeds)} seeds)\n")
    print(f"{'M':>3} | {'gap mean%':>9} {'gap max%':>8} | {'optimal-hit':>11}")
    rows = []
    for M in M_values:
        gaps, hits = [], 0
        for sd in seeds:
            # nearest-neighbour trajectory (CPU, deterministic) so the two methods
            # share identical states and the gap is purely combinatorial.
            states = uav_states(sc, M, sd, trajectory="nn")
            greedy = strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V)["aoi"]
            opt = exhaustive_optimum(states, cands, S_max, C_tot, mu, tau_charge, V)
            if math.isfinite(greedy) and math.isfinite(opt) and opt > 0:
                g = 100.0 * (greedy - opt) / opt
                gaps.append(g)
                if g < 1e-6:
                    hits += 1
        mean_g = sum(gaps) / len(gaps) if gaps else float("nan")
        max_g = max(gaps) if gaps else float("nan")
        print(f"{M:>3} | {mean_g:>9.2f} {max_g:>8.2f} | {hits:>3}/{len(gaps):<3}")
        rows.append([M, mean_g, max_g, hits, len(gaps)])

    allg = [r[1] for r in rows if math.isfinite(r[1])]
    print(f"\nOverall mean gap = {sum(allg)/len(allg):.2f}%  "
          f"(0% means the greedy solver matched the exact optimum).")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "optimality_gap.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["M", "gap_mean_pct", "gap_max_pct", "optimal_hits", "n_seeds"])
        w.writerows(rows)
    print("\nSaved results/optimality_gap.csv")


if __name__ == "__main__":
    main()
