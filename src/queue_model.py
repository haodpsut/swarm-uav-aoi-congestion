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
                      tau_charge: float, tol: float = 1e-9, it: int = 10000):
    """Solve lambda = M / (tau_fly + W_q(lambda) + tau_charge) self-consistently.

    The map is self-limiting: larger W_q lowers lambda, so a simple damped
    iteration converges. Returns (lambda, W_q, rho, stable).
    """
    lam = 0.5 * min(M / (tau_fly + tau_charge), c * mu * 0.999)
    for _ in range(it):
        w = wq(lam, c, mu)
        if math.isinf(w):
            # Pull lambda back below capacity and continue.
            lam = 0.9 * (c * mu)
            w = wq(lam, c, mu)
        new = M / (tau_fly + w + tau_charge)
        new = min(new, 0.999999 * c * mu)  # keep strictly stable
        if abs(new - lam) < tol:
            lam = new
            break
        lam = 0.5 * lam + 0.5 * new  # damping
    w = wq(lam, c, mu)
    rho = (lam / mu) / c
    stable = rho < 1.0 and math.isfinite(w)
    return lam, w, rho, stable


def peak_aoi(M: int, c: int, mu: float, tau_fly: float, tau_charge: float,
             alpha: float, travel_to_station: float):
    """Peak AoI(M) = patrol revisit (alpha/M) + one charging excursion.

    excursion = round-trip travel to station + queue wait + charge time.
    Returns (aoi, details dict).
    """
    lam, w, rho, stable = solve_fixed_point(M, c, mu, tau_fly, tau_charge)
    if not stable:
        return math.inf, dict(lam=lam, wq=math.inf, rho=rho, stable=False)
    t_patrol = alpha / M
    excursion = travel_to_station + w + tau_charge
    aoi = t_patrol + excursion
    return aoi, dict(lam=lam, wq=w, rho=rho, stable=True,
                     t_patrol=t_patrol, excursion=excursion)
