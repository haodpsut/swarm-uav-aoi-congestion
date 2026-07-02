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
    path = os.path.join(RES, "prop1_phys_mstar.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
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


def fig_prop1_phys():
    path = os.path.join(RES, "prop1_phys_curves.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    by_c = {}
    for r in rows:
        by_c.setdefault(int(r["c"]), []).append(r)
    plt.figure(figsize=(6.5, 4.2))
    for c in sorted(by_c):
        rs = sorted(by_c[c], key=lambda r: int(r["M"]))
        M = [int(r["M"]) for r in rs]
        y = [float(r["aoi_mean_s"]) / 60.0 for r in rs]   # -> minutes
        M2 = [m for m, v in zip(M, y) if math.isfinite(v)]
        y2 = [v for v in y if math.isfinite(v)]
        plt.plot(M2, y2, marker="o", ms=3, label=f"c={c}")
        if y2:
            i = min(range(len(y2)), key=lambda k: y2[k])
            plt.scatter([M2[i]], [y2[i]], color="k", zorder=5, s=28)
    plt.xlabel("Swarm size M")
    plt.ylabel("Peak AoI (min)")
    plt.title("Prop.1 (physical model): non-monotone AoI(M)")
    plt.legend(fontsize=8, ncol=2)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, "fig_prop1_phys.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


def fig_prop2():
    path = os.path.join(RES, "prop2_placement.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    seeds = [int(r["seed"]) for r in rows]
    cov = [float(r["aoi_cov_s"]) / 60.0 for r in rows]
    traf = [float(r["aoi_traf_s"]) / 60.0 for r in rows]
    x = range(len(seeds))
    plt.figure(figsize=(7.0, 4.0))
    w = 0.4
    plt.bar([i - w / 2 for i in x], cov, width=w, label="coverage-optimal")
    plt.bar([i + w / 2 for i in x], traf, width=w, label="traffic-optimal")
    plt.xlabel("Seed")
    plt.ylabel("Peak AoI (min)")
    plt.title("Prop.2: traffic-driven placement beats coverage-driven")
    plt.xticks(list(x), seeds, fontsize=7)
    plt.legend()
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    out = os.path.join(RES, "fig_prop2.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


def fig_crossover():
    path = os.path.join(RES, "joint_crossover.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    L = [float(r["L_m"]) / 1000 for r in rows]
    prop = [float(r["proposed_min"]) for r in rows]
    single = [float(r["single_min"]) for r in rows]
    cov = [float(r["coverage_min"]) for r in rows]
    plt.figure(figsize=(6.5, 4.2))
    plt.plot(L, prop, marker="o", label="proposed (distributed, traffic-optimal)")
    plt.plot(L, single, marker="s", label="single pooled station (Wei-style)")
    plt.plot(L, cov, marker="^", label="coverage-optimal")
    plt.xlabel("Field side length (km)")
    plt.ylabel("Peak AoI (min)")
    plt.title("Crossover: distributed placement wins once travel dominates")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, "fig_crossover.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


def fig_ablation():
    path = os.path.join(RES, "joint_ablation.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    methods = [k for k in rows[0].keys() if k != "seed"]
    means = []
    for m in methods:
        vals = [float(r[m]) / 60.0 for r in rows if math.isfinite(float(r[m]))]
        means.append(sum(vals) / len(vals) if vals else float("nan"))
    plt.figure(figsize=(7.0, 4.0))
    plt.bar(range(len(methods)), means, color="steelblue")
    plt.xticks(range(len(methods)), methods, rotation=20, fontsize=8, ha="right")
    plt.ylabel("Peak AoI (min)")
    plt.title("Ablation at L=15 km: each ingredient contributes")
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    out = os.path.join(RES, "fig_ablation.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


def fig_des():
    path = os.path.join(RES, "des_validation.csv")
    if not os.path.exists(path):
        return
    rows = [r for r in load(path) if float(r["des_exp_wq"]) > 0.5]
    rows.sort(key=lambda r: float(r["rho"]))
    rho = [float(r["rho"]) for r in rows]
    mmc = [float(r["mmc_wq"]) for r in rows]
    fs = [float(r["finite_wq"]) for r in rows]
    de = [float(r["des_exp_wq"]) for r in rows]
    dd = [float(r["des_det_wq"]) for r in rows]
    plt.figure(figsize=(6.5, 4.2))
    plt.scatter(rho, mmc, s=18, marker="x", label="open M/M/c (over-predicts ~6x)")
    plt.scatter(rho, fs, s=18, marker="s", label="finite-source (our model)")
    plt.scatter(rho, de, s=18, marker="o", label="DES (exponential service)")
    plt.scatter(rho, dd, s=18, marker="^", label="DES (deterministic service, real)")
    plt.xlabel("Station utilisation rho")
    plt.ylabel("Mean queue wait (s)")
    plt.title("Queue-model validation vs discrete-event simulation")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RES, "fig_des_validation.png")
    plt.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    fig_des()            # queue-model validation vs DES (closes the model-risk gap)
    fig_mstar()          # provisioning M*(capacity), finite-source
    fig_prop1_phys()     # Prop.1 U-shape family, finite-source (physical model)
    fig_prop2()
    fig_crossover()
    fig_ablation()
