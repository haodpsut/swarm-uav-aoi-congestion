# Formulation — Congestion-Aware Joint Charging-Station Placement, Capacity, and Swarm-UAV Trajectory Design for Age-Optimal Data Collection

Status: S2 (transaction-grade formulation). This document is the mathematical spec; LaTeX comes after the smoke test decides go/no-go.

Base paper extended: *Joint Optimization of Charging Station Placement and UAV Trajectory for Fresh Data Collection*, IEEE IoT-J 2024 (Xplore 10506755) — **single UAV**, placement + trajectory, peak AoI, convex.

Nearest incumbent to beat/differentiate: Wei et al., *Minimizing AoI in UAV-Assisted Data Collection With Limited Charging Facilities*, IEEE WCL 13(5):1463-1467, 2024 (Xplore 10463610) — multi-UAV, **single-server** contended charging (c=1), **fixed** (no placement), DRL (DR-MADQN).

Our load-bearing novelty (both structural results are unpublished per the 2026-07-02 prior-art sweep):
1. Joint **placement + capacity (ports per station) + swarm trajectory + assignment** under an **M/M/c** queue.
2. **Non-monotone AoI(M)** — a congestion threshold / U-shape (Prop. 1).
3. **Placement inversion**: coverage-optimal placement is provably AoI-suboptimal under contention (Prop. 2).

---

## 1. System model

### 1.1 Sensors
- Set `K = {1,...,K}`, sensor `k` at `w_k ∈ R^2` on the ground.
- Each sensor generates status updates; freshness is measured by Age of Information (AoI).
- **AoI:** `A_k(t) = t − u_k(t)`, where `u_k(t)` is the generation time of the freshest update from `k` that has been delivered by time `t`. On a successful collection at time `τ` of a packet generated at `g`, `u_k` jumps to `g` and `A_k(τ⁺) = τ − g`.
- **Objective metric:** network **peak AoI** `Ā = max_k limsup_{t→∞} A_k(t)` (matches base paper). Time-average AoI kept as a secondary objective for ablation.

### 1.2 Swarm of UAVs
- `M = {1,...,M}` UAVs at fixed altitude `H`, horizontal position `q_m(t) ∈ R^2`.
- Discrete slots `t = 1,...,T`, slot length `δ_t`. Kinematics: `||q_m(t+1) − q_m(t)|| ≤ V_max δ_t`.
- State of charge `e_m(t) ∈ [0, E_max]`.
- **Collection:** UAV collects from sensor `k` when `||q_m(t) − w_k|| ≤ r_c` (disk model; a rate/SNR model is the transaction-grade upgrade in §6).

### 1.3 Candidate charging sites (the new decision axis)
- Candidate set `S = {1,...,S}` at `b_s ∈ R^2`.
- `x_s ∈ {0,1}`: build a station at `s`.
- `c_s ∈ {0,1,...,C_port}`: number of **parallel charging ports** (servers) at `s`; `c_s ≤ C_port · x_s`.
- Budgets: `Σ_s x_s ≤ S_max` (stations), `Σ_s c_s ≤ C_tot` (total ports / power budget).

### 1.4 Energy model (rotary-wing, Zeng 2019)
Propulsion power at speed `V`:
```
P(V) = P0 (1 + 3V^2 / U_tip^2)
     + Pi ( sqrt(1 + V^4/(4 v0^4)) − V^2/(2 v0^2) )^{1/2}
     + (1/2) d0 rho s A V^3
```
- Energy drain per slot: `e_m(t+1) = e_m(t) − P(V_m(t)) δ_t` while flying/collecting; `+ (charge)` while docked.
- **Recharge feasibility:** for every slot, the UAV must retain enough charge to reach its assigned open station: `e_m(t) ≥ E_reach(q_m(t), b_{a_m})`.

---

## 2. Charging as a FINITE-SOURCE (machine-repair) queue

> MODEL CORRECTION (DES-validated, 2026-07-02). An earlier draft used an open
> M/M/c (Erlang-C) queue. A discrete-event simulation of the actual cycling UAVs
> (`experiments/des_validation.py`) showed the open M/M/c **over-predicts the wait
> by ~6x**, because the system is CLOSED: only M UAVs exist, so the arrival rate
> falls as more of them are already at the station. The correct model is the
> **finite-source / machine-repair queue M/M/c//N**, which tracks the DES far
> better and is a **conservative upper bound** on the true (near-deterministic)
> wait. All results use it.

A station `s` serving the `N_s` UAVs assigned to it with `c_s` ports is a
finite-source queue:

- Each assigned UAV, while patrolling, needs to charge after an operating time of
  mean `tau_fly` (rate `lam = 1/tau_fly`); ports serve at `mu = 1/tau_charge`.
- Birth-death chain, state `n` = UAVs at the station (`0..N_s`):
  ```
  up-rate   n -> n+1 : (N_s - n) * lam      (arrivals VANISH as n -> N_s; closed)
  down-rate n -> n-1 : min(n, c_s) * mu
  p_n = p_0 * prod_{k=0}^{n-1} (N_s - k) lam / (min(k+1, c_s) mu),  sum_n p_n = 1
  ```
