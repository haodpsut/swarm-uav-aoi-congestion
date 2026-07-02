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


def simulate(M, c, tau_fly, tau_charge, travel, service="det", operating="det",
             jitter=0.15, horizon_cycles=400, seed=0, warmup=40):
    """Event-driven single-station queue with M cycling UAVs and c ports.

    operating/service in {"exp","det"}: exponential vs near-deterministic
    patrol-between-charges / charge duration. "exp"+"exp" reproduces the
    finite-source M/M/c//N assumptions (formula check); "det"+"det" is the
    realistic system. Returns the mean queue wait per charging visit (steady
    state, after warmup).
    """
    rng = random.Random(seed)

    def patrol_budget():
        if operating == "exp":
            return rng.expovariate(1.0 / tau_fly)
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

    print("Mean queue wait Wq [s]. DES columns: 'MM' = exp operating + exp service "
          "(== finite-source assumptions); 'real' = deterministic (the true system).\n")
    print(f"{'M':>3} {'c':>2} {'rho':>5} | {'MMc':>8} {'FiniteS':>8} | "
          f"{'DES_MM':>7} {'FS/MM':>6} | {'DESreal':>7} {'FS/real':>7}")
    rows = []
    for M, c in configs:
        lam, w_mmc, rho, stable = solve_fixed_point(M, c, mu, tau_fly, tau_charge)
        if not stable:
            continue
        # up-time = patrol budget + round-trip travel (matches the DES cycle).
        up_time = tau_fly + 2.0 * travel
        w_fs, Lq, lam_eff, rho_fs = finite_source_wq(M, c, up_time, tau_charge)

        # DES with exp-operating + exp-service reproduces finite-source assumptions.
        des_mm = sum(simulate(M, c, tau_fly, tau_charge, travel, "exp", "exp", seed=s) for s in seeds) / len(seeds)
        # DES with deterministic operating + service is the realistic system.
        des_real = sum(simulate(M, c, tau_fly, tau_charge, travel, "det", "det", seed=s) for s in seeds) / len(seeds)
        r_mm = f"{w_fs / des_mm:.2f}" if des_mm > 0.5 else "  -"   # 0/0 at ~no-load
        r_real = f"{w_fs / des_real:.2f}" if des_real > 0.5 else "  -"
        print(f"{M:>3} {c:>2} {rho_fs:>5.2f} | {w_mmc:>8.1f} {w_fs:>8.1f} | "
              f"{des_mm:>7.1f} {r_mm:>6} | {des_real:>7.1f} {r_real:>7}")
        rows.append([M, c, rho_fs, w_mmc, w_fs, des_mm, des_real])

    # (1) Formula check: finite-source should MATCH DES under exp-operating+service.
    mm_pairs = [(r[4], r[5]) for r in rows if r[5] > 1.0]
    if mm_pairs:
        err = sum(abs(wf - de) / de for wf, de in mm_pairs) / len(mm_pairs)
        print(f"\n[formula check] finite-source vs DES(exp op+svc): mean rel. error "
              f"= {100*err:.1f}% (small -> the M/M/c//N formula is correct).")
    # (2) Realism: finite-source is a CONSERVATIVE upper bound on the real system.
    real_pairs = [(r[4], r[6]) for r in rows if r[6] > 1.0]
    if real_pairs:
        cons = sum(1 for wf, dr in real_pairs if wf >= dr - 1e-6)
        fac = sum(wf / dr for wf, dr in real_pairs) / len(real_pairs)
        print(f"[realism] finite-source >= DES(real) in {cons}/{len(real_pairs)} "
              f"configs (conservative), mean factor {fac:.1f}x. Real waits are lower "
              f"because operating+charging are near-deterministic, not exponential.")
    # (3) Why M/M/c is wrong.
    mmc_pairs = [(r[3], r[5]) for r in rows if r[5] > 1.0]
    if mmc_pairs:
        fac = sum(wm / de for wm, de in mmc_pairs) / len(mmc_pairs)
        print(f"[open M/M/c] over-predicts DES(exp) by {fac:.1f}x -> the WRONG model "
              f"(its bias distorted decisions, e.g. a spurious placement crossover).")

    out = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "des_validation.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["M", "c", "rho", "mmc_wq", "finite_wq", "des_mm_wq", "des_real_wq"])
        w.writerows(rows)
    print("\nSaved results/des_validation.csv")


if __name__ == "__main__":
    main()
