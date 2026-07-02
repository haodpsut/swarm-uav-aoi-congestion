"""
Render result figures from the CSVs (matplotlib; data plots only — final
result/flow figures become TikZ later). Run AFTER validate_prop1.py.

Run:  python experiments/make_figures.py
Outputs: results/fig_prop1_curves.png, results/fig_prop1_mstar.png
"""

import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "results")


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fig_curves():
    rows = load(os.path.join(RES, "prop1_curves.csv"))
    by_c = {}
    for r in rows:
        by_c.setdefault(int(r["c"]), []).append(r)
    plt.figure(figsize=(6.5, 4.2))
    for c in sorted(by_c):
        rs = sorted(by_c[c], key=lambda r: int(r["M"]))
        M = [int(r["M"]) for r in rs]
        y = [float(r["aoi_mean"]) for r in rs]
        e = [float(r["aoi_std"]) for r in rs]
        M2 = [m for m, v in zip(M, y) if math.isfinite(v)]
        y2 = [v for v in y if math.isfinite(v)]
        e2 = [e[i] for i, v in enumerate(y) if math.isfinite(v)]
        plt.errorbar(M2, y2, yerr=e2, marker="o", ms=3, capsize=2, label=f"c={c} ports")
        # mark M*
        if y2:
            i = min(range(len(y2)), key=lambda k: y2[k])
            plt.scatter([M2[i]], [y2[i]], color="k", zorder=5, s=28)
    plt.xlabel("Swarm size M (number of UAVs)")
    plt.ylabel("Peak AoI (min)")
    plt.title("Non-monotone AoI(M): congestion threshold (pooled M/M/c = optimal)")
    plt.legend(fontsize=8, ncol=2)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, "fig_prop1_curves.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


def fig_mstar():
    rows = load(os.path.join(RES, "prop1_mstar.csv"))
    cap = [float(r["capacity"]) for r in rows]
    ms = [int(r["M_star"]) for r in rows]
    plt.figure(figsize=(5.5, 4.0))
    plt.plot(cap, ms, marker="s")
    plt.xlabel("Charging capacity  c*mu  (charges/min)")
    plt.ylabel("Optimal swarm size M*")
    plt.title("Provisioning law: M* grows with charging capacity")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, "fig_prop1_mstar.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    fig_curves()
    fig_mstar()
