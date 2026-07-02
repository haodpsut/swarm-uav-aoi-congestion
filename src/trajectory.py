"""
GPU differentiable trajectory optimizer (the compute centrepiece; runs on the
RTX 4090 when CUDA is present, on CPU otherwise).

Each UAV collects data within a horizontal radius r_c of a sensor, so the patrol
is NOT a tour that visits every sensor point but the shortest closed tour of
HOVER points whose r_c-disks cover all assigned sensors -- a Close-Enough TSP
(CETSP). We optimise the hover-point coordinates by gradient descent (Adam):

    loss = sum_uav [ closed_tour_length(waypoints) + lambda_cov * coverage_pen ]

The waypoint cyclic ORDER is fixed at init (angular sort around each sub-field
centroid); only positions slide, which keeps the length term differentiable. All
UAVs of a scenario are optimised in ONE padded/masked batch, so many UAVs (and,
by stacking seeds, whole sweeps) run in parallel on the GPU.

Returns each UAV's optimised tour length; peak AoI uses tour_len / V for the
flight part of the revisit period.
"""

import math

import torch


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _angular_order(pts):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return sorted(range(len(pts)), key=lambda i: math.atan2(pts[i][1] - cy, pts[i][0] - cx))


def _kmeans_centroids(pts, k, rng_seed=0):
    """k centroids of pts (simple Lloyd) as CETSP hover-point init."""
    import random
    rng = random.Random(rng_seed)
    if len(pts) <= k:
        return [list(p) for p in pts] + [list(pts[0])] * (k - len(pts))
    cents = [list(pts[i]) for i in rng.sample(range(len(pts)), k)]
    for _ in range(15):
        buckets = [[] for _ in range(k)]
        for p in pts:
            j = min(range(k), key=lambda c: (p[0] - cents[c][0]) ** 2 + (p[1] - cents[c][1]) ** 2)
            buckets[j].append(p)
        for c in range(k):
            if buckets[c]:
                cents[c] = [sum(x) / len(buckets[c]) for x in zip(*buckets[c])]
    return cents


def _n_way_for(group, r_c):
    """Number of hover points needed to cover the group with r_c disks (estimate).

    A hover point covers ~pi*r_c^2. Use the group's bounding area / disk area,
    clamped to [3, len(group)]. Fewer-than-sensors waypoints is the CETSP gain.
    """
    xs = [p[0] for p in group]
    ys = [p[1] for p in group]
    area = max(1.0, (max(xs) - min(xs))) * max(1.0, (max(ys) - min(ys)))
    est = math.ceil(area / (math.pi * r_c * r_c))
    return max(3, min(len(group), est + 1))


def optimize_trajectories(groups, r_c, V, iters=400, lr=8.0, lambda_cov=50.0,
                          device=None, seed=0):
    """Batched CETSP trajectory optimisation for all UAV sub-fields.

    groups : list of M sensor-coord lists (one per UAV).
    r_c    : collection radius [m].  V : cruise speed [m/s].
    Returns list of M optimised flight times t_fly_loop = tour_len / V [s].
    Per-UAV waypoint count is sized to the coverage need (CETSP); UAVs with fewer
    needed points pad by duplicating a centroid (zero-length segments).
    """
    device = device or get_device()
    M = len(groups)
    nways = [_n_way_for(g, r_c) for g in groups]
    n_way = max(nways)                                    # batch pad target
    max_s = max(len(g) for g in groups)

    sensors = torch.zeros(M, max_s, 2, device=device)
    smask = torch.zeros(M, max_s, device=device)
    wp0 = torch.zeros(M, n_way, 2, device=device)
    for u, g in enumerate(groups):
        for j, p in enumerate(g):
            sensors[u, j] = torch.tensor(p, device=device)
            smask[u, j] = 1.0
        cents = _kmeans_centroids(g, nways[u], rng_seed=seed * 131 + u)
        order = _angular_order(cents)
        cents = [cents[i] for i in order]
        # duplicate last centroid to pad up to n_way (zero-length segments)
        while len(cents) < n_way:
            cents.append(list(cents[-1]))
        for j, p in enumerate(cents):
            wp0[u, j] = torch.tensor(p, device=device)

    wp = wp0.clone().requires_grad_(True)
    opt = torch.optim.Adam([wp], lr=lr)

    for _ in range(iters):
        opt.zero_grad()
        # Closed tour length per UAV: sum of consecutive waypoint distances.
        nxt = torch.roll(wp, shifts=-1, dims=1)
        seg = torch.linalg.norm(nxt - wp, dim=2)          # [M, n_way]
        tour_len = seg.sum(dim=1)                          # [M]
        # Coverage: each sensor's distance to nearest waypoint must be <= r_c.
        # dist2 [M, max_s, n_way]
        diff = sensors.unsqueeze(2) - wp.unsqueeze(1)
        dist = torch.linalg.norm(diff, dim=3)              # [M, max_s, n_way]
        mind = dist.min(dim=2).values                      # [M, max_s]
        viol = torch.clamp(mind - r_c, min=0.0) ** 2
        cov_pen = (viol * smask).sum(dim=1)                # [M]
        loss = (tour_len + lambda_cov * cov_pen).sum()
        loss.backward()
        opt.step()

    with torch.no_grad():
        nxt = torch.roll(wp, shifts=-1, dims=1)
        tour_len = torch.linalg.norm(nxt - wp, dim=2).sum(dim=1)
        # Report coverage violation for honesty (should be ~0).
        diff = sensors.unsqueeze(2) - wp.unsqueeze(1)
        mind = torch.linalg.norm(diff, dim=3).min(dim=2).values
        max_viol = (torch.clamp(mind - r_c, min=0.0) * smask).max().item()
    t_fly = (tour_len / V).cpu().tolist()
    return t_fly, max_viol
