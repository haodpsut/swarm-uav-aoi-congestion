"""
Prop. 1 validation with the PHYSICAL model (rotary-wing energy + air-to-ground
comms, SI units). Confirms the non-monotone AoI(M) congestion threshold survives
when the flight budget is derived from real battery drain instead of a constant.

Single central charging station with c pooled ports (optimal-assignment upper
bound). Per-UAV heterogeneity (sub-field size, station distance) enters the AoI;
the shared queue wait W_q comes from the aggregate fixed point.

Run:  python experiments/validate_prop1_phys.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from field import patrol_geometry          # noqa: E402
from scenario import DEFAULTS, tau_charge_of, per_uav_cycle  # noqa: E402
from queue_model import finite_source_wq   # noqa: E402


def swarm_peak_aoi(M, c, sc, seed):
    """Peak AoI over the swarm for M UAVs, c pooled ports, one central station.

    Uses the finite-source (machine-repair) queue -- the DES-validated model for
    cycling UAVs (the open M/M/c over-predicts wait ~6x, see des_validation.py).
    """
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    geom = patrol_geometry(sc["K"], sc["L"], M, seed)
    center = (sc["L"] / 2.0, sc["L"] / 2.0)

    t_loops, tau_flys, dists = [], [], []
    for gz in geom:
        t_loop, tau_fly, _ = per_uav_cycle(
            sc["V"], sc["E_max"], sc["E_reserve"],
            gz["tour_len"], gz["n"], gz["mean_collect_d"], sc["packet_bits"])
        t_loops.append(t_loop)
        tau_flys.append(tau_fly)
        dists.append(math.dist(gz["centroid"], center))

    if not t_loops:
        return math.inf, 0.0
    tau_fly_mean = sum(tau_flys) / len(tau_flys)
    mean_travel = sum(2.0 * d / sc["V"] for d in dists) / len(dists)
    up_time = tau_fly_mean + mean_travel      # operating time incl. round-trip travel
    w, _, _, rho = finite_source_wq(M, c, up_time, tau_charge)
    aoi = max(t_loops[i] + 2.0 * dists[i] / sc["V"] + w + tau_charge
              for i in range(len(t_loops)))
    return aoi, rho


def main():
    sc = dict(DEFAULTS)
    M_values = list(range(1, 21))
    seeds = list(range(30))
    capacities = [1, 2, 3, 4, 6, 8, 12]

    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    print(f"Scenario: K={sc['K']} sensors, {sc['L']/1000:.0f}x{sc['L']/1000:.0f} km, "
          f"V={sc['V']} m/s, battery {sc['E_max']/3600:.0f} Wh, "
          f"tau_charge={tau_charge/60:.1f} min\n")

    all_rows, mstar_rows = [], []
    print(f"{'c':>3} {'M*':>3} {'AoI@M* (min)':>13}")
    for c in capacities:
        rows = []
        for M in M_values:
            vals, rhos = [], []
            for sd in seeds:
                aoi, rho = swarm_peak_aoi(M, c, sc, sd)
                vals.append(aoi)
                rhos.append(rho if rho is not None else 0.0)
            finite = [v for v in vals if math.isfinite(v)]
            if finite:
                mean = sum(finite) / len(finite)
                std = math.sqrt(sum((v - mean) ** 2 for v in finite) / len(finite))
            else:
                mean, std = math.inf, 0.0
            rows.append(dict(c=c, M=M, aoi_mean=mean, aoi_std=std,
                             rho=sum(rhos) / len(rhos),
                             unstable=sum(1 for v in vals if not math.isfinite(v)) / len(vals)))
        all_rows.extend(rows)
        finite = [r for r in rows if math.isfinite(r["aoi_mean"])]
        best = min(finite, key=lambda r: r["aoi_mean"]) if finite else None
        if best:
            mstar_rows.append(dict(c=c, M_star=best["M"], aoi=best["aoi_mean"]))
            print(f"{c:>3} {best['M']:>3} {best['aoi_mean']/60:>13.2f}")

    ms = [r["M_star"] for r in mstar_rows]
    mono = all(ms[i] <= ms[i + 1] for i in range(len(ms) - 1))
    print(f"\nProvisioning law (M* non-decreasing in capacity): {'HOLDS' if mono else 'VIOLATED'}")
    print(f"  c={[r['c'] for r in mstar_rows]}  ->  M*={ms}")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "prop1_phys_curves.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["c", "M", "aoi_mean_s", "aoi_std_s", "rho", "unstable_frac"])
        for r in all_rows:
            w.writerow([r["c"], r["M"], r["aoi_mean"], r["aoi_std"], r["rho"], r["unstable"]])
    mu = 1.0 / tau_charge
    with open(os.path.join(out, "prop1_phys_mstar.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["c", "capacity", "M_star", "aoi_at_mstar_s"])
        for r in mstar_rows:
            w.writerow([r["c"], r["c"] * mu, r["M_star"], r["aoi"]])
    print("\nSaved results/prop1_phys_curves.csv and results/prop1_phys_mstar.csv")


if __name__ == "__main__":
    main()
