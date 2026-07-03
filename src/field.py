"""
Field / patrol geometry: measure the per-UAV patrol time DIRECTLY (not via an
alpha/M abstraction), so the coverage term of peak AoI carries no cross-M
normalization artifact.

patrol_time(K,L,M,V,seed): place K sensors at random (fixed by seed, so the SAME
field is reused across all M within a seed), partition into M groups by k-means,
build a nearest-neighbour tour improved by 2-opt per group, and return the mean
per-UAV tour time. This is T_patrol(M); it decreases ~1/M but is a real measured
geometry, averaged over seeds for robustness.
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


def _nn_order(pts):
    """Nearest-neighbour visiting order over pts (indices into a closed tour)."""
    unvisited = list(range(len(pts)))
    cur = unvisited.pop(0)
    order = [cur]
    while unvisited:
        nxt_i, nd = 0, float("inf")
        for i, j in enumerate(unvisited):
            d = math.dist(pts[cur], pts[j])
            if d < nd:
                nd, nxt_i = d, i
        cur = unvisited.pop(nxt_i)
        order.append(cur)
    return order


def _tour_len(pts, order):
    n = len(order)
    return sum(math.dist(pts[order[i]], pts[order[(i + 1) % n]]) for i in range(n))


def _two_opt(pts, order, max_pass=6):
    """Light 2-opt to stabilise tour length (reduces NN heuristic variance)."""
    n = len(order)
    if n < 4:
        return order
    improved = True
    passes = 0
    while improved and passes < max_pass:
        improved = False
        passes += 1
        for i in range(n - 1):
            for k in range(i + 1, n):
                a, b = order[i], order[(i + 1) % n]
                c, d = order[k], order[(k + 1) % n]
                if a == c or b == d:
                    continue
                delta = (math.dist(pts[a], pts[c]) + math.dist(pts[b], pts[d])
                         - math.dist(pts[a], pts[b]) - math.dist(pts[c], pts[d]))
                if delta < -1e-12:
                    order[i + 1:k + 1] = reversed(order[i + 1:k + 1])
                    improved = True
    return order


def _group_tour_len(pts):
    if len(pts) <= 1:
        return 0.0
    order = _two_opt(pts, _nn_order(pts))
    return _tour_len(pts, order)


def patrol_time(K: int, L: float, M: int, V: float, seed: int) -> float:
    """Measured mean per-UAV patrol (revisit) time T_patrol(M) for this field.

    Same field per seed (reused across M); k-means into M groups; 2-opt tour per
    group; return mean tour time. Peak AoI uses this directly (no alpha/M).
    """
    rng = random.Random(seed)
    pts = [(rng.uniform(0, L), rng.uniform(0, L)) for _ in range(K)]
    groups = _kmeans(pts, M, rng)
    tour_times = [_group_tour_len(g) / V for g in groups if g]
    return sum(tour_times) / len(tour_times)


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def partition_field(K: int, L: float, M: int, seed: int, clustered: bool = False):
    """Return (points, groups): the sensor set and its k-means partition into M
    sub-fields (list of coord-lists). Same field per seed. Used by the GPU
    trajectory optimizer, which needs raw sensor coordinates per UAV.

    clustered=True places sensors in a few Gaussian hotspots instead of
    uniformly (a non-uniform robustness scenario for the experiments)."""
    rng = random.Random(seed)
    if clustered:
        n_c = 4
        centers = [(rng.uniform(0.15 * L, 0.85 * L),
                    rng.uniform(0.15 * L, 0.85 * L)) for _ in range(n_c)]
        sd = 0.08 * L
        pts = []
        for _ in range(K):
            cx, cy = centers[rng.randrange(n_c)]
            x = min(L, max(0.0, rng.gauss(cx, sd)))
            y = min(L, max(0.0, rng.gauss(cy, sd)))
            pts.append((x, y))
    else:
        pts = [(rng.uniform(0, L), rng.uniform(0, L)) for _ in range(K)]
    groups = _kmeans(pts, M, rng)
    return pts, [g for g in groups if g]


def patrol_geometry(K: int, L: float, M: int, seed: int):
    """Per-UAV sub-field geometry for the physical model (SI metres).

    Returns a list of M dicts: {tour_len, n, centroid, mean_collect_d}, where
    mean_collect_d is the mean sensor distance to its sub-field centroid (a
    proxy for the horizontal offset at collection). Same field per seed.
    """
    rng = random.Random(seed)
    pts = [(rng.uniform(0, L), rng.uniform(0, L)) for _ in range(K)]
    groups = _kmeans(pts, M, rng)
    out = []
    for g in groups:
        if not g:
            continue
        cen = _centroid(g)
        mean_d = sum(math.dist(p, cen) for p in g) / len(g)
        out.append(dict(tour_len=_group_tour_len(g), n=len(g),
                        centroid=cen, mean_collect_d=mean_d))
    return out
