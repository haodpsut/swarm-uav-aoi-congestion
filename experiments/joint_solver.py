"""
Joint solver vs baselines: the paper's main comparison, reported HONESTLY.

Key finding: pooling all charging ports into ONE station minimises queue wait
(the M/M/c pooling theorem), so a single pooled station is a very strong
baseline in SMALL fields. Distributed, contention-aware placement wins only when
the field is large enough that travel cost dominates the pooling advantage.
We therefore report a FIELD-SIZE SWEEP showing the crossover, plus an ablation
table in the large-field regime where the proposed method is meant to be used.

Run:  python experiments/joint_solver.py
GPU: the CETSP trajectory optimiser uses CUDA automatically when available.
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scenario import DEFAULTS          # noqa: E402
from solver import solve, candidate_sites  # noqa: E402

try:
    from scipy.stats import wilcoxon
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False


def mean_std_min(vals):
    f = [v / 60.0 for v in vals if math.isfinite(v)]
    if not f:
        return math.inf, 0.0
    m = sum(f) / len(f)
    return m, math.sqrt(sum((v - m) ** 2 for v in f) / len(f))


def field_sweep(sc, M, seeds, Ls):
    """Crossover: proposed vs single_station vs coverage across field size."""
    print("=== Field-size crossover (proposed vs single pooled station) ===")
    print(f"{'L(km)':>6} | {'proposed':>9} {'single':>9} {'coverage':>9} | {'prop vs single':>14}")
    rows = []
    for L in Ls:
        scL = dict(sc); scL["L"] = float(L)
        cands = candidate_sites(scL["L"], n=3)
        res = {}
        for m in ("proposed", "single_station", "coverage"):
            res[m] = [solve(scL, M, sd, m, cands=cands) for sd in seeds]
        p, _ = mean_std_min(res["proposed"])
        s, _ = mean_std_min(res["single_station"])
        c, _ = mean_std_min(res["coverage"])
        gain = 100.0 * (s - p) / s if math.isfinite(s) and math.isfinite(p) and s > 0 else float("nan")
        tag = f"{gain:+.1f}% ({'win' if gain > 0 else 'lose'})"
        print(f"{L/1000:>6.0f} | {p:>9.2f} {s:>9.2f} {c:>9.2f} | {tag:>14}")
        rows.append([L, p, s, c, gain])
    return rows


def ablation(sc, M, seeds, L):
    """Ablation table at a large field where distributed placement is warranted."""
    scL = dict(sc); scL["L"] = float(L)
    cands = candidate_sites(scL["L"], n=3)
    methods = [
        ("proposed", "CETSP traj + traffic-optimal placement"),
        ("no_cetsp", "NN traj + traffic-optimal (ablate trajectory)"),
        ("coverage", "CETSP traj + coverage placement (ablate contention)"),
        ("roundrobin", "CETSP traj + coverage sites + round-robin"),
        ("single_station", "CETSP traj + one pooled station (Wei-style)"),
    ]
    print(f"\n=== Ablation at L={L/1000:.0f} km (M={M}) ===")
    print(f"{'method':>16} | {'AoI(min)':>9} {'std':>6} | desc")
    res = {}
    for m, desc in methods:
        res[m] = [solve(scL, M, sd, m, cands=cands) for sd in seeds]
        mean, std = mean_std_min(res[m])
        print(f"{m:>16} | {mean:>9.2f} {std:>6.2f} | {desc}")

    # Wilcoxon: proposed vs strongest baseline.
    base_names = [m for m, _ in methods if m != "proposed"]
    strongest = min(base_names, key=lambda m: mean_std_min(res[m])[0])
    prop, base = res["proposed"], res[strongest]
    paired = [(a, b) for a, b in zip(prop, base) if math.isfinite(a) and math.isfinite(b)]
    if paired:
        gain = 100.0 * (sum(b for _, b in paired) - sum(a for a, _ in paired)) / sum(b for _, b in paired)
        print(f"\nStrongest baseline: {strongest}; proposed reduces peak AoI by {gain:+.1f}%")
        if HAVE_SCIPY and len(paired) >= 6 and any(a != b for a, b in paired):
            try:
                stat, p = wilcoxon([a for a, _ in paired], [b for _, b in paired])
                print(f"Wilcoxon: W={stat:.1f}, p={p:.2e} "
                      f"({'significant' if p < 0.05 else 'NOT significant'} @0.05)")
            except Exception as e:
                print(f"Wilcoxon skipped: {e}")
        elif not HAVE_SCIPY:
            print("scipy missing -> Wilcoxon skipped.")
    return res, methods


def main():
    sc = dict(DEFAULTS)
    M = 12
    seeds = list(range(20))
    Ls = [5000, 8000, 11000, 14000, 17000, 20000]

    rows = field_sweep(sc, M, seeds, Ls)
    res, methods = ablation(sc, M, seeds, L=15000)

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "joint_crossover.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["L_m", "proposed_min", "single_min", "coverage_min", "gain_pct"])
        w.writerows(rows)
    with open(os.path.join(out, "joint_ablation.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed"] + [m for m, _ in methods])
        for i, sd in enumerate(seeds):
            w.writerow([sd] + [res[m][i] for m, _ in methods])
    print("\nSaved results/joint_crossover.csv and results/joint_ablation.csv")


if __name__ == "__main__":
    main()
