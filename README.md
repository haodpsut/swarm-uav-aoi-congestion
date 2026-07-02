# Congestion-Aware Joint Charging-Station Placement, Capacity, and Swarm-UAV Trajectory Design for Age-Optimal Data Collection

Reference implementation and paper for a study on keeping Internet of Things data
fresh with a swarm of energy-limited UAVs that recharge at a small number of
shared, multi-port charging stations.

**Author:** Phuc Hao Do (CAIRA, Da Nang Architecture University) · haodp.ai@gmail.com
**Repository:** https://github.com/haodpsut/swarm-uav-aoi-congestion

---

## Summary

A UAV swarm can keep sensor data fresh, but the UAVs must recharge, and with only
a few charging stations those stations become a **contended resource**: UAVs that
arrive together compete for a limited number of ports and wait, which inflates the
Age of Information (AoI). This work jointly designs **where to place stations**,
**how many ports each gets**, **how the swarm flies**, and **which UAV charges
where**, to minimize the network peak AoI.

Two ideas carry the paper:

1. **The charging system is a closed queue.** Because only `M` UAVs exist, the
   station is a **finite-source (machine-repair) queue `M/M/c//N`**, not an open
   `M/M/c`. A discrete-event simulation confirms the finite-source model within
   about 4%, while the open `M/M/c` overpredicts the wait by about 6x and would
   distort the design (it even produces a spurious placement crossover).
2. **Two structural results.**
   - *Congestion threshold:* peak AoI is **non-monotone in the swarm size** (a
     U-shape); beyond an optimal size `M*` extra UAVs only add charging
     congestion. `M*` grows with the charging capacity (a provisioning law).
   - *Placement inversion:* under contention the AoI-optimal placement is
     **traffic-driven** (it balances queue load), not coverage-driven
     (minimum detour). The coverage-optimal placement is provably suboptimal.

A block-coordinate solver with a **GPU close-enough-TSP trajectory optimizer**
realizes the gains, reducing peak AoI by up to 12.6% over a strong single-station
baseline (Wilcoxon `p < 1e-4`).

## Repository layout

```
paper/                 LaTeX source (IEEE IoT-J format)
  main.tex             entry point; sections/ and figs/ are \input
  sections/            intro, related, formulation, analysis, solver, experiments, conclusion
  figs/                TikZ flow figures (system model, solver)
  refs.bib             33 references
src/
  queue_model.py       finite-source (machine-repair) queue Wq; retired open M/M/c
  energy.py            rotary-wing propulsion power (Zeng 2019)
  comms.py             air-to-ground line-of-sight rate and collection dwell
  field.py             sensor field, k-means sub-fields, NN + 2-opt patrol
  scenario.py          physical per-UAV cycle (SI units)
  trajectory.py        GPU differentiable CETSP hover-tour optimizer (PyTorch)
  solver.py            block-coordinate joint solver + baselines
experiments/
  des_validation.py    validates the queue model against a discrete-event sim
  validate_prop1_phys.py   Proposition 1 (congestion threshold + provisioning)
  prop2_placement.py   Proposition 2 (placement inversion)
  joint_solver.py      joint solver vs baselines: crossover sweep + ablation
  make_figures.py      renders all result figures from the CSVs
results/               CSV outputs and figures from the RTX 4090 run
```

## Reproducing the results

The analysis is CPU-only except the CETSP trajectory optimizer, which uses the
GPU when available (and falls back to CPU otherwise). Environment is conda-only.

```bash
conda env create -f environment.yml
conda activate swarm-uav-aoi

python experiments/des_validation.py        # queue model vs DES (6x / 4%)
python experiments/validate_prop1_phys.py   # M* = [4,6,9,12,17,20,20]
python experiments/prop2_placement.py       # traffic beats coverage 20/20
python experiments/joint_solver.py          # crossover + ablation (GPU CETSP)
python experiments/make_figures.py          # figures -> results/*.png
```

Seeds are fixed, so runs are deterministic and reproduce the numbers in the
paper (up to floating-point last digits across platforms).

### GPU note

On the RTX 4090 server the NVIDIA driver supports up to CUDA 12.5, so install the
matching PyTorch build if the default wheel reports a driver mismatch:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## Building the paper

```bash
cd paper
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## License

Research code released for reproducibility. Please cite the paper if you use it.
