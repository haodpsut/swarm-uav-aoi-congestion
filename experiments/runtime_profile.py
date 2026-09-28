"""R6-4 va R6-7e: bao SIEU THAM SO va THOI GIAN CHAY, tach khoi GPU voi khoi CPU.

Phan bien 6 vong 2 viet:
    "Optimization hyperparameters (Adam learning rate, iteration count, 2-opt frequency,
     termination criteria) and runtime are still not reported; they should be added, at
     least by reference to the artifact."
va vong 1 diem 7(e) doi them: so lan khoi dong lai / so hat giong, va PHAN CUNG.

CACH DO. Mot lan giai gom dung HAI khoi, va chung chay tren HAI thiet bi khac nhau:
  (1) khoi QUY DAO  : optimize_trajectories(), Adam + 2-opt, chay tren GPU
  (2) khoi TO HOP   : strategy_traffic(), duyet to hop vi tri x chia cong x gan lai, CPU
Bao rieng tung khoi moi tra loi duoc cau hoi that cua phan bien, vi mot con so gop lai
khong cho biet GPU dang lam bao nhieu phan viec.

⛔ BA CAI BAY, ca ba deu lam con so VO NGHIA neu bo qua:
  (a) Lan goi CUDA DAU TIEN gom ca khoi tao context, thuong 1-3 giay. Phai CHAY AM mot
      lan roi vut di, khong tinh vao so bao cao.
  (b) Kernel GPU chay BAT DONG BO. Khong goi torch.cuda.synchronize() truoc va sau thi
      dong ho dung lai truoc khi GPU lam xong, va ta se bao mot con so nho gia tao.
  (c) Sieu tham so KHONG duoc go tay vao day. Doc bang inspect tu chinh chu ky ham, de
      neu ai doi mac dinh trong src/ thi bang trong bai doi theo, khong phan ky am tham.
      Day la lop loi 'bang go tay khong cap nhat' trong so nha.

TU KIEM (doi chung duong): tong thoi gian hai khoi phai xap xi thoi gian do doc lap cua
ca lan giai. Lech qua 15% nghia la CON MOT KHOI CHUA DUOC DO, va script bao HONG.
"""
import csv
import inspect
import os
import platform
import statistics as st
import sys
import time

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import torch                                                       # noqa: E402
from scenario import DEFAULTS, tau_charge_of                       # noqa: E402
from energy import propulsion_power                                # noqa: E402
from trajectory import optimize_trajectories, get_device           # noqa: E402
from solver import (uav_states, candidate_sites, strategy_traffic,  # noqa: E402
                    _port_splits)
from field import partition_field                                  # noqa: E402

SEEDS = list(range(20))
loi = []


def kiem(dk, ten, ct=""):
    if not dk:
        loi.append(ten)
    print("  %s %s%s" % ("DAT " if dk else "HONG", ten, ("  [" + ct + "]") if ct else ""))


def dong_bo():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def dong_ho():
    dong_bo()
    return time.perf_counter()