- Mean queue length `Lq = sum_n max(0, n - c_s) p_n`; throughput
  `lam_eff = sum_n (N_s - n) lam p_n`; **mean wait `W_q = Lq / lam_eff`** (Little).
- No stability constraint is needed: a finite population cannot blow the queue up
  (this replaces the old `rho_s < 1` constraint C3).

### 2.1 Revisit period and peak AoI
```
peak AoI_m = t_loop_m                          (one revisit period: patrol + collect)
           + 2 * dist(m, station)/V            (round trip to charge)
           + W_q(N_s, c_s, tau_fly, tau_charge) (FINITE-SOURCE wait: couples the swarm)
           + tau_charge
```
The closed-loop coupling (more UAVs on a station gives longer wait, with a ceiling
set by the finite population) is the mechanism behind Prop. 1: AoI(M) =
coverage(~1/M) + wait(M) + const still has an interior minimiser (U-shape).

---

## 3. Optimization problem (MINLP)

```
min_{ x, c, {q_m(·)}, {a_m} }   Ā = max_k  limsup_t A_k(t)

s.t.
(C1) AoI recursion:  A_k(t) driven by collection events along {q_m}; peak coupling.
(C2) energy:         e_m(t) ∈ [0, E_max];  e_m(t) ≥ E_reach(q_m(t), b_{a_m})  ∀ m,t.
(C3) stability:      rho_s = lambda_s / (c_s mu) < 1     ∀ s with x_s = 1.
(C4) arrival FP:     lambda_s = Σ_{m: a_m=s} 1/T_cycle_m ;  T_cycle_m = (§2.1).
(C5) budgets:        Σ_s x_s ≤ S_max ;  Σ_s c_s ≤ C_tot ;  c_s ≤ C_port x_s ;  x_s ∈ {0,1}, c_s ∈ Z≥0.
(C6) kinematics:     ||q_m(t+1) − q_m(t)|| ≤ V_max δ_t.
(C7) assignment:     a_m ∈ { s : x_s = 1 }.
(C8) separation:     ||q_m(t) − q_{m'}(t)|| ≥ d_min   ∀ m≠m', t.
```
Binary `x`, integer `c`, continuous trajectories, combinatorial assignment, **nonconvex Erlang-C** and a **fixed-point constraint** → a genuinely hard MINLP. This is the "hardened formulation" the transaction-grade house style requires (no perfect-CSI / static / instant-charge idealizations).

---

## 4. Solution method (SCA + queueing decomposition — deliberately NOT another MARL)

Block-coordinate descent with an inner fixed-point solve. Chosen over MARL because (a) the space is crowded with DRL/MARL and (b) it separates us from Wei's DR-MADQN.

- **Init:** feasible placement `(x,c)` (e.g., k-means of sensors + uniform ports), nearest-station assignment.
- **Repeat until convergence:**
  1. **Trajectory block** — fix `(x,c,a)`; optimize `{q_m}` for peak AoI via **SCA** (successive convex approximation of the AoI/visit constraints, as in the base paper) + collision.
  2. **Queue fixed point** — given trajectories + assignment, solve `(lambda, T_cycle)` self-consistently (Banach iteration; monotone so it converges when a stabilizing `(x,c)` exists).
  3. **Capacity block** — fix `lambda_s`; allocate ports `c_s` under `Σ c_s ≤ C_tot`. `W_q` is convex-decreasing in `c_s` (continuous relaxation of Erlang-C), so this is a convex separable allocation → water-filling on ports; round to integers.
  4. **Assignment block** — reassign UAVs to open stations to minimize `max_s rho_s` (load balancing) → LP / Hungarian.
  5. **Placement (outer)** — combinatorial search over `x` (greedy add/swap or SDP/LP relaxation of the facility-location core).
- **Baselines to beat:** (i) base-paper single-UAV placement replicated then swarm bolted on with nearest-station charging; (ii) Wei-style single-server / no-placement; (iii) coverage-optimal (k-means) placement; (iv) round-robin charging; (v) a tuned metaheuristic (GA/PSO) for the joint vector. Multi-seed (≥3, target 10), mean ± std, Wilcoxon vs runner-up.

---

## 5. Structural results (the headline — must be verified, not asserted)

### Proposition 1 (Non-monotone AoI in swarm size; congestion threshold).
Homogeneous setting, total charging capacity `K_cap = Σ_s c_s mu` fixed, `M` UAVs sharing the field and charging load.
- **Coverage benefit:** with more collectors the revisit time to each sensor shrinks, so the AoI floor behaves like `Θ(1/M)`.
- **Congestion penalty:** aggregate charge arrival `lambda_tot ≈ M / T_cycle` rises with `M`; as `lambda_tot → K_cap`, Erlang-C gives `W_q → ∞`, hence `T_cycle → ∞` and `A_k → ∞`.
- **Claim:** `AoI(M) ≈ α/M + β·W_q(M)` with `W_q` convex and diverging as `rho→1`; thus `AoI(M)` is quasiconvex with an **interior minimizer `M*`**. For `M < M*` adding UAVs helps; for `M > M*` adding UAVs **worsens** AoI.
- **Sketch:** `dAoI/dM < 0` for small `M` (coverage term dominates, `W_q ≈ 0` when `rho ≪ 1`); `dAoI/dM → +∞` as `lambda_tot → K_cap`. Continuity ⇒ interior minimizer. `M* = f(K_cap)`; provisioning rule: to serve `M` UAVs at utilization `rho_target`, need `Σ_s c_s mu > lambda_tot(M) / rho_target`.

