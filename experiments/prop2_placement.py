"""
Prop. 2 validation: placement inversion under charging contention.

Claim: with a swarm, the AoI-optimal charging-station placement / port allocation
/ assignment is TRAFFIC-driven (balances queue load), and the coverage-optimal
(min-detour, contention-blind) choice is suboptimal.

Uses the shared finite-source solver (src/solver.py), so the queue model matches
the rest of the paper (DES-validated machine-repair queue, not open M/M/c).

Run:  python experiments/prop2_placement.py
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scenario import DEFAULTS, tau_charge_of  # noqa: E402
from solver import (uav_states, candidate_sites, strategy_coverage,  # noqa: E402
                    strategy_traffic)


def main():
    sc = dict(DEFAULTS)
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    S_max, C_tot = 2, 4
    M = 12
    seeds = list(range(20))
    V = sc["V"]

    print(f"Prop.2: S_max={S_max} sites from {len(cands)} candidates, "
          f"C_tot={C_tot} ports, M={M} UAVs (finite-source queue)\n")
    print(f"{'seed':>4} | {'AoI_cov(min)':>12} {'AoI_traf(min)':>13} {'gain%':>6} | "
          f"{'sites diff':>10} {'ports diff':>10}")

    gains, cov_wins, diff_sites, diff_ports, csv_rows = [], 0, 0, 0, []
    for sd in seeds:
        states = uav_states(sc, M, sd)
        A = strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, V)
        B = strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V)
        gain = 100.0 * (A["aoi"] - B["aoi"]) / A["aoi"] if math.isfinite(A["aoi"]) and math.isfinite(B["aoi"]) else float("nan")
        if math.isfinite(gain):
            gains.append(gain)
        sdiff = set(A["combo"]) != set(B["combo"])
        pdiff = sorted(A["ports"]) != sorted(B["ports"])
        diff_sites += int(sdiff)
        diff_ports += int(pdiff)
        cov_wins += int(math.isfinite(B["aoi"]) and B["aoi"] <= A["aoi"] + 1e-9)
        print(f"{sd:>4} | {A['aoi']/60:>12.2f} {B['aoi']/60:>13.2f} {gain:>6.1f} | "
              f"{str(sdiff):>10} {str(pdiff):>10}")
        csv_rows.append([sd, A["aoi"], B["aoi"], gain, int(sdiff), int(pdiff)])

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "prop2_placement.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "aoi_cov_s", "aoi_traf_s", "gain_pct", "sites_differ", "ports_differ"])
        w.writerows(csv_rows)

    print()
    if gains:
        print(f"Mean AoI reduction (traffic vs coverage): {sum(gains)/len(gains):.1f}%")
    print(f"Traffic-optimal <= coverage-optimal in {cov_wins}/{len(seeds)} seeds")
    print(f"Chosen SITES differ in {diff_sites}/{len(seeds)} seeds; "
          f"PORT allocation differs in {diff_ports}/{len(seeds)} seeds")
    print("\nSaved results/prop2_placement.csv")
    if gains and sum(gains) / len(gains) > 1.0:
        print("-> Prop.2 SUPPORTED: AoI-optimal placement is traffic-driven and beats coverage.")
    else:
        print("-> Prop.2 NOT clearly supported; investigate.")


if __name__ == "__main__":
    main()
