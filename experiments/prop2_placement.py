"""
Prop. 2 validation: placement inversion under charging contention.

Claim: with a swarm, the AoI-optimal charging-station placement / port allocation
/ assignment is TRAFFIC-driven (balances queue load), and the coverage-optimal
(min-detour, contention-blind) choice is provably suboptimal.

We compare, per seed, in the capacity-limited regime:
  A) COVERAGE-OPTIMAL : pick the S_max sites minimizing total UAV->station detour;
                        split ports evenly; assign each UAV to its nearest station.
  B) TRAFFIC-OPTIMAL  : jointly pick sites + port split + a load-balanced
                        assignment to minimize peak AoI (contention-aware).

Per-station M/M/c_s queues (each open station is its own queue). If B beats A and
its sites/ports/assignment differ, the placement decision has flipped from
coverage-driven to traffic-driven.

Run:  python experiments/prop2_placement.py
"""

import csv
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from field import patrol_geometry          # noqa: E402
from scenario import DEFAULTS, tau_charge_of, per_uav_cycle  # noqa: E402
from queue_model import solve_fixed_point   # noqa: E402


def candidate_sites(L, n=3):
    """n x n grid of candidate station positions inside the field."""
    xs = [L * (i + 1) / (n + 1) for i in range(n)]
    return [(x, y) for x in xs for y in xs]


def uav_states(sc, M, seed):
    """Per-UAV: centroid, revisit period t_loop, physical flight budget tau_fly."""
    geom = patrol_geometry(sc["K"], sc["L"], M, seed)
    states = []
    for gz in geom:
        t_loop, tau_fly, _ = per_uav_cycle(
            sc["V"], sc["E_max"], sc["E_reserve"],
            gz["tour_len"], gz["n"], gz["mean_collect_d"], sc["packet_bits"])
        states.append(dict(centroid=gz["centroid"], t_loop=t_loop, tau_fly=tau_fly))
    return states


def peak_aoi(states, sites, ports, assign, mu, tau_charge, V):
    """Peak AoI given open `sites`, `ports` per site, and UAV->site `assign`."""
    peak = 0.0
    for s in range(len(sites)):
        idx = [i for i, a in enumerate(assign) if a == s]
        if not idx:
            continue
        if ports[s] <= 0:
            return math.inf
        tau_fly_mean = sum(states[i]["tau_fly"] for i in idx) / len(idx)
        lam, w, rho, stable = solve_fixed_point(len(idx), ports[s], mu,
                                                tau_fly_mean, tau_charge)
        if not stable:
            return math.inf
        for i in idx:
            d = math.dist(states[i]["centroid"], sites[s])
            aoi = states[i]["t_loop"] + 2.0 * d / V + w + tau_charge
            peak = max(peak, aoi)
    return peak


def nearest_assign(states, sites):
    return [min(range(len(sites)), key=lambda s: math.dist(st["centroid"], sites[s]))
            for st in states]


def greedy_balance(states, sites, ports, mu, tau_charge, V, assign0):
    """Local search: move the UAV that most reduces peak AoI, until no gain."""
    assign = list(assign0)
    best = peak_aoi(states, sites, ports, assign, mu, tau_charge, V)
    improved = True
    while improved:
        improved = False
        for i in range(len(states)):
            cur = assign[i]
            for s in range(len(sites)):
                if s == cur:
                    continue
                assign[i] = s
                val = peak_aoi(states, sites, ports, assign, mu, tau_charge, V)
                if val < best - 1e-9:
                    best, improved = val, True
                    break
                assign[i] = cur
            if improved:
                break
    return assign, best


def strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, V):
    """A: min-detour sites, even ports, nearest assignment (contention-blind)."""
    best = None
    for combo in itertools.combinations(range(len(cands)), S_max):
        sites = [cands[j] for j in combo]
        assign = nearest_assign(states, sites)
        detour = sum(math.dist(states[i]["centroid"], sites[assign[i]])
                     for i in range(len(states)))
        if best is None or detour < best[0]:
            best = (detour, sites, assign, combo)
    _, sites, assign, combo = best
    base = C_tot // S_max
    ports = [base] * S_max
    for k in range(C_tot - base * S_max):
        ports[k] += 1
    aoi = peak_aoi(states, sites, ports, assign, mu, tau_charge, V)
    return dict(aoi=aoi, sites=sites, ports=ports, combo=combo)


def strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V):
    """B: joint site + port split + load-balanced assignment to min peak AoI."""
    best = None
    # enumerate port splits summing to C_tot with S_max bins, each >=1
    def splits(total, bins):
        if bins == 1:
            yield (total,)
            return
        for x in range(1, total - bins + 2):
            for rest in splits(total - x, bins - 1):
                yield (x,) + rest

    for combo in itertools.combinations(range(len(cands)), S_max):
        sites = [cands[j] for j in combo]
        for ports in splits(C_tot, S_max):
            assign0 = nearest_assign(states, sites)
            assign, val = greedy_balance(states, sites, list(ports), mu, tau_charge, V, assign0)
            if best is None or val < best["aoi"]:
                best = dict(aoi=val, sites=sites, ports=list(ports),
                            combo=combo, assign=assign)
    return best


def main():
    sc = dict(DEFAULTS)
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau_charge = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    S_max, C_tot = 2, 4          # open 2 stations, 4 ports total
    M = 12                       # capacity-limited swarm
    seeds = list(range(20))

    print(f"Prop.2: S_max={S_max} sites from {len(cands)} candidates, "
          f"C_tot={C_tot} ports, M={M} UAVs, capacity-limited\n")
    print(f"{'seed':>4} | {'AoI_cov(min)':>12} {'AoI_traf(min)':>13} {'gain%':>6} | "
          f"{'sites diff':>10} {'ports diff':>10}")

    gains, cov_wins, diff_sites, diff_ports = [], 0, 0, 0
    csv_rows = []
    for sd in seeds:
        states = uav_states(sc, M, sd)
        A = strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, sc["V"])
        B = strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, sc["V"])
        if not (math.isfinite(A["aoi"]) and math.isfinite(B["aoi"])):
            gain = float("nan")
        else:
            gain = 100.0 * (A["aoi"] - B["aoi"]) / A["aoi"]
            gains.append(gain)
        sdiff = set(A["combo"]) != set(B["combo"])
        pdiff = sorted(A["ports"]) != sorted(B["ports"])
        diff_sites += int(sdiff)
        diff_ports += int(pdiff)
        cov_wins += int(math.isfinite(B["aoi"]) and B["aoi"] <= A["aoi"] + 1e-9)
        av = A["aoi"] / 60 if math.isfinite(A["aoi"]) else float("inf")
        bv = B["aoi"] / 60 if math.isfinite(B["aoi"]) else float("inf")
        print(f"{sd:>4} | {av:>12.2f} {bv:>13.2f} {gain:>6.1f} | "
              f"{str(sdiff):>10} {str(pdiff):>10}")
        csv_rows.append([sd, A["aoi"], B["aoi"], gain, int(sdiff), int(pdiff)])

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "prop2_placement.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "aoi_cov_s", "aoi_traf_s", "gain_pct", "sites_differ", "ports_differ"])
        w.writerows(csv_rows)
    print("\nSaved results/prop2_placement.csv")

    print()
    if gains:
        mean_gain = sum(gains) / len(gains)
        print(f"Mean AoI reduction (traffic vs coverage): {mean_gain:.1f}%")
    print(f"Traffic-optimal >= coverage-optimal in {cov_wins}/{len(seeds)} seeds")
    print(f"Chosen SITES differ in {diff_sites}/{len(seeds)} seeds; "
          f"PORT allocation differs in {diff_ports}/{len(seeds)} seeds")
    if gains and sum(gains) / len(gains) > 1.0:
        print("\n-> Prop.2 SUPPORTED: the AoI-optimal placement is traffic-driven and")
        print("   beats the coverage-optimal (contention-blind) choice.")
    else:
        print("\n-> Prop.2 NOT clearly supported in this regime; investigate.")


if __name__ == "__main__":
    main()