### Proposition 2 (Placement inversion under contention).
- **Single-UAV (base):** optimal placement minimizes recharge **detour** → coverage/distance-driven; tends to concentrate a station near the trajectory centroid.
- **Swarm:** if all UAVs route to the single closest (coverage-optimal) station, `lambda` concentrates, `rho → 1`, `W_q` explodes. The AoI-optimal placement must **spread** stations to balance load (`min max_s rho_s`), even at the cost of longer detours.
- **Claim + construction:** there exist instances (e.g., 2 candidate sites) where the coverage-optimal placement (1 central site, min detour) is AoI-suboptimal for `M` UAVs, while an AoI-optimal placement (2 spread sites splitting `lambda`) yields lower `W_q` and lower peak AoI despite added detour. Hence the single-UAV placement is **provably suboptimal** for the swarm, and placement flips from **coverage-driven to traffic-driven**.

---

## 6. Make-or-break gate (defined precisely — this decides go/no-go)

**Risk (the QCGA/QIPSO failure mode):** Prop. 1's U-shape could vanish if optimal assignment perfectly load-balances and there is spare aggregate capacity — i.e., congestion is *assignment-limited* (bad routing) rather than *capacity-limited* (fundamental). If smart scheduling always dissolves congestion, the story collapses.

**Gate test (smoke, local, no GPU):** in the **capacity-limited regime** (`Σ_s c_s mu` is the binding bottleneck; `rho_target` stays near 1 even under optimal assignment), verify:
- **(a)** `AoI(M)` is empirically **U-shaped under OPTIMAL assignment** (LP/Hungarian balancing `lambda_s` across ALL open stations), not merely under naive nearest-station routing.
- **(b)** The minimizer `M*` and the divergence are **robust across ≥3 seeds** and multiple field/capacity configs (per the empirical-verification playbook — no single-seed wins).
- **(c)** Prop. 2 instance reproduces: coverage-optimal placement is beaten by load-balanced placement in the capacity-limited regime.

**Decision:** GREEN (build full paper) iff the U-shape **binds under optimal assignment** in an honest capacity-limited regime AND Prop. 2 reproduces. If under optimal assignment AoI is monotone until trivial capacity saturation, or the effect is single-seed noise → **RED**: reframe (e.g., pure capacity-provisioning study) or abandon and report honestly.

---

## 7. Main comparison (finite-source queue, DES-validated)

With the CORRECT finite-source queue, the distributed contention-aware placement
beats the single pooled station at ALL tested field sizes, and the gain grows
with field size (travel-driven). Measured (M=12, C_tot=4, 20 seeds):

| Field L | proposed vs single pooled station |
|---------|-----------------------------------|
| 5 km    | +4.2%                             |
| 8 km    | +7.9%                             |
| 14 km   | +11.3%                            |
| 20 km   | +12.6%                            |

Note: an earlier M/M/c draft showed a spurious "crossover" (single-pooled winning
in small fields). That was an artifact of the over-pessimistic open queue; the
finite-source model (which does not over-penalise split stations) removes it. The
finite-source wait saturates rather than diverging, so distributed placement's
travel saving is not swamped by a phantom queue penalty. Ablation at L=15 km:
proposed 41.4 min vs no_cetsp 42.8 (CETSP helps +3.1%), coverage 50.8
(contention-awareness helps far more), single pooled 46.8; Wilcoxon p=1.3e-4.

The finite-source model is DES-validated (`experiments/des_validation.py`): with
exponential operating+service it matches the discrete-event simulation to ~4%
(formula correct), and it is a conservative upper bound on the real
near-deterministic system (real waits ~4.5x lower). The open M/M/c over-predicts
the wait ~6x, which is what produced the phantom crossover. The **operating time
between charges must include the round-trip travel to the station** (up_time =
tau_fly + 2*dist/V); omitting travel over-predicts wait ~2x.

## 8. Roadmap
- [x] S1 brainstorm + prior-art sweep (queue-coupling gap OCCUPIED → pivot to placement+capacity+structural results).
- [x] S2 formulation (this file).
- [x] S3 smoke + validation: §6 gate GREEN; Prop.1 (semi + physical) U-shape + provisioning law; Prop.2 placement inversion; joint solver + CETSP trajectory + baselines + crossover.
- [x] S4 push to git (haodpsut/swarm-uav-aoi-congestion); GPU CETSP runs on RTX 4090.
- [ ] S6 scale runs on 4090; TikZ figures (U-shape AoI(M), provisioning law, crossover, placement map).
- [ ] S7 write (target IEEE TMC / IoT-J / TVT), honest crossover framing.
