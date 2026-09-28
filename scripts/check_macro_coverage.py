"""Cong MOT CHO O: so nao da co macro thi ban thao khong duoc go tay lai.

    python repo/scripts/check_macro_coverage.py \
        --macros results/tables/r1_macros.tex \
        --tex v2-revision/main.tex v2-revision/sections/*.tex

Kiem HAI thu, va ca hai deu la thu da that su cat trong vong sua nay:

  A. MOT BAN DUY NHAT. Tep macro chi duoc ton tai o DUNG MOT cho trong cay thu muc.
     ⛔ 26/08: co hai ban (repo/results/tables/ va v2-revision/results/tables/), ban thao
     nap nham ban cu, nen no im lang dung 24 macro trong khi ban moi da co 42. Khong loi,
     khong canh bao, ban in van ra 14 trang. Chi lo ra khi mot macro MOI chua ton tai o
     ban cu duoc dung toi.

  B. KHONG GO TAY. Gia tri nao da co macro thi khong duoc xuat hien nhu so tran trong
     .tex. ⛔ 26/08: §VI-D in "14.8% on average" trong khi trung binh that la 14.69%;
     chu thich Hinh 6 in "on every seed" trong khi co mot seed hoa dung bang.

⛔ PHAM VI CO Y HEP O PHAN B. Chi bat cac gia tri CO DAU THAP PHAN. Cac macro mang gia
tri nguyen nho (0, 1, 5, 7, 20) trung voi hang tram con so binh thuong trong van ban
(so muc, so cam bien, so UAV), va bat chung se cho ra mot dong bao dong gia. Mot cong
keu nham thi bi tat, va luc do no khong con bao ve gi nua. Xem
feedback-siet-cong-phai-do-bao-dong-gia. Cong nay IN RA so don vi da kiem de khong ai
nham "0 canh bao" voi "kiem 0 don vi".
"""
import argparse
import glob
import os
import re
import sys

# Ngu canh phai BOC RA truoc khi doc so: tham chieu muc, phuong trinh, hinh, bang,
# trich dan, nhan, va lenh dung so lam tham so trinh bay. Boc theo NGU CANH chu khong
# theo GIA TRI: luat theo gia tri tung nuot ca cac so headline cua chinh bai.
STRIP = [
    r"%.*",                                  # chu thich LaTeX
    r"\\(?:label|ref|eqref|cite|citep|includegraphics|input|include)\s*(?:\[[^\]]*\])?\{[^}]*\}",
    r"\\(?:newcommand|renewcommand|providecommand)\s*\{[^}]*\}",
    r"\\begin\{[^}]*\}(?:\[[^\]]*\])?",
    r"\\end\{[^}]*\}",
    r"(?:Section|Sec\.|Fig\.|Figure|Table|Tab\.|Eq\.|Equation|Algorithm|Alg\.)~?\s*\\?\w*\s*[IVX0-9]+(?:\.[0-9]+)*",
    r"\d+(?:\.\d+)?\s*(?:pt|em|ex|in|cm|mm|\\columnwidth|\\textwidth|\\linewidth)",
    r"\\[a-zA-Z]+\s*=\s*[-\d.]+",
]

NUM = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w])")


def load_macros(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def find_duplicate_homes(macro_path):
    """Tim moi ban sao cung ten TRONG CAY CUA BAI NAY, va cho biet chung co GIONG NHAU.

    ⛔ Hai loi cua ban truoc, ca hai deu do chinh cong nay gay ra:
      (a) no leo len 4 cap tu tep macro, nen o bo cuc `<bai>/v3-revision/results/tables/`
          thi root cham ca thu muc CHA chua cac bai KHAC, va no bao mot tep cua bai khac
          la "ban thu hai". Bao dong gia thi lam nguoi ta tat cong.
      (b) no dem SO BAN. Nhung dieu dang so khong phai co hai ban, ma la hai ban KHAC
          NHAU: quy trinh sinh o mot cho roi chep sang thu muc dung bai thi hai ban la
          binh thuong. Phep kiem dung cho muc dich da khai la SO NOI DUNG.
    Nay: root = thu muc BAI (co reviews/ hoac build-submit*.sh), va tra ve them bam.
    """
    import hashlib
    name = os.path.basename(macro_path)
    root = os.path.dirname(os.path.abspath(macro_path))
    for _ in range(6):
        cha = os.path.dirname(root)
        if cha == root:
            break
        if (os.path.isdir(os.path.join(root, "reviews"))
                or glob.glob(os.path.join(root, "build-submit*.sh"))):
            break
        root = cha
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", "__pycache__", "build",
                                    "submit", "pkg", ".latexmk")]
        if name in filenames:
            f = os.path.join(dirpath, name)
            h = hashlib.sha256(open(f, "rb").read()).hexdigest()[:12]
            hits.append((os.path.relpath(f, root), h))
    return root, sorted(hits)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--macros", required=True)
    ap.add_argument("--tex", nargs="+", required=True)
    a = ap.parse_args()

    if not os.path.exists(a.macros):
        print("  ⛔ khong co %s" % a.macros)
        return 1
    macros = load_macros(a.macros)
    if not macros:
        print("  ⛔ %s khong co macro nao -> cong nay se kiem 0 don vi" % a.macros)
        return 1

    bad = 0

    # ---- A. mot ban duy nhat ------------------------------------------------
    root, homes = find_duplicate_homes(a.macros)
    bams = {h for _, h in homes}
    if len(bams) > 1:
        print("  ⛔ %s co %d ban KHAC NHAU trong cay cua bai, ban thao co the nap nham:"
              % (os.path.basename(a.macros), len(bams)))
        for f, h in homes:
            print("       %s  %s" % (h, f))
        bad += 1
    elif len(homes) > 1:
        print("  %d ban, GIONG HET nhau (%s) ✅" % (len(homes), list(bams)[0]))
        for f, _ in homes:
            print("       %s" % f)
    else:
        print("  mot ban duy nhat: %s ✅" % (homes[0][0] if homes else a.macros))

    # ---- B. khong go tay ----------------------------------------------------
    # chi cac gia tri co dau thap phan; xem ghi chu pham vi o dau tep
    want = {v: k for k, v in macros.items() if "." in v}
    checked = flagged = 0
    for path in a.tex:
        if not os.path.exists(path) or os.path.samefile(path, a.macros):
            continue
        s = open(path, encoding="utf-8").read()
        for pat in STRIP:
            s = re.sub(pat, " ", s)
        for line_no, line in enumerate(s.splitlines(), 1):
            for lit in NUM.findall(line):
                checked += 1
                if lit in want:
                    flagged += 1
                    print("  ⛔ %s:%d  go tay %s -> phai dung \\%s"
                          % (os.path.relpath(path, root), line_no, lit, want[lit]))
    bad += flagged

    print("  da kiem %d so thap phan trong %d tep, doi chieu voi %d macro co phan thap phan"
          % (checked, len(a.tex), len(want)))
    print("  => %s" % ("FAIL" if bad else "PASS"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
