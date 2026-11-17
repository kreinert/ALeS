#!/usr/bin/env python3
"""Run ALeSc directly over core lengths and report the observed Pareto frontier.

Defaults reproduce the w=31, p=0.90, N=100, upper-bound=39, k=1 sweep.
The reported frontier maximizes both required core length and observed sensitivity.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path


BEST_SENS = re.compile(
    r"Best sensitivity is\s+(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
)
SEED = re.compile(r"^\s*(?:\d+\|)?\s*([01]+)\s*$")


def last_seed_set(text):
    lines = text.splitlines()
    latest = None
    for i, line in enumerate(lines):
        if line.strip() not in ("seeds:", "designed:"):
            continue
        block = []
        for candidate in lines[i + 1 :]:
            match = SEED.match(candidate)
            if not match:
                break
            block.append(match.group(1))
        if block:
            latest = block
    return latest


def run_one(args, core, outdir):
    log = outdir / f"m{core}.log"
    cmd = [str(args.binary), str(args.weight), str(args.k), str(args.sim),
           str(args.window), str(core), str(args.upper_bound),
           "1" if args.reverse_doubling else "0"]
    env = os.environ.copy()
    if args.tries is not None:
        env["ALESC_MAX_TRIES"] = str(args.tries)
    started = time.monotonic()
    with log.open("w") as output:
        proc = subprocess.run(cmd, cwd=args.binary.parent, env=env,
                              stdout=output, stderr=subprocess.STDOUT,
                              timeout=args.timeout, check=False)
    elapsed = time.monotonic() - started
    text = log.read_text(errors="replace")
    found = BEST_SENS.findall(text)
    if proc.returncode != 0 or not found:
        tail = "\n".join(text.splitlines()[-30:])
        raise RuntimeError(
            f"ALeSc failed for m={core} (exit {proc.returncode}, log {log}):\n{tail}"
        )
    shapes = last_seed_set(text) or []
    return {
        "core": core,
        "sensitivity": float(found[-1]),
        "shapes": ";".join(shapes),
        "max_span": max((len(shape) for shape in shapes), default=0),
        "weight": shapes[0].count("1") if shapes else 0,
        "elapsed_seconds": elapsed,
        "log": log.name,
    }


def is_dominated(row, rows):
    return any(
        other["core"] >= row["core"]
        and other["sensitivity"] >= row["sensitivity"]
        and (other["core"] > row["core"]
             or other["sensitivity"] > row["sensitivity"])
        for other in rows
    )


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=root / "ALeSc")
    parser.add_argument("--weight", type=int, default=31)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--sim", type=float, default=0.90)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--upper-bound", type=int, default=39)
    parser.add_argument("--cores", type=int, nargs="+",
                        default=list(range(13, 23)))
    parser.add_argument("--reverse-doubling", action="store_true")
    parser.add_argument("--tries", type=int,
                        help="override ALeSc's ALESC_MAX_TRIES (default: ALeSc default)")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args()
    args.binary = args.binary.resolve()
    if args.outdir is None:
        sim_tag = f"{args.sim:.3f}".replace(".", "")
        args.outdir = root / (
            f"core_pareto_w{args.weight}_p{sim_tag}_N{args.window}_"
            f"ub{args.upper_bound}_k{args.k}_rev{int(args.reverse_doubling)}"
        )
    args.outdir.mkdir(parents=True, exist_ok=True)
    if not args.binary.is_file():
        parser.error(f"ALeSc binary not found: {args.binary}; build it with `make ALeSc`")

    rows = []
    for core in args.cores:
        print(f"Running ALeSc w={args.weight} k={args.k} sim={args.sim} "
              f"N={args.window} m={core} ub={args.upper_bound} "
              f"reverse_doubling={int(args.reverse_doubling)}", flush=True)
        row = run_one(args, core, args.outdir)
        rows.append(row)
        print(f"  sensitivity={row['sensitivity']:.8f} "
              f"({row['elapsed_seconds']:.1f}s)", flush=True)

    frontier = [row for row in rows if not is_dominated(row, rows)]
    frontier.sort(key=lambda row: row["core"])
    fields = ["core", "sensitivity", "shapes", "max_span", "weight",
              "elapsed_seconds", "log"]
    csv_path = args.outdir / "results.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report = args.outdir / "pareto.md"
    with report.open("w") as output:
        output.write("# Observed ALeSc core/sensitivity Pareto frontier\n\n")
        output.write(
            f"- weight: {args.weight}\n- designed seeds: {args.k}\n"
            f"- similarity: {args.sim}\n- region length: {args.window}\n"
            f"- seed length upper bound: {args.upper_bound}\n"
            f"- reverse-doubling: {bool(args.reverse_doubling)}\n\n"
        )
        output.write(
            "Each row is a direct ALeSc run. The frontier maximizes both core "
            "length and observed sensitivity; it is heuristic, not a proof of "
            "the optimum.\n\n"
        )
        output.write("| m | sensitivity | seed set | max span | seconds |\n")
        output.write("|--:|--:|:--|--:|--:|\n")
        for row in frontier:
            shapes = "<br>".join(
                f"`{shape}`" for shape in row["shapes"].split(";") if shape
            )
            output.write(
                f"| {row['core']} | {row['sensitivity']:.8f} | "
                f"{shapes} | {row['max_span']} | "
                f"{row['elapsed_seconds']:.1f} |\n"
            )
        output.write("\nAll runs are in `results.csv`; individual logs are retained.\n")
    print(f"\nPareto report: {report}")
    print(f"All results:   {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired as exc:
        print(f"ALeSc timed out: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
