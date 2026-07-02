"""
Field / patrol geometry: derive the coverage coefficient alpha empirically
(NOT from a hand-picked constant), so the U-shape test is honest.

alpha is the per-UAV patrol revisit time scaled so that T_patrol = alpha / M:
we place K sensors at random, partition them into M balanced sub-fields by
k-means, build a nearest-neighbour tour per sub-field, take the mean tour time,
and back out alpha = M * mean_tour_time. Averaging over sensor realisations gives
a seed-dependent alpha, used for multi-seed robustness.
"""

import math
import random


def _kmeans(points, k, rng, iters=25):
    """Tiny k-means (balanced-ish) to partition sensors among UAVs."""
    centers = [list(points[rng.randrange(len(points))]) for _ in range(k)]
    assign = [0] * len(points)
    for _ in range(iters):
        for i, p in enumerate(points):
            best, bd = 0, float("inf")
            for j, cth in enumerate(centers):
                d = (p[0] - cth[0]) ** 2 + (p[1] - cth[1]) ** 2
                if d < bd:
                    bd, best = d, j
            assign[i] = best
        for j in range(k):
            pts = [points[i] for i in range(len(points)) if assign[i] == j]
            if pts:
                centers[j] = [sum(x) / len(pts) for x in zip(*pts)]
    groups = [[points[i] for i in range(len(points)) if assign[i] == j] for j in range(k)]
    return groups


def _nn_tour_length(pts):
    """Closed nearest-neighbour tour length over pts (heuristic patrol route)."""
    if len(pts) <= 1:
        return 0.0
    unvisited = pts[:]
    cur = unvisited.pop(0)
    start = cur
    total = 0.0
    while unvisited:
        nxt_i, nd = 0, float("inf")
        for i, p in enumerate(unvisited):
            d = math.dist(cur, p)
            if d < nd:
                nd, nxt_i = d, i
        total += nd
        cur = unvisited.pop(nxt_i)
    total += math.dist(cur, start)  # close the loop
    return total


def coverage_alpha(K: int, L: float, M: int, V: float, seed: int) -> float:
    """Empirical alpha such that per-UAV patrol time ~ alpha / M for this M.

    Returns alpha = M * (mean per-sub-field tour time). Because tour length of n
    points in area A scales ~ sqrt(n*A), alpha is roughly M-invariant, which is
    exactly the 1/M coverage benefit we want to test rather than assume.
    """
    rng = random.Random(seed)
    pts = [(rng.uniform(0, L), rng.uniform(0, L)) for _ in range(K)]
    groups = _kmeans(pts, M, rng)
    tour_times = [_nn_tour_length(g) / V for g in groups if g]
    mean_tour = sum(tour_times) / len(tour_times)
    return M * mean_tour
