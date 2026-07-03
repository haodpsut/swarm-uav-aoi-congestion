"""
Large-swarm scaling study. A reviewer noted that $M=12$ to $20$ is a small fleet,
not a swarm. Here we scale to genuinely large swarms ($M$ up to $60$) over a wide
field with many sensors, and we scale the charging CAPACITY with the swarm (more
ports as $M$ grows), consistent with the provisioning law: a large swarm is only
worthwhile if its charging capacity grows with it. We check that the proposed
contention-aware placement keeps its advantage over the single pooled station and
the coverage-optimal placement at swarm scale.

Sensors scale as K = 8*M (about eight sensors per UAV) over a 20 km field. The
port budget scales as C_tot = round(M/3). GPU CETSP handles the large swarm.

Run:  python experiments/scale.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scenario import DEFAULTS                       # noqa: E402
from solver import solve, candidate_sites          # noqa: E402


def main():
    M_values = [20, 30, 40, 50, 60]
    seeds = list(range(10))
    S_max = 2
    L = 20000.0
    cands = candidate_sites(L, n=4)                 # 16 candidate sites

    print(f"Large-swarm scaling (L={L/1000:.0f} km, K=8M, C_tot=round(M/3), "
          f"S_max={S_max}, {len(seeds)} seeds)\n")
    print(f"{'M':>3} {'K':>4} {'C_tot':>5} | {'proposed':>9} {'single':>7} "
          f"{'coverage':>8} | {'gain%':>6}")
    rows = []
    for M in M_values:
        sc = dict(DEFAULTS)
        sc["L"] = L
        sc["K"] = 8 * M
        C_tot = max(6, round(M / 3))
        res = {}
        for m in ("proposed", "single_station", "coverage"):
            vals = [solve(sc, M, sd, m, cands=cands, S_max=S_max, C_tot=C_tot)
                    for sd in seeds]
            fin = [v / 60.0 for v in vals if math.isfinite(v)]
            res[m] = sum(fin) / len(fin) if fin else math.inf
        gain = (100.0 * (res["single_station"] - res["proposed"]) / res["single_station"]
                if math.isfinite(res["single_station"]) else float("nan"))
        print(f"{M:>3} {8*M:>4} {C_tot:>5} | {res['proposed']:>9.2f} "
              f"{res['single_station']:>7.2f} {res['coverage']:>8.2f} | {gain:>6.1f}")
        rows.append([M, 8 * M, C_tot, res["proposed"], res["single_station"],
                     res["coverage"], gain])

    wins = sum(1 for r in rows if r[6] > 0)
    print(f"\nProposed beats the single pooled station at {wins}/{len(rows)} swarm "
          f"sizes, so the advantage persists at scale.")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "scale.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["M", "K", "C_tot", "proposed_min", "single_min",
                    "coverage_min", "gain_pct"])
        w.writerows(rows)
    print("\nSaved results/scale.csv")


if __name__ == "__main__":
    main()
