"""
Joint solver for the swarm-UAV age-optimal data-collection problem, and the
baselines it is compared against.

Blocks (block-coordinate / alternating):
  - trajectory : CETSP hover-tour per UAV (GPU, src/trajectory) OR NN+2-opt proxy.
  - queue      : per-station M/M/c_s fixed point (src/queue_model).
  - ports      : integer allocation searched jointly with placement.
  - assignment : greedy load balancing of UAVs to open stations.
  - placement  : outer search over candidate sites.

The PROPOSED method uses CETSP trajectories + traffic-optimal (contention-aware)
placement/ports/assignment. Baselines drop one or more of these to isolate the
contribution.
"""

import itertools
import math

from energy import propulsion_power, hover_power
from comms import collect_time
from field import partition_field, _group_tour_len, _centroid
from queue_model import finite_source_wq
from trajectory import optimize_trajectories


# ---------- per-UAV states (geometry + physical cycle) ----------

def uav_states(sc, M, seed, trajectory="cetsp", r_c=200.0):
    """Per-UAV: centroid, revisit period t_loop [s], flight budget tau_fly [s]."""
    pts, groups = partition_field(sc["K"], sc["L"], M, seed)
    if trajectory == "cetsp":
        t_fly_loops, _ = optimize_trajectories(groups, r_c, sc["V"], seed=seed)
    else:  # NN+2-opt proxy
        t_fly_loops = [_group_tour_len(g) / sc["V"] for g in groups]

    P_cruise = propulsion_power(sc["V"])
    P_hover = hover_power()
    states = []
    for g, t_fly_loop in zip(groups, t_fly_loops):
        n = len(g)
        cen = _centroid(g)
        mean_d = sum(math.dist(p, cen) for p in g) / n
        t_collect_loop = n * collect_time(mean_d, sc["packet_bits"])
        t_loop = t_fly_loop + t_collect_loop
        e_loop = P_cruise * t_fly_loop + P_hover * t_collect_loop
        E_usable = sc["E_max"] * (1.0 - sc["E_reserve"])
        n_loops = max(1.0, math.floor(E_usable / e_loop))
        tau_fly = n_loops * t_loop
        states.append(dict(centroid=cen, t_loop=t_loop, tau_fly=tau_fly))
    return states


# ---------- peak-AoI evaluation for a given placement ----------

def peak_aoi(states, sites, ports, assign, mu, tau_charge, V, reach_budget=None):
    """Peak AoI [s]. If reach_budget is given (max one-way flight TIME a UAV can
    afford to reach its station), any UAV whose station is unreachable makes the
    configuration infeasible (inf) -- this is what forces distributed placement
    in large fields."""
    peak = 0.0
    for s in range(len(sites)):
        idx = [i for i, a in enumerate(assign) if a == s]
        if not idx:
            continue
        if ports[s] <= 0:
            return math.inf
        tau_fly_mean = sum(states[i]["tau_fly"] for i in idx) / len(idx)
        # Finite-source (machine-repair) wait: the correct closed-loop model for
        # the UAVs cycling to this station (validated vs DES). Always stable.
        w, _, _, _ = finite_source_wq(len(idx), ports[s], tau_fly_mean, tau_charge)
        for i in idx:
            d = math.dist(states[i]["centroid"], sites[s])
            if reach_budget is not None and d / V > reach_budget:
                return math.inf                     # station unreachable on remaining energy
            peak = max(peak, states[i]["t_loop"] + 2.0 * d / V + w + tau_charge)
    return peak


def nearest_assign(states, sites):
    return [min(range(len(sites)), key=lambda s: math.dist(st["centroid"], sites[s]))
            for st in states]


def greedy_balance(states, sites, ports, mu, tau_charge, V, assign0, reach_budget=None):
    assign = list(assign0)
    best = peak_aoi(states, sites, ports, assign, mu, tau_charge, V, reach_budget)
    improved = True
    while improved:
        improved = False
        for i in range(len(states)):
            cur = assign[i]
            for s in range(len(sites)):
                if s == cur:
                    continue
                assign[i] = s
                val = peak_aoi(states, sites, ports, assign, mu, tau_charge, V, reach_budget)
                if val < best - 1e-9:
                    best, improved = val, True
                    break
                assign[i] = cur
            if improved:
                break
    return assign, best


