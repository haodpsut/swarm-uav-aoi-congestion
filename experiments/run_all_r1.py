"""Chay LAI toan bo phep do cua vong sua R1, mot lenh, va ghi ban khai.

    python experiments/run_all_r1.py

Moi script deu tat dinh (seed co dinh trong tung tep), nen chay hai lan phai cho ket qua
GIONG HET. Script nay chay tung cai, bam ma bam SHA-256 cua tung CSV sinh ra, va ghi
results/R1_MANIFEST.md.

⛔ VI SAO CAN BAN KHAI. Phan bien doi bai co the tai tao. "Chay duoc" chua du: phai
chung minh chay lai cho DUNG con so cu. Ban khai in bam cua tung tep ket qua, nen bat ky
ai cung doi chieu duoc, va neu mot lan chay sau cho bam khac thi biet ngay.
"""
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")

JOBS = [
    ("prop2_placement.py",   "prop2_placement.csv",
     "Diem 6: dao nguoc dat tram, tach theo CO/KHONG khac phan bo cong"),
    ("prop2_ranking_md.py",  "prop2_ranking_md.csv",
     "Diem 5: thu hang dat tram duoi M/M so voi M/D (dich vu tat dinh)"),
    ("joint_reopt_check.py", "joint_reopt_check.csv",
     "Diem 3: gia cua viec co dinh sub-field truoc khi dat tram"),
    ("aoi_metric_gap.py",    "aoi_metric_gap.csv",
     "Diem 1: cho TRUNG BINH so voi cac phan vi cao, tu DES"),
    ("reach_margin.py",      "reach_margin.csv",
     "Diem 4: bien kha dat tram cua cau hinh cuoi"),
    ("prop1_uniqueness.py",  "prop1_uniqueness.csv",
     "Diem 2: M* co duy nhat khong, va gia thiet loi roi rac co bi du lieu bac khong"),
    ("single_uav_baseline.py", "single_uav_baseline.csv",
     "Doc ngoai: duong co so MOT UAV, bai hua o phan dong gop ma khong he bao cao"),
    ("ablation_effect.py",   "ablation_effect.csv",
     "Doc ngoai: hieu ung + CI bootstrap, thay cho mot p-value dang nam o SAN"),
    ("paoi_vs_timeavg.py",   "paoi_vs_timeavg.csv",
     "Doc ngoai: DINH moi chu ky so voi TRUNG BINH THEO THOI GIAN cua cung chu ky"),
    ("des_validation.py",    "des_summary.csv",
     "nen: mo hinh hang doi so voi DES (da co tu ban dau)"),
    ("ablation_9km_3tram.py", "ablation_9km_3st.csv",
     "Doc ngoai vong 1: so sanh chinh o 9 km / 3 tram, che do THAT SU bay duoc"),
    ("chan_doan_hat_bi_loai.py", "chan_doan_9km_hat_bi_loai.txt",
     "Doc ngoai vong 2: 9 hat bi loai khac 11 hat kia o dau, va 5,8% co bi thien lech khong"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    print("=" * 78)
    print("  CHAY LAI TOAN BO PHEP DO VONG SUA R1")
    print("=" * 78)
    out, bad = [], 0
    for script, csvname, why in JOBS:
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, script)],
                           cwd=ROOT, capture_output=True, text=True)
        dt = time.time() - t0
        p = os.path.join(RES, csvname)
        ok = r.returncode == 0 and os.path.exists(p)
        bad += 0 if ok else 1
        digest = sha(p) if os.path.exists(p) else "-"
        print("  %-24s %6.1fs  %-18s %s"
              % (script, dt, digest, "ok" if ok else "⛔ LOI"))
        if not ok and r.stderr:
            print("      " + r.stderr.strip().splitlines()[-1][:100])
        # ⛔ CANH BAO KHI CHAY LAI LAM DOI SO DA CONG BO. Cac script dung bo toi uu
        # quy dao tren GPU khong tai tao duoc TUNG BIT giua cac may: chay lai
        # prop2_placement.py tren CPU cho trung binh 14,69% trong khi ban chay tren
        # RTX 4090 cho 14,77%, tuc doi chu so thu ba. Ghi de am tham thi ban thao va
        # HINH VE se lech nhau, vi hinh sinh tu ban cu. Bao to, va giu ban da cong bo.
        drift = ""
        try:
            import subprocess as _sp
            r0 = _sp.run(["git", "show", "HEAD:results/%s" % csvname],
                         cwd=ROOT, capture_output=True)
            if r0.returncode == 0 and os.path.exists(p):
                if r0.stdout != open(p, "rb").read():
                    drift = "  ⚠ KHAC ban da cong bo (may khac / phan cung khac)"
        except Exception:
            pass
        if drift:
            print("     %s" % drift.strip())
        out.append((script, csvname, why, digest, dt, ok))

    lines = ["# Ban khai tai tao — vong sua R1", "",
             "Sinh boi `experiments/run_all_r1.py`. Moi script tat dinh (seed co dinh),",
             "nen chay lai phai cho **cung bam SHA-256**.", "",
             # ⛔ KHONG dua THOI GIAN CHAY vao ban khai. No doi moi lan chay (3,5 so
             # 3,6 giay), nen chinh ban khai dung de chung minh tinh tat dinh lai
             # KHONG tat dinh. Da mac loi nay o lan dau. Thoi gian chi in ra man hinh.
             "| script | ket qua | bam SHA-256 (16) | tra loi diem nao |",
             "|---|---|---|---|"]
    for s, c, w, d, dt, ok in out:
        lines.append("| `%s` | `results/%s` | `%s` | %s |" % (s, c, d, w))
    lines += ["", "## Pham vi cua loi hua tai tao", "",
              "Bam SHA-256 o tren tai tao duoc **tren cung mot may**: hai lan chay lien tiep",
              "cho bam giong het. Chung **khong** tai tao duoc tung bit giua cac may khac nhau",
              "cho nhung script goi bo toi uu quy dao chay tren GPU: cung ma nguon, cung seed,",
              "ban chay tren RTX 4090 va ban chay tren CPU lech nhau o chu so co nghia thu ba",
              "(vi du trung binh 14,77% so voi 14,69%). Cac tep ket qua trong kho la ban da",
              "cong bo; script chay lai se BAO nếu no sinh ra noi dung khac.", "",
              "## Cach kiem", "",
              "```bash", "python experiments/run_all_r1.py",
              "```", "",
              "Doi chieu cot bam voi bang tren. Lech mot dong nao la co gi do da doi."]
    with open(os.path.join(RES, "R1_MANIFEST.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n  => %s | da ghi results/R1_MANIFEST.md"
          % ("TAT CA CHAY DUOC" if not bad else "⛔ %d script loi" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
