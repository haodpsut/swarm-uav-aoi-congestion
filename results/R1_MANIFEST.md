# Ban khai tai tao — vong sua R1

Sinh boi `experiments/run_all_r1.py`. Moi script tat dinh (seed co dinh),
nen chay lai phai cho **cung bam SHA-256**.

| script | ket qua | bam SHA-256 (16) | tra loi diem nao |
|---|---|---|---|
| `prop2_placement.py` | `results/prop2_placement.csv` | `f5f4f3ed5766a304` | Diem 6: dao nguoc dat tram, tach theo CO/KHONG khac phan bo cong |
| `prop2_ranking_md.py` | `results/prop2_ranking_md.csv` | `497d5c681d3e58dc` | Diem 5: thu hang dat tram duoi M/M so voi M/D (dich vu tat dinh) |
| `joint_reopt_check.py` | `results/joint_reopt_check.csv` | `1ea82d83ae673743` | Diem 3: gia cua viec co dinh sub-field truoc khi dat tram |
| `aoi_metric_gap.py` | `results/aoi_metric_gap.csv` | `7f170f9086f1edcd` | Diem 1: cho TRUNG BINH so voi cac phan vi cao, tu DES |
| `reach_margin.py` | `results/reach_margin.csv` | `c552f85959c92c3f` | Diem 4: bien kha dat tram cua cau hinh cuoi |
| `prop1_uniqueness.py` | `results/prop1_uniqueness.csv` | `a61faf058ea19373` | Diem 2: M* co duy nhat khong, va gia thiet loi roi rac co bi du lieu bac khong |
| `des_validation.py` | `results/des_summary.csv` | `1a8e8cba0b86974e` | nen: mo hinh hang doi so voi DES (da co tu ban dau) |

## Pham vi cua loi hua tai tao

Bam SHA-256 o tren tai tao duoc **tren cung mot may**: hai lan chay lien tiep
cho bam giong het. Chung **khong** tai tao duoc tung bit giua cac may khac nhau
cho nhung script goi bo toi uu quy dao chay tren GPU: cung ma nguon, cung seed,
ban chay tren RTX 4090 va ban chay tren CPU lech nhau o chu so co nghia thu ba
(vi du trung binh 14,77% so voi 14,69%). Cac tep ket qua trong kho la ban da
cong bo; script chay lai se BAO nếu no sinh ra noi dung khac.

## Cach kiem

```bash
python experiments/run_all_r1.py
```

Doi chieu cot bam voi bang tren. Lech mot dong nao la co gi do da doi.
