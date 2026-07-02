# swarm-uav-aoi-congestion

Congestion-Aware Joint Charging-Station **Placement**, **Capacity**, and **Swarm-UAV Trajectory** Design for **Age-Optimal** Data Collection.

Extends the single-UAV IEEE IoT-J 2024 work (Xplore 10506755) to a **swarm**, where charging stations become **multi-server (M/M/c) contended queues**. Load-bearing contributions:

1. Joint **placement + port-capacity + swarm trajectory + assignment** under an M/M/c charging queue (MINLP).
2. **Non-monotone AoI(M)** — a congestion threshold: past an optimal swarm size `M*`, adding UAVs *worsens* AoI (Prop. 1).
3. **Placement inversion**: coverage-optimal placement is provably AoI-suboptimal under contention; placement flips coverage-driven → traffic-driven (Prop. 2).

Target venue: IEEE TMC / IoT-J / TVT.

## Status
- **S2 formulation** complete — see [`formulation.md`](formulation.md).
- **S3 smoke test** (next) — `src/` implements the make-or-break gate (§6 of formulation): does the U-shape `AoI(M)` bind under *optimal* assignment in the capacity-limited regime? GREEN → build full paper; RED → reframe/abandon (reported honestly).

## Layout
```
formulation.md      # mathematical spec (system model, MINLP, method, structural props, go/no-go gate)
src/                # simulation + solvers (smoke first, full later)
experiments/        # runnable smoke/gate scripts, seeds fixed
results/            # CSV outputs from RTX 4090 runs
environment.yml     # conda env (4090 server is conda-only)
```

## Workflow
Build + smoke locally → push here → run on RTX 4090 (conda-only; use `environment.yml`) → push results back → figures + LaTeX.

## Honesty guards
Multi-seed (≥3, target 10), mean ± std, Wilcoxon vs runner-up. No single-seed wins. Congestion must bind under *optimal* assignment, not naive nearest-station. Code and paper numbers must match.
