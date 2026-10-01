#!/usr/bin/env python3
"""ALeSc grids: w=31, p=0.90, k=1..4, m=19,21,23,25, symmetry 0 then 1.
   Usage: run_grid_ub43.py [upperBound] [N]
   Defaults: upperBound=39, N=100."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

root = Path("/Users/reinert/CC/ALeS")
outdir = root / "grid_results"
outdir.mkdir(exist_ok=True)
binpath = root / "ALeSc"
ks = [1, 2, 3, 4]
ms = [19, 21, 23, 25]
SPAN = int(sys.argv[1]) if len(sys.argv) > 1 else 39
WEIGHT = 31
P = "0.90"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
OMP_THREADS = os.environ.get("OMP_NUM_THREADS", "4")
TAG = "" if N == 100 else f"_n{N}"

seed_pat = re.compile(r"^\s*(?:\d+\|)?\s*([01]+)\s*$")


def last_seeds(text, want_k=None):
    lines = text.splitlines()
    last_designed = None
    last_plain = None
    i = 0
    while i < len(lines):
        tag = lines[i].strip()
        if tag in ("seeds:", "designed:", "reversed:"):
            j = i + 1
            block = []
            while j < len(lines):
                m = seed_pat.match(lines[j])
                if not m:
                    break
                block.append(m.group(1))
                j += 1
            if block:
                if tag == "designed:":
                    last_designed = block
                elif tag == "seeds:":
                    last_plain = block
            i = j
            continue
        i += 1
    block = last_designed or last_plain
    if want_k and block and len(block) > want_k:
        block = block[:want_k]
    return block


def parse_best(text):
    m = re.search(r"Best sensitivity is\s+([0-9.eE+-]+)", text)
    return float(m.group(1)) if m else None


def write_summary(path, rows, tag):
    with path.open("w") as f:
        for r in rows:
            extra = f" {tag}" if tag else ""
            f.write(
                f"k={r['k']} cl={r['cl']} ub={SPAN} N={N}{extra} best={r['best']} "
                f"nSeeds={len(r['seeds']) if r['seeds'] else 0} "
                f"time={r['time']:.1f}s rc={r['rc']}\n"
            )


def write_tex(path, rows, symmetry):
    by = {(r["k"], r["cl"]): r for r in rows}
    flag = 1 if symmetry else 0
    mode = "with reverse-doubled seed sets" if symmetry else "without reverse doubling"
    lab = "sym-sens" if symmetry else "sens"
    slab = "sym-shapes" if symmetry else "shapes"
    extra_cap = (
        " Search evaluates each designed set of $k$ seeds together with their reverses."
        if symmetry
        else ""
    )
    extra_hdr = (
        "% symmetry flag scores designed seeds plus reverses during search\n"
        if symmetry
        else ""
    )
    lines = [
        f"% Auto-generated from ./ALeSc {WEIGHT} k {P} {N} m {SPAN} {flag}\n",
        extra_hdr,
        "\\begin{table}[htbp]\n\\centering\n",
        f"\\caption{{Sensitivity of ALeSc {mode} ($w={WEIGHT}$, $p={P}$, $N={N}$, "
        f"length upper bound {SPAN}).{extra_cap} Columns are core length $m$; "
        f"rows are the number of designed seeds $k$.}}\n",
        f"\\label{{tab:alesc-{lab}-w31-ub{SPAN}{TAG}}}\n",
        "\\begin{tabular}{ccccc}\n\\hline\n",
        "$k\\setminus m$ & " + " & ".join(str(m) for m in ms) + " \\\\\n\\hline\n",
    ]
    for k in ks:
        vals = []
        for m in ms:
            r = by.get((k, m))
            vals.append(f"{r['best']:.4f}" if r and r["best"] is not None else "--")
        lines.append(f"{k} & " + " & ".join(vals) + " \\\\\n")
    lines += [
        "\\hline\n\\end{tabular}\n\\end{table}\n\n",
        "\\begin{table}[htbp]\n\\centering\n",
        f"\\caption{{Best ALeSc seed sets {mode} ($w={WEIGHT}$, $p={P}$, $N={N}$, "
        f"length upper bound {SPAN}).}}\n",
        f"\\label{{tab:alesc-{slab}-w31-ub{SPAN}{TAG}}}\n",
        "\\small\n\\begin{tabular}{ccp{0.72\\textwidth}}\n\\hline\n",
        "$k$ & $m$ & Seeds \\\\\n\\hline\n",
    ]
    for k in ks:
        for m in ms:
            r = by.get((k, m))
            seeds = r["seeds"] if r else None
            if not seeds:
                lines.append(f"{k} & {m} & -- \\\\\n\\hline\n")
                continue
            for i, s in enumerate(seeds):
                prefix = f"{k} & {m} & " if i == 0 else " &  & "
                lines.append(f"{prefix}\\texttt{{{s}}} \\\\\n")
            lines.append("\\hline\n")
    lines.append("\\end{tabular}\n\\end{table}\n")
    path.write_text("".join(lines))


def run_one(k, cl, symmetry, base_seeds=None):
    prefix = f"sym_ub{SPAN}{TAG}" if symmetry else f"nosym_ub{SPAN}{TAG}"
    log = outdir / f"{prefix}_k{k}_cl{cl}.log"
    cmd = [str(binpath), str(WEIGHT), str(k), P, str(N), str(cl), str(SPAN), "1" if symmetry else "0"]
    if base_seeds:
        cmd.extend(base_seeds[: k - 1])
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = OMP_THREADS
    t0 = time.time()
    extra = f" frozen={len(base_seeds[:k-1])}" if base_seeds else ""
    print(f"START {'sym' if symmetry else 'nosym'} k={k} cl={cl} N={N}{extra}", flush=True)
    proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    dt = time.time() - t0
    text = (proc.stdout or "") + (proc.stderr or "")
    log.write_text(text)
    best = parse_best(text)
    seeds = last_seeds(text, k)
    print(
        f"DONE {'sym' if symmetry else 'nosym'} k={k} cl={cl} "
        f"best={best} time={dt:.1f}s rc={proc.returncode}",
        flush=True,
    )
    return {
        "k": k,
        "cl": cl,
        "best": best,
        "seeds": seeds,
        "time": dt,
        "rc": proc.returncode,
    }


def run_grid(symmetry):
    rows = []
    tex = root / (
        f"alesc_tables_sym_{SPAN}{TAG}.tex" if symmetry else f"alesc_tables_{SPAN}{TAG}.tex"
    )
    summary = outdir / (
        f"summary_sym_{SPAN}{TAG}.txt" if symmetry else f"summary_{SPAN}{TAG}.txt"
    )
    label = "sym" if symmetry else "nosym"
    print(f"==== GRID {label} ub={SPAN} N={N} ====", flush=True)
    prev_by_cl = {}
    for k in ks:
        for cl in ms:
            base = None
            if k > 1:
                prev = prev_by_cl.get(cl)
                if prev and len(prev) >= k - 1:
                    base = prev[: k - 1]
            r = run_one(k, cl, symmetry, base)
            rows.append(r)
            if r["seeds"]:
                prev_by_cl[cl] = r["seeds"][:k]
            write_summary(summary, rows, "" if symmetry else "nosym")
            write_tex(tex, rows, symmetry)
    print(f"==== DONE GRID {label} ====", flush=True)
    return rows


def parse_prev_summary(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = re.search(r"k=(\d+) cl=(\d+).*best=([0-9.eE+-]+).*time=([0-9.]+)s", line)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = (float(m.group(3)), float(m.group(4)))
    return out


def compare_grid(label, prev_path, rows):
    prev = parse_prev_summary(prev_path)
    print(f"\n==== COMPARE {label} vs previous ub={SPAN} N={N} ====", flush=True)
    print(f"{'k':>2} {'m':>3} {'prev':>10} {'new':>10} {'delta':>10} {'prev_s':>8} {'new_s':>8}", flush=True)
    n_up = n_eq = n_dn = 0
    for r in rows:
        key = (r["k"], r["cl"])
        new = r["best"]
        old, ot = prev.get(key, (None, None))
        if old is None or new is None:
            delta = "n/a"
        else:
            d = new - old
            delta = f"{d:+.6f}"
            if d > 1e-8:
                n_up += 1
            elif d < -1e-8:
                n_dn += 1
            else:
                n_eq += 1
        print(
            f"{r['k']:2d} {r['cl']:3d} "
            f"{old if old is not None else float('nan'):10.6f} "
            f"{new if new is not None else float('nan'):10.6f} "
            f"{delta:>10} "
            f"{ot if ot is not None else float('nan'):8.1f} "
            f"{r['time']:8.1f}",
            flush=True,
        )
    print(f"improved={n_up} same={n_eq} worse={n_dn}", flush=True)


if __name__ == "__main__":
    t0 = time.time()
    nosym = run_grid(False)
    compare_grid("nosym", outdir / f"summary_{SPAN}{TAG}_prev.txt", nosym)
    sym = run_grid(True)
    compare_grid("sym", outdir / f"summary_sym_{SPAN}{TAG}_prev.txt", sym)
    print(f"ALL GRIDS DONE in {time.time() - t0:.1f}s", flush=True)
