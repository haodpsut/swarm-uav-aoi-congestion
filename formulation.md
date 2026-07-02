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

## 2. Charging as an M/M/c queue (the load-bearing coupling)

A station `s` with `c_s` ports is a **c_s-server queue**. This is what only a *swarm* creates and what the base paper (single UAV) and Wei (c=1) do not have.

- **Arrivals:** UAVs routed to `s` arrive to recharge. Renewal approximation: each UAV returns to charge once per operating cycle, so the aggregate arrival rate is
  ```
  lambda_s = Σ_{m : a_m = s} 1 / T_cycle_m           (C-fixedpoint)
  ```
- **Service:** mean charge time `1/mu` per port (Exp for M/M/c closed form; deterministic charge time handled by M/D/c as a robustness check).
- **Offered load / utilization:** `a_s = lambda_s / mu`, `rho_s = a_s / c_s = lambda_s / (c_s mu)`.
- **Stability (hard constraint):** `rho_s < 1` for every open station.
- **Expected queue wait (Erlang-C):**
  ```
  W_q(lambda_s, c_s, mu) = C(c_s, a_s) / (c_s mu − lambda_s)

  C(c, a) = [ a^c / (c! (1 − a/c)) ]
            ------------------------------------------------
            [ Σ_{n=0}^{c−1} a^n/n!  +  a^c / (c! (1 − a/c)) ]      (Erlang-C prob. of wait)
  ```

### 2.1 Cycle time and the fixed point
```
T_cycle_m = T_collect_m                         (dwell over its sensor sub-field)
          + T_fly_m                             (fly to assigned station)
          + W_q(lambda_{a_m}, c_{a_m}, mu)      (QUEUE WAIT — couples the swarm)
          + T_charge_m                          (= (E_max − e_arrive)/charge_rate)
          + T_return_m                          (return to field)
```
Because `lambda_s` depends on `{T_cycle_m}` (C-fixedpoint) and `T_cycle_m` depends on `W_q(lambda_s,·)`, the pair `(lambda, T_cycle)` is a **self-consistent fixed point**. This feedback (`M ↑ → lambda ↑ → W_q ↑ → T_cycle ↑`) is the mechanism behind Prop. 1.

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

## 7. Roadmap
- [x] S1 brainstorm + prior-art sweep (queue-coupling gap OCCUPIED → pivot to placement+capacity+structural results).
- [ ] S2 formulation (this file) — refine energy/collection to rate model, tighten Prop. proofs.
- [ ] S3 smoke test (local) — implement §6 gate. `src/` analytical M/M/c + optimal assignment + placement baselines.
- [ ] S4 push to git (haodpsut/swarm-uav-aoi-congestion), run on RTX 4090.
- [ ] S6 pull results, TikZ figures (U-shape AoI(M), placement inversion map).
- [ ] S7 write (target IEEE TMC / IoT-J / TVT).
