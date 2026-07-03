"""
Render result figures from the CSVs (matplotlib; data plots only).

Design system (applied consistently across all six figures):
  * Colorblind-safe Okabe-Ito palette; one method -> one colour everywhere.
  * IEEE-column sizing, readable fonts, light grid, top/right spines removed.
  * Every figure ANNOTATES its key insight, it does not just dump raw data.

Run:  python experiments/make_figures.py
Outputs (filenames are fixed; the LaTeX depends on them):
  results/fig_des_validation.png
  results/fig_prop1_phys.png
  results/fig_prop1_mstar.png
  results/fig_prop2.png
  results/fig_crossover.png
  results/fig_ablation.png
"""

import csv
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "results")

# ---------------------------------------------------------------------------
# Shared style system
# ---------------------------------------------------------------------------
# Okabe-Ito colourblind-safe palette
OI = {
    "black":  "#000000",
    "orange": "#E69F00",
    "sky":    "#56B4E9",
    "green":  "#009E73",
    "yellow": "#F0E442",
    "blue":   "#0072B2",
    "verm":   "#D55E00",
    "purple": "#CC79A7",
    "grey":   "#8C8C8C",
}
ACCENT = OI["blue"]  # the "proposed" method is always this colour

# One colour per method, reused across every figure that shows it.
METHOD_COLOR = {
    "proposed":       OI["blue"],
    "traffic":        OI["blue"],
    "single_station": OI["green"],
    "single":         OI["green"],
    "coverage":       OI["verm"],
    "no_cetsp":       OI["orange"],
    "roundrobin":     OI["purple"],
}

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 600,          # crisp high-res PNG previews
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.8,
    "figure.autolayout": False,
    "font.family": "DejaVu Sans",
    # Embed TrueType fonts so the vector PDF is portable and text stays selectable.
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def style_axes(ax, grid_axis="both"):
    """Despine top/right, add a light grid, keep it uncluttered."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", axis=grid_axis, alpha=0.3, linewidth=0.7)
    ax.set_axisbelow(True)


def save(fig, name):
    """Write each figure as BOTH a vector PDF (sharp in the paper) and a
    high-resolution PNG (dpi=600, for previews). `name` may be given with or
    without a .png suffix; the base name is reused for both outputs."""
    base = name[:-4] if name.lower().endswith(".png") else name
    for ext in (".pdf", ".png"):
        out = os.path.join(RES, base + ext)
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print("wrote", out, "(%.0f KB)" % (os.path.getsize(out) / 1024))
    plt.close(fig)


# ---------------------------------------------------------------------------
# fig_des_validation: queue-model validation vs discrete-event simulation
# ---------------------------------------------------------------------------
def fig_des():
    path = os.path.join(RES, "des_validation.csv")
    if not os.path.exists(path):
        return
    rows = [r for r in load(path) if float(r["des_mm_wq"]) > 0.5]
    rows.sort(key=lambda r: float(r["rho"]))
    rho = np.array([float(r["rho"]) for r in rows])
    mmc = np.array([float(r["mmc_wq"]) for r in rows])
    fs = np.array([float(r["finite_wq"]) for r in rows])
    md = np.array([float(r["md_wq"]) for r in rows]) if "md_wq" in rows[0] else None
    de = np.array([float(r["des_mm_wq"]) for r in rows])
    dd = np.array([float(r["des_real_wq"]) for r in rows])

    # Quantify the two headline claims from the data, using the SAME statistic as
    # des_validation.py and the paper text: mean over rows with a non-trivial
    # wait (des_mm > 1 s). This makes the figure print 6x / 4%, matching the body.
    sig = de > 1.0
    mmc_over = float(np.mean(mmc[sig] / de[sig]))       # how far M/M/c overshoots DES
    fs_err = float(np.mean(np.abs(fs[sig] - de[sig]) / de[sig]) * 100.0)

    fig, ax = plt.subplots(figsize=(3.7, 3.3))
    ax.plot(rho, mmc, marker="x", ms=5, ls="--", color=OI["verm"],
            label="open M/M/c (assumes $\\infty$ sources)")
    ax.plot(rho, fs, marker="s", ms=4, ls="-", color=OI["blue"],
            label="finite-source $M/M/c//N$")
    if md is not None:
        ax.plot(rho, md, marker="d", ms=3.5, ls="-.", color=OI["purple"],
                label="$M/D/c//N$ approx.")
    ax.plot(rho, de, marker="o", ms=4, ls="none", color=OI["sky"],
            mfc="none", label="DES, exp op.+svc.")
    ax.plot(rho, dd, marker="^", ms=4, ls="none", color=OI["green"],
            label="DES, deterministic (real)")

    ax.set_yscale("log")
    ax.set_xlabel(r"Station utilisation $\rho$")
    ax.set_ylabel("Mean queue wait (s)")
    style_axes(ax)

    # Raise the top so both callouts live in a clean band above every series.
    ax.set_ylim(top=mmc.max() * 3.2)

    # Orange callout (right): a clean vertical leader onto the M/M/c curve, which
    # is the topmost series there, so the arrow crosses no other line or marker.
    oi = int(np.argmin(np.abs(rho - 0.55)))
    ax.annotate("open M/M/c\noverpredicts " + r"$\approx %.0f\times$" % mmc_over,
                xy=(rho[oi], mmc[oi]), xytext=(rho[oi], mmc.max() * 1.85),
                fontsize=8.5, color=OI["verm"], ha="center", va="bottom",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1),
                arrowprops=dict(arrowstyle="->", color=OI["verm"], lw=0.9))

    # Blue callout (left): colour-coded label parked in the empty pocket that sits
    # above all series at low utilisation, so no leader is needed and none crosses.
    ax.text(0.245, 300, "finite-source matches\nDES within "
            + r"$\approx %.0f\%%$" % fs_err,
            fontsize=8.5, color=OI["blue"], ha="left", va="center",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1))

    leg = ax.legend(loc="lower right", frameon=True, fontsize=7.4,
                    framealpha=0.9, edgecolor="none")
    leg.get_frame().set_facecolor("white")
    save(fig, "fig_des_validation.png")


# ---------------------------------------------------------------------------
# fig_prop1_phys: peak AoI(M) for several c -> U-shape / congestion threshold
# ---------------------------------------------------------------------------
def fig_prop1_phys():
    path = os.path.join(RES, "prop1_phys_curves.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    by_c = {}
    for r in rows:
        by_c.setdefault(int(r["c"]), []).append(r)
    cs = sorted(by_c)

    fig, ax = plt.subplots(figsize=(3.8, 3.5))
    norm = Normalize(vmin=min(cs), vmax=max(cs))
    cmap = plt.get_cmap("viridis")

    star_pts = []
    for c in cs:
        rs = sorted(by_c[c], key=lambda r: int(r["M"]))
        M = np.array([int(r["M"]) for r in rs])
        y = np.array([float(r["aoi_mean_s"]) / 60.0 for r in rs])  # minutes
        col = cmap(norm(c))
        ax.plot(M, y, marker="o", ms=2.5, color=col, lw=1.5)
        i = int(np.argmin(y))
        star_pts.append((M[i], y[i], c))

    # mark each curve's M*
    for k, (mx, my, c) in enumerate(star_pts):
        ax.scatter([mx], [my], color="k", zorder=6, s=34, marker="*")

    # dashed line connecting the minima to make the provisioning trend visible
    sx = [p[0] for p in star_pts]
    sy = [p[1] for p in star_pts]
    ax.plot(sx, sy, ls=":", color="k", lw=1.0, zorder=5)

    # label the two extreme M* with a white backing box (they sit near curves)
    lblbox = dict(facecolor="white", alpha=0.8, edgecolor="none", pad=1)
    mx0, my0, _ = star_pts[0]        # smallest capacity: M* small, on the falling edge
    ax.annotate(r"$M^\ast{=}%d$" % mx0, xy=(mx0, my0), xytext=(1.5, 62),
                fontsize=8, color="k", ha="left", va="center", zorder=7,
                bbox=lblbox, arrowprops=dict(arrowstyle="->", color="k", lw=0.8))
    mxL, myL, _ = star_pts[-1]       # largest capacity: M* pinned at the swarm-size cap
    ax.annotate(r"$M^\ast{=}%d$" % mxL, xy=(mxL, myL), xytext=(16.4, 38),
                fontsize=8, color="k", ha="left", va="center", zorder=7,
                bbox=lblbox, arrowprops=dict(arrowstyle="->", color="k", lw=0.8))

    # region annotations, parked in the empty upper-left pocket with leaders that
    # approach the topmost relevant curve from above (so they cross no other curve)
    ax.annotate("coverage-limited\n(too few UAVs)", xy=(2.5, 42), xytext=(3.0, 92),
                fontsize=8, color=OI["grey"], ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=OI["grey"], lw=1.0))
    ax.annotate("congestion-limited\n(charger queue)", xy=(12, 79.7),
                xytext=(5.3, 128), fontsize=8, color=OI["grey"], ha="left",
                va="center", arrowprops=dict(arrowstyle="->", color=OI["grey"], lw=1.0))

    ax.set_xlabel("Swarm size $M$ (number of UAVs)")
    ax.set_ylabel("Peak AoI (min)")
    style_axes(ax)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.02)
    cb.set_label("charging ports $c$", fontsize=9)
    cb.set_ticks(cs)
    cb.ax.tick_params(labelsize=8)
    save(fig, "fig_prop1_phys.png")


# ---------------------------------------------------------------------------
# fig_prop1_mstar: optimal swarm size M* vs charging capacity (provisioning law)
# ---------------------------------------------------------------------------
def fig_mstar():
    path = os.path.join(RES, "prop1_phys_mstar.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    rows.sort(key=lambda r: float(r["capacity"]))
    cap = np.array([float(r["capacity"]) * 60.0 for r in rows])  # charges/min
    ms = np.array([int(r["M_star"]) for r in rows])
    cap_cap = 20  # swarm-size grid ceiling

    fig, ax = plt.subplots(figsize=(4.3, 3.0))
    ax.plot(cap, ms, marker="s", ms=6, color=ACCENT, zorder=4)
    ax.fill_between(cap, ms, 0, color=ACCENT, alpha=0.08)

    # ceiling line: M* saturates when it hits the simulated swarm cap
    ax.axhline(cap_cap, ls="--", color=OI["grey"], lw=1.0)
    ax.text(cap.max(), cap_cap + 0.4, "swarm-size cap", fontsize=8,
            color=OI["grey"], ha="right", va="bottom")

    # Callout sits in the clean band just above the cap line (left of the "swarm-
    # size cap" tag); leader drops onto the rising curve, crossing no data.
    ax.annotate("provisioning law:\n$M^\\ast$ grows with capacity",
                xy=(cap[3], ms[3]), xytext=(cap[0] + 0.02, cap_cap + 1.5),
                fontsize=8.5, color=ACCENT, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.0))

    ax.set_xlabel(r"Charging capacity $c\,\mu$ (charges/min)")
    ax.set_ylabel(r"Optimal swarm size $M^\ast$")
    ax.set_ylim(0, cap_cap + 3)
    style_axes(ax)
    save(fig, "fig_prop1_mstar.png")


# ---------------------------------------------------------------------------
# fig_prop2: coverage- vs traffic-driven placement, per seed (dumbbell / slope)
# ---------------------------------------------------------------------------
def fig_prop2():
    path = os.path.join(RES, "prop2_placement.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    cov = np.array([float(r["aoi_cov_s"]) / 60.0 for r in rows])
    traf = np.array([float(r["aoi_traf_s"]) / 60.0 for r in rows])
    gain = np.array([float(r["gain_pct"]) for r in rows])
    differ = np.array([int(r["sites_differ"]) for r in rows])

    mean_gain = gain.mean()
    n_differ = int(differ.sum())
    n = len(rows)

    order = np.argsort(cov)  # sort by coverage-optimal AoI for a clean ladder
    cov, traf = cov[order], traf[order]
    ypos = np.arange(n)

    fig, ax = plt.subplots(figsize=(3.5, 4.0))
    # connector = the per-seed improvement
    for i in range(n):
        ax.plot([traf[i], cov[i]], [ypos[i], ypos[i]], color=OI["grey"],
                lw=1.4, alpha=0.6, zorder=1)
    ax.scatter(cov, ypos, color=OI["verm"], s=26, zorder=3,
               label="coverage-optimal")
    ax.scatter(traf, ypos, color=ACCENT, s=26, zorder=3,
               label="traffic-optimal (ours)")

    ax.set_yticks(ypos)
    ax.set_yticklabels([str(i + 1) for i in range(n)], fontsize=7)
    ax.set_ylabel("seed (sorted by coverage AoI)")
    ax.set_xlabel("Peak AoI (min)")
    ax.set_ylim(-1, n)
    style_axes(ax, grid_axis="x")

    ax.set_title("Traffic-driven placement lowers peak AoI\n"
                 "mean $-%.1f\\%%$, sites differ on %d/%d"
                 % (mean_gain, n_differ, n), fontsize=9.5)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    save(fig, "fig_prop2.png")


# ---------------------------------------------------------------------------
# fig_crossover: AoI vs field size, gap between proposed and baselines widens
# ---------------------------------------------------------------------------
def fig_crossover():
    path = os.path.join(RES, "joint_crossover.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    rows.sort(key=lambda r: float(r["L_m"]))
    L = np.array([float(r["L_m"]) / 1000 for r in rows])
    prop = np.array([float(r["proposed_min"]) for r in rows])
    single = np.array([float(r["single_min"]) for r in rows])
    cov = np.array([float(r["coverage_min"]) for r in rows])
    gain = np.array([float(r["gain_pct"]) for r in rows])

    fig, ax = plt.subplots(figsize=(3.5, 3.2))
    # shaded band = the advantage of the proposed method over coverage baseline
    ax.fill_between(L, prop, cov, color=ACCENT, alpha=0.12, zorder=1,
                    label="advantage region")
    ax.plot(L, cov, marker="^", ms=4, color=OI["verm"], label="coverage-optimal")
    ax.plot(L, single, marker="s", ms=4, color=OI["green"],
            label="single pooled station")
    ax.plot(L, prop, marker="o", ms=4, color=ACCENT, label="proposed (ours)")

    # annotate the widening gain at both ends
    ax.annotate(r"$+%.1f\%%$" % gain[0], xy=(L[0], (prop[0] + cov[0]) / 2),
                xytext=(L[0] + 0.4, (prop[0] + cov[0]) / 2 - 3), fontsize=8.5,
                color=ACCENT)
    ax.annotate(r"$+%.1f\%%$" % gain[-1], xy=(L[-1], (prop[-1] + cov[-1]) / 2),
                xytext=(L[-1] - 4.5, (prop[-1] + cov[-1]) / 2 + 2), fontsize=8.5,
                color=ACCENT, fontweight="bold")
    ax.annotate("gap widens as\ntravel dominates",
                xy=(L[-2], (prop[-2] + cov[-2]) / 2),
                xytext=(6.0, 56), fontsize=8, color=OI["grey"], ha="left",
                arrowprops=dict(arrowstyle="->", color=OI["grey"], lw=1.0))

    ax.set_xlabel("Field side length (km)")
    ax.set_ylabel("Peak AoI (min)")
    style_axes(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    save(fig, "fig_crossover.png")


# ---------------------------------------------------------------------------
# fig_ablation: contribution of each ingredient (sorted bars, proposed accent)
# ---------------------------------------------------------------------------
def fig_ablation():
    path = os.path.join(RES, "joint_ablation.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    methods = [k for k in rows[0].keys() if k != "seed"]
    means = {}
    for m in methods:
        vals = [float(r[m]) / 60.0 for r in rows if math.isfinite(float(r[m]))]
        means[m] = float(np.mean(vals)) if vals else float("nan")

    # gain from adding CETSP tour = (no_cetsp - proposed) / no_cetsp
    cetsp_gain = (means["no_cetsp"] - means["proposed"]) / means["no_cetsp"] * 100.0
    # gain from contention-aware placement = (coverage - proposed) / coverage
    place_gain = (means["coverage"] - means["proposed"]) / means["coverage"] * 100.0

    pretty = {
        "proposed": "proposed",
        "no_cetsp": "no CETSP tour",
        "coverage": "coverage place.",
        "roundrobin": "round-robin",
        "single_station": "single station",
    }
    order = sorted(methods, key=lambda m: means[m])  # ascending: best (lowest) first
    labels = [pretty.get(m, m) for m in order]
    vals = [means[m] for m in order]
    colors = [ACCENT if m == "proposed" else OI["grey"] for m in order]

    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    bars = ax.bar(range(len(order)), vals, color=colors, width=0.68,
                  edgecolor="white", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.4, "%.1f" % v,
                ha="center", va="bottom", fontsize=8)

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8.5)
    ax.set_ylabel("Peak AoI (min)")
    ax.set_ylim(0, max(vals) * 1.18)
    style_axes(ax, grid_axis="y")

    ax.set_title("Ablation at $L{=}15$ km\n"
                 "CETSP $+%.1f\\%%$, contention-aware placement $+%.1f\\%%$"
                 % (cetsp_gain, place_gain), fontsize=9)
    save(fig, "fig_ablation.png")


def fig_optgap():
    path = os.path.join(RES, "optimality_gap.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    M = [int(r["M"]) for r in rows]
    gmean = [float(r["gap_mean_pct"]) for r in rows]
    gmax = [float(r["gap_max_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    ax.plot(M, gmean, marker="o", color=ACCENT, label="mean gap")
    ax.plot(M, gmax, marker="s", ls="--", color=OI["orange"], label="max gap")
    ax.axhline(0, color=OI["grey"], lw=0.8)
    ax.set_xlabel("Swarm size $M$")
    ax.set_ylabel("Optimality gap (%)")
    ax.set_ylim(bottom=-0.5)
    ax.set_title("Greedy solver vs exact optimum")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig_optgap.png")


def fig_sensitivity():
    path = os.path.join(RES, "sensitivity.csv")
    if not os.path.exists(path):
        return
    rows = load(path)
    labels, gains = [], []
    for r in rows:
        sw, val = r["sweep"], r["value"]
        if sw == "r_c":
            labels.append(r"$r_c{=}%d$" % int(float(val)))
        elif sw == "tau_charge_min":
            labels.append(r"$\tau_{\mathrm{c}}{=}%.0f$" % float(val))
        elif sw.startswith("distribution:"):
            labels.append(sw.split(":")[1])
        else:
            labels.append(sw)
        gains.append(float(r["gain_pct"]))
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    x = range(len(labels))
    ax.bar(x, gains, color=ACCENT)
    for i, g in enumerate(gains):
        ax.text(i, g + 0.3, "%.1f" % g, ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Gain over single (%)")
    ax.set_title("Robustness: proposed vs single pooled station (L=14 km)")
    style_axes(ax, grid_axis="y")
    save(fig, "fig_sensitivity.png")


def fig_scale():
    path = os.path.join(RES, "scale.csv")
    if not os.path.exists(path):
        return
    rows = sorted(load(path), key=lambda r: int(r["M"]))
    M = [int(r["M"]) for r in rows]
    prop = [float(r["proposed_min"]) for r in rows]
    single = [float(r["single_min"]) for r in rows]
    cov = [float(r["coverage_min"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.plot(M, cov, marker="^", color=OI["verm"], label="coverage-optimal")
    ax.plot(M, single, marker="s", color=OI["green"], label="single pooled station")
    ax.plot(M, prop, marker="o", color=ACCENT, label="proposed (ours)")
    ax.set_xlabel("Swarm size $M$ ($K{=}8M$ sensors)")
    ax.set_ylabel("Peak AoI (min)")
    ax.set_title("Scaling to a large swarm (capacity grows with $M$)")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig_scale.png")


if __name__ == "__main__":
    fig_des()            # queue-model validation vs DES
    fig_scale()          # large-swarm scaling
    fig_prop1_phys()     # U-shape family (congestion threshold)
    fig_mstar()          # provisioning M*(capacity)
    fig_prop2()          # coverage vs traffic placement (per seed)
    fig_crossover()      # distributed wins as travel dominates
    fig_ablation()       # ingredient contributions
    fig_optgap()         # optimality gap vs exact optimum
    fig_sensitivity()    # robustness sweeps (r_c, tau_charge, clustered)
