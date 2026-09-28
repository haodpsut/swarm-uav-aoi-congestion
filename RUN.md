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
# DES validation of the QUEUE MODEL (critical): shows the open M/M/c over-
# predicts wait ~6x, and the finite-source (machine-repair) model matches DES.
python experiments/des_validation.py

# Prop. 1, PHYSICAL model (finite-source queue + rotary-wing energy + comms)
python experiments/validate_prop1_phys.py

# (legacy, open-queue illustration only -- superseded by the two above)
# python experiments/gate_ushape.py
# python experiments/validate_prop1.py

# Prop. 2, placement inversion (coverage- vs traffic-optimal), ~1-3 min
python experiments/prop2_placement.py

# Joint solver vs baselines (GPU CETSP trajectory) + crossover + ablation.
# This is the GPU workload: the CETSP optimiser uses the RTX 4090 automatically.
python experiments/joint_solver.py

# Optimality gap: greedy solver vs exact optimum on small instances (CPU).
python experiments/optimality_gap.py

# Sensitivity/robustness: r_c, tau_charge, uniform vs clustered field (GPU CETSP).
python experiments/sensitivity.py

# render all figures from the CSVs -> results/*.pdf and *.png
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

## Vong sua R2 (28/09/2026): tam script do moi

Moi phep do duoi day tra loi mot nhan xet cu the cua phan bien, va moi script deu co
phan TU KIEM in ra cuoi (gom doi chung duong, va doi chung am o cho co the).

| script | tra loi diem nao | dau ra |
|---|---|---|
| `runtime_profile.py` | R6-4, R6-7(e): thoi gian chay va sieu tham so | `runtime_profile.csv`, `runtime_env.csv` |
| `stats_family.py` | R6-7(d): ho so sanh, hieu chinh Holm, hat giong xau nhat | `stats_family.csv` |
| `port_scarce.py` | R3-2: khan hiem cong o quy mo lon | `port_scarce.csv` |
| `per_method_mstar.py` | R2-3: moi phuong phap tu chon co doi | `per_method_mstar*.csv` |
| `separation_check.py` | R1-3, R6-5, R3 vong 2: rang buoc gian cach (12i) | `separation_check.csv` |
| `constraint_audit.py` | R5-3: muc vi pham lon nhat cua tung rang buoc | `constraint_audit.csv` |
| `common_des.py` | R5-7: MOT DES chung cham thiet ke cuoi cua moi phuong phap | `common_des*.csv` |
| `reach_envelope.py` | R5-3, R4-4: bao van hanh cua rang buoc kha dat tram | `reach_envelope.csv` |

Chay tat ca (sau `run_all_r1.py`):

```bash
for s in runtime_profile stats_family port_scarce per_method_mstar \
         separation_check constraint_audit common_des reach_envelope; do
  python experiments/$s.py || echo "HONG: $s"
done
python experiments/emit_r1_macros.py     # sinh r1_macros.tex + 3 bang
python experiments/make_figures.py       # ve lai 9 hinh o be rong MOT COT
```

⛔ **Moi con so trong bai den tu MOT may.** Cac ket qua trong kho nay duoc chay tren mot
node co RTX 4090, torch 2.6.0+cu124. Chay lai tren may khac se lech o chu so co nghia
thu ba o nhung script di qua bo toi uu quy dao GPU; do la ly do `R1_MANIFEST.md` ghi bam
theo tung tep.