def sieu_tham_so():
    """Doc thang tu chu ky ham, KHONG go tay. Xem bay (c) o dau tep."""
    p = inspect.signature(optimize_trajectories).parameters
    d = {k: v.default for k, v in p.items() if v.default is not inspect.Parameter.empty}
    d["adam_steps_tong"] = d["iters"] + d["reorder_rounds"] * max(1, d["iters"] // 3)
    return d


def moi_truong():
    dev = get_device()
    ten_gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "khong co"
    return dict(thiet_bi=str(dev), gpu=ten_gpu, torch=torch.__version__,
                cuda=torch.version.cuda or "khong", python=platform.python_version(),
                may=platform.node(), nhan_cpu=os.cpu_count())


def main():
    sc = dict(DEFAULTS)
    sc["reachability"] = True
    mu = 1.0 / tau_charge_of(sc["E_max"], sc["charge_power"])
    tau = tau_charge_of(sc["E_max"], sc["charge_power"])
    cands = candidate_sites(sc["L"], n=3)
    V, S_max, C_tot = sc["V"], 2, 4
    reach = sc["E_reserve"] * sc["E_max"] / propulsion_power(V)

    mt = moi_truong()
    hp = sieu_tham_so()
    print("== MOI TRUONG ==")
    for k, v in mt.items():
        print("   %-10s %s" % (k, v))
    print("\n== SIEU THAM SO (doc tu chu ky optimize_trajectories, khong go tay) ==")
    for k in ("lr", "iters", "reorder_rounds", "lambda_cov", "adam_steps_tong"):
        print("   %-18s %s" % (k, hp[k]))
    print("   %-18s %d (seed co dinh 0..%d, mot lan chay moi seed, khong restart ngau nhien)"
          % ("so hat giong", len(SEEDS), len(SEEDS) - 1))
    print("   %-18s so buoc CO DINH, khong co nguong dung som" % "tieu chi dung")
    print("   %-18s C(%d,%d) = %d to hop vi tri x %d cach chia cong"
          % ("khong gian duyet", len(cands), S_max,
             len(list(__import__("itertools").combinations(range(len(cands)), S_max))),
             len(list(_port_splits(C_tot, S_max)))))

    # --- (a) chay AM de nuot chi phi khoi tao CUDA context ---
    print("\n== chay AM mot lan de nuot khoi tao CUDA context ==")
    t0 = time.perf_counter()
    _ = uav_states(sc, 4, 999)
    dong_bo()
    print("   lan am: %.2f s (KHONG tinh vao bao cao)" % (time.perf_counter() - t0))

    rows = []
    for M in (12, 60):
        print("\n== M = %d ==" % M)
        print("%5s | %10s %10s %10s | %s" % ("seed", "quy dao", "to hop", "tong", "GPU chiem"))
        print("-" * 60)
        for sd in SEEDS:
            # khoi 1: quy dao tren GPU. Do rieng partition de khong tinh nham vao GPU.
            t = dong_ho()
            groups = partition_field(sc["K"], sc["L"], M, sd,
                                     clustered=sc.get("clustered", False))[1]
            t_part = dong_ho() - t

            t = dong_ho()
            optimize_trajectories(groups, 200.0, V, seed=sd)
            t_traj = dong_ho() - t

            # khoi 2: to hop tren CPU. Dung states da dung san de khong do lai khoi 1.
            states = uav_states(sc, M, sd)
            t = dong_ho()
            strategy_traffic(states, cands, S_max, C_tot, mu, tau, V, reach)
            t_comb = dong_ho() - t

            # doi chung: do CA LAN GIAI doc lap, phai xap xi tong hai khoi
            t = dong_ho()
            s2 = uav_states(sc, M, sd)
            strategy_traffic(s2, cands, S_max, C_tot, mu, tau, V, reach)
            t_e2e = dong_ho() - t

            rows.append(dict(M=M, seed=sd, t_partition=t_part, t_trajectory_gpu=t_traj,
                             t_combinatorial_cpu=t_comb, t_end_to_end=t_e2e))
            tong = t_part + t_traj + t_comb
            print("%5d | %10.3f %10.3f %10.3f | %8.1f%%"
                  % (sd, t_traj, t_comb, tong, 100.0 * t_traj / tong))

        sub = [r for r in rows if r["M"] == M]
        for k, nhan in (("t_trajectory_gpu", "quy dao (GPU)"),
                        ("t_combinatorial_cpu", "to hop (CPU)"),
                        ("t_end_to_end", "ca lan giai")):
            v = [r[k] for r in sub]
            print("   %-16s trung binh %7.3f s  do lech chuan %6.3f  min %6.3f  max %6.3f"
                  % (nhan, st.mean(v), st.pstdev(v), min(v), max(v)))

        # tu kiem: tong hai khoi phai xap xi lan giai doc lap
        tong_khoi = st.mean([r["t_partition"] + r["t_trajectory_gpu"] + r["t_combinatorial_cpu"]
                             for r in sub])
        e2e = st.mean([r["t_end_to_end"] for r in sub])
        lech = abs(tong_khoi - e2e) / max(tong_khoi, e2e)
        kiem(lech < 0.15, "M=%d: tong hai khoi khop lan giai doc lap" % M,
             "%.3f s so %.3f s, lech %.1f%%" % (tong_khoi, e2e, 100 * lech))

    kiem(torch.cuda.is_available(), "chay tren GPU that, khong roi ve CPU", mt["gpu"])
    kiem(all(r["t_trajectory_gpu"] > 0 for r in rows), "moi phep do deu duong")

    p = os.path.join(HERE, "..", "results", "runtime_profile.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    # ban khai moi truong di kem, vi mot con so thoi gian khong co may thi vo nghia
    q = os.path.join(HERE, "..", "results", "runtime_env.csv")
    with open(q, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["truong", "gia_tri"])
        for k, v in list(mt.items()) + [(k, hp[k]) for k in
                                        ("lr", "iters", "reorder_rounds", "lambda_cov",
                                         "adam_steps_tong")]:
            w.writerow([k, v])

    print("\n=> %s (%d loi). Da ghi results/runtime_profile.csv va results/runtime_env.csv"
          % ("DAT" if not loi else "CHUA DAT", len(loi)))
    for x in loi:
        print("   loi: " + x)
    return 0 if not loi else 1


if __name__ == "__main__":
    sys.exit(main())