def _port_splits(total, bins):
    if bins == 1:
        yield (total,)
        return
    for x in range(1, total - bins + 2):
        for rest in _port_splits(total - x, bins - 1):
            yield (x,) + rest


def candidate_sites(L, n=3):
    xs = [L * (i + 1) / (n + 1) for i in range(n)]
    return [(x, y) for x in xs for y in xs]


# ---------- strategies ----------

def strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V, reach_budget=None):
    """Contention-aware: joint site + port split + load-balanced assignment."""
    best = None
    for combo in itertools.combinations(range(len(cands)), S_max):
        sites = [cands[j] for j in combo]
        for ports in _port_splits(C_tot, S_max):
            assign0 = nearest_assign(states, sites)
            assign, val = greedy_balance(states, sites, list(ports), mu, tau_charge, V, assign0, reach_budget)
            if best is None or val < best["aoi"]:
                best = dict(aoi=val, sites=sites, ports=list(ports), assign=assign, combo=combo)
    return best


def strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, V, reach_budget=None):
    """Contention-blind: min-detour sites, even ports, nearest assignment."""
    best = None
    for combo in itertools.combinations(range(len(cands)), S_max):
        sites = [cands[j] for j in combo]
        assign = nearest_assign(states, sites)
        detour = sum(math.dist(states[i]["centroid"], sites[assign[i]]) for i in range(len(states)))
        if best is None or detour < best[0]:
            best = (detour, sites, assign, combo)
    _, sites, assign, combo = best
    base = C_tot // S_max
    ports = [base] * S_max
    for k in range(C_tot - base * S_max):
        ports[k] += 1
    return dict(aoi=peak_aoi(states, sites, ports, assign, mu, tau_charge, V, reach_budget),
                sites=sites, ports=ports, assign=assign, combo=combo)


# ---------- full methods (proposed + baselines) ----------

def solve(sc, M, seed, method, cands=None, S_max=2, C_tot=4):
    """Return peak AoI [s] for the chosen method.

    methods:
      proposed      : CETSP trajectory + traffic-optimal placement.
      no_cetsp      : NN proxy trajectory + traffic-optimal placement (ablate traj).
      coverage      : CETSP trajectory + coverage-optimal placement (ablate contention).
      single_station: CETSP trajectory + one central station, all ports pooled (Wei-style).
      roundrobin    : CETSP trajectory + coverage sites + round-robin assignment.
    """
    mu = 1.0 / (sc["E_max"] / sc["charge_power"])
    tau_charge = sc["E_max"] / sc["charge_power"]
    cands = cands or candidate_sites(sc["L"], n=3)
    V = sc["V"]
    # Reachability: one-way flight TIME a UAV can afford on its energy reserve.
    reach = (sc["E_reserve"] * sc["E_max"] / propulsion_power(V)) if sc.get("reachability", False) else None

    traj = "nn" if method == "no_cetsp" else "cetsp"
    states = uav_states(sc, M, seed, trajectory=traj)

    if method in ("proposed", "no_cetsp"):
        return strategy_traffic(states, cands, S_max, C_tot, mu, tau_charge, V, reach)["aoi"]
    if method == "coverage":
        return strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, V, reach)["aoi"]
    if method == "single_station":
        center = (sc["L"] / 2.0, sc["L"] / 2.0)
        assign = [0] * len(states)
        return peak_aoi(states, [center], [C_tot], assign, mu, tau_charge, V, reach)
    if method == "roundrobin":
        cov = strategy_coverage(states, cands, S_max, C_tot, mu, tau_charge, V, reach)
        sites, ports = cov["sites"], cov["ports"]
        assign = [i % S_max for i in range(len(states))]
        return peak_aoi(states, sites, ports, assign, mu, tau_charge, V, reach)
    raise ValueError(method)
