# RUN — RTX 4090 server (conda-only)

This phase (Prop. 1 validation) is **CPU-only**: pure-Python analytical M/M/c +
matplotlib. No GPU is used yet (the GPU/PyTorch solver arrives at the trajectory
phase). It runs in well under a minute.

## 1. One-time environment setup
```bash
conda env create -f environment.yml      # creates env "swarm-uav-aoi"
conda activate swarm-uav-aoi
```
If the env already exists and you want to refresh it:
```bash
conda env update -f environment.yml --prune
conda activate swarm-uav-aoi
```

## 2. Run the experiments (from the repo root)
```bash
# make-or-break gate (sanity: U-shape binds under optimal assignment)
python experiments/gate_ushape.py

# Prop. 1, semi-analytical  -> results/prop1_*.csv
python experiments/validate_prop1.py

# Prop. 1, PHYSICAL model (rotary-wing energy + air-to-ground comms, SI)
python experiments/validate_prop1_phys.py

# Prop. 2, placement inversion (coverage- vs traffic-optimal), ~1-3 min
python experiments/prop2_placement.py

# Joint solver vs baselines (GPU CETSP trajectory) + crossover + ablation.
# This is the GPU workload: the CETSP optimiser uses the RTX 4090 automatically.
python experiments/joint_solver.py

# render all figures from the CSVs -> results/*.png
python experiments/make_figures.py
```

Verify the GPU is actually used:
```bash
python -c "import torch; print('CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
```

## 3. Push results back
```bash
git add results/
git commit -m "results: Prop.1 validation from RTX 4090"
git push
```

## Expected output (reference, from local run)
- `gate_ushape.py` prints `VERDICT: GREEN`.
- `validate_prop1.py` prints the provisioning table; M* should be
  **non-decreasing in capacity** (local: c=[1,2,3,4,6,8,12] -> M*=[2,4,5,7,11,15,20]).
- `results/`:
  - `gate_ushape.csv`
  - `prop1_curves.csv`, `prop1_mstar.csv`
  - `fig_prop1_curves.png` (family of U-shaped AoI(M), one per capacity)
  - `fig_prop1_mstar.png` (M* vs capacity)

If your server numbers differ materially from the reference, that is a signal —
tell me and I will investigate before we build on top of it.

## Notes
- Seeds are fixed (`range(30)`), so runs are deterministic and reproducible.
- Everything reads/writes only inside the repo; nothing needs network or GPU here.
