"""
Discrete-event simulation (DES) validating the M/M/c charging-queue surrogate.

The analytical model assumes Poisson arrivals + exponential service (Erlang-C).
Reality is different: UAV recharge arrivals are near-PERIODIC (each UAV returns
once per cycle) and charging is closer to DETERMINISTIC. This DES simulates
actual UAV agents cycling patrol -> travel -> queue (FIFS, c ports) -> charge ->
back, with per-cycle jitter, and measures the true mean queue wait. We compare it
to the Erlang-C prediction under:
  (a) exponential service  -> should MATCH M/M/c (sanity check of the simulator);
  (b) deterministic service -> the realistic case; we expect the model to be a
      conservative UPPER BOUND on wait (regular arrivals + fixed service reduce
      queueing), so peak AoI predictions are safe.

Run:  python experiments/des_validation.py
"""

import csv
import heapq
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from queue_model import wq as erlang_wq, solve_fixed_point, finite_source_wq  # noqa: E402


def simulate(M, c, tau_fly, tau_charge, travel, service="det",
             jitter=0.15, horizon_cycles=400, seed=0, warmup=40):
    """Event-driven single-station queue with M cycling UAVs and c ports.

    Returns the mean queue wait per charging visit (steady state, after warmup).
    """
    rng = random.Random(seed)

    def patrol_budget():
        return tau_fly * (1.0 + rng.uniform(-jitter, jitter))

    def charge_time():
        if service == "exp":
            return rng.expovariate(1.0 / tau_charge)
        return tau_charge  # deterministic

    # Event heap of (time, kind, uav). kind: 0 = arrive at station, 1 = depart.
    heap = []
    for u in range(M):
        # stagger initial arrivals across a cycle so they are not synchronised
        t0 = travel + patrol_budget() * (u / M)
        heapq.heappush(heap, (t0, 0, u))

    free = c
    fifo = []               # queued (arrival_time, uav)
    waits = []              # (visit_index_ok, wait)
    visit_count = 0

    while heap:
        t, kind, u = heapq.heappop(heap)
        if visit_count > M * horizon_cycles:
            break
        if kind == 0:                       # UAV arrives at station
            if free > 0:
                free -= 1
                w = 0.0
                if visit_count >= M * warmup:
                    waits.append(w)
                visit_count += 1
                heapq.heappush(heap, (t + charge_time(), 1, u))
            else:
                fifo.append((t, u))
        else:                               # UAV finishes charging
            free += 1
            # schedule its next arrival: travel back + patrol + travel to station
            nxt = t + travel + patrol_budget() + travel
            heapq.heappush(heap, (nxt, 0, u))
            if fifo:
                at, qu = fifo.pop(0)
                free -= 1
                w = t - at
                if visit_count >= M * warmup:
                    waits.append(w)
                visit_count += 1
                heapq.heappush(heap, (t + charge_time(), 1, qu))

    return sum(waits) / len(waits) if waits else 0.0


def main():
    # Homogeneous validation scenario (single pooled station).
    tau_fly, tau_charge, travel = 1500.0, 480.0, 250.0
    mu = 1.0 / tau_charge
    seeds = list(range(8))

    configs = []
    for c in (2, 3, 4):
        for M in range(2, 4 * c + 1):
            configs.append((M, c))

    print("Wq [s]: open M/M/c vs finite-source M/M/c//N vs DES "
          "(exp = exponential service, det = deterministic)\n")
    print(f"{'M':>3} {'c':>2} {'rho':>5} | {'MMc':>8} {'FiniteS':>8} | "
          f"{'DESexp':>8} {'FS/exp':>7} | {'DESdet':>8} {'FS/det':>7}")
    rows = []
    for M, c in configs:
        # open M/M/c (self-consistent fixed point)
        lam, w_mmc, rho, stable = solve_fixed_point(M, c, mu, tau_fly, tau_charge)
        if not stable:
            continue
        # finite-source (the correct closed model)
        w_fs, Lq, lam_eff, rho_fs = finite_source_wq(M, c, tau_fly, tau_charge)

        des_exp = sum(simulate(M, c, tau_fly, tau_charge, travel, "exp", seed=s) for s in seeds) / len(seeds)
        des_det = sum(simulate(M, c, tau_fly, tau_charge, travel, "det", seed=s) for s in seeds) / len(seeds)
        r_exp = w_fs / des_exp if des_exp > 0.5 else float("nan")
        r_det = w_fs / des_det if des_det > 0.5 else float("nan")
        print(f"{M:>3} {c:>2} {rho_fs:>5.2f} | {w_mmc:>8.1f} {w_fs:>8.1f} | "
              f"{des_exp:>8.1f} {r_exp:>7.2f} | {des_det:>8.1f} {r_det:>7.2f}")
        rows.append([M, c, rho_fs, w_mmc, w_fs, des_exp, des_det])

    # Accuracy of finite-source vs DES-exp (its matching regime) where wait > 1s.
    pairs = [(r[4], r[5]) for r in rows if r[5] > 1.0]
    if pairs:
        err = sum(abs(wf - de) / de for wf, de in pairs) / len(pairs)
        print(f"\nFinite-source vs DES(exp): mean rel. error = {100*err:.1f}% "
              f"(should be small -> validates the closed-queue model).")
    mmc_pairs = [(r[3], r[5]) for r in rows if r[5] > 1.0]
    if mmc_pairs:
        fac = sum(wm / de for wm, de in mmc_pairs) / len(mmc_pairs)
        print(f"Open M/M/c vs DES(exp): mean over-prediction factor = {fac:.1f}x "
              f"(why M/M/c is the WRONG model here).")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "des_validation.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["M", "c", "rho", "mmc_wq", "finite_wq", "des_exp_wq", "des_det_wq"])
        w.writerows(rows)
    print("\nSaved results/des_validation.csv")


if __name__ == "__main__":
    main()
