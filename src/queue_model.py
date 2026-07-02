"""
Analytical M/M/c charging-queue model for swarm-UAV age-optimal data collection.

This module implements the load-bearing coupling from formulation.md:
- Erlang-C expected queue wait W_q(lambda, c, mu).
- The (lambda, T_cycle) fixed point that links swarm size M to congestion.
- Peak AoI as (patrol revisit) + (one charging excursion), which is the correct
  worst-case revisit gap for a UAV that leaves its sub-field to recharge.

Everything is kept semi-analytical so the smoke test runs in seconds with no GPU.
"""

import math


def erlang_c(c: int, a: float) -> float:
    """Erlang-C probability that an arriving customer must wait.

    c : number of parallel servers (charging ports).
    a : offered load lambda/mu (in Erlangs).
    Returns P(wait) in [0, 1]; returns 1.0 if the system is unstable (a >= c).
    """
    if a >= c:
        return 1.0
    # Sum_{n=0}^{c-1} a^n / n!  computed stably.
    s = 0.0
    term = 1.0  # a^0 / 0!
    for n in range(c):
        if n > 0:
            term *= a / n
        s += term
    # Last-server term a^c / (c! (1 - a/c)).
    top = term * (a / c) / (1.0 - a / c)  # term is a^{c-1}/(c-1)!, so *a/c gives a^c/c!
    return top / (s + top)


def wq(lmbda: float, c: int, mu: float) -> float:
    """Expected time spent waiting in queue (not counting service), M/M/c.

    Returns math.inf if unstable (rho >= 1).
    """
    a = lmbda / mu
    rho = a / c
    if rho >= 1.0:
        return math.inf
    return erlang_c(c, a) / (c * mu - lmbda)


def solve_fixed_point(M: int, c: int, mu: float, tau_fly: float,
                      tau_charge: float, tol: float = 1e-12, it: int = 200):
    """Solve lambda = M / (tau_fly + W_q(lambda) + tau_charge) self-consistently.

    Define h(lambda) = M/(tau_fly + W_q(lambda) + tau_charge) - lambda on the
    open interval (0, c*mu). W_q is increasing in lambda, so the first term is
    decreasing and h is strictly decreasing => a UNIQUE root, found by bisection.
    This is monotone in M by construction (no oscillation/cap artifacts).
    Returns (lambda, W_q, rho, stable).
    """
    cap = c * mu

    def h(lam):
        return M / (tau_fly + wq(lam, c, mu) + tau_charge) - lam

    lo, hi = 1e-15, cap * (1.0 - 1e-12)
    hlo, hhi = h(lo), h(hi)
    # h(lo) > 0 (arrival wants > 0); h(hi) -> -cap < 0 since W_q -> inf. Root exists.
    if hlo <= 0.0:
        # Degenerate: essentially no charging demand.
        lam = lo
    else:
        for _ in range(it):
            mid = 0.5 * (lo + hi)
            hm = h(mid)
            if abs(hm) < tol or (hi - lo) < tol * cap:
                lo = hi = mid
                break
            if hm > 0.0:
                lo = mid
            else:
                hi = mid
        lam = 0.5 * (lo + hi)
    w = wq(lam, c, mu)
    rho = (lam / mu) / c
    stable = rho < 1.0 and math.isfinite(w)
    return lam, w, rho, stable


def peak_aoi(M: int, c: int, mu: float, tau_fly: float, tau_charge: float,
             t_patrol: float, travel_to_station: float):
    """Peak AoI(M) = measured patrol revisit + one charging excursion.

    t_patrol : measured per-UAV patrol time for this M (from field.patrol_time),
               NOT an alpha/M abstraction, so no cross-M normalization artifact.
    excursion = round-trip travel to station + queue wait + charge time.
    Returns (aoi, details dict).
    """
    lam, w, rho, stable = solve_fixed_point(M, c, mu, tau_fly, tau_charge)
    if not stable:
        return math.inf, dict(lam=lam, wq=math.inf, rho=rho, stable=False)
    excursion = travel_to_station + w + tau_charge
    aoi = t_patrol + excursion
    return aoi, dict(lam=lam, wq=w, rho=rho, stable=True,
                     t_patrol=t_patrol, excursion=excursion)
