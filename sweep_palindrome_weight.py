#!/usr/bin/env python3
"""Sweep the weight of a palindromic shape set at m=1 and record best sensitivity.

RSHit prefers a lighter shape over an extra shape, so for each shape count k we need
the largest weight in [minweight, maxweight] that still clears minhit.
"""
import os
import re
import subprocess
import sys

BIN = "./ALeSc"
OUTDIR = "rshit_results"

P = 0.90
SPAN = 38
MINWEIGHT = 15
MAXWEIGHT = 32
RUN_TIMEOUT = 3600

BEST_SENS = re.compile(
    r"Best sensitivity is\s+(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def run_one(weight, k, wl):
    tag = "palB_k%d_w%d_n%d" % (k, weight, wl)
    log = os.path.join(OUTDIR, tag + ".log")
    cmd = [BIN, str(weight), str(k), str(P), str(wl), "1", str(SPAN), "0", "1"]
    try:
        with open(log, "w") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                  check=False, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        sys.stderr.write("ALeSc timed out after %d s (log: %s)\n" % (RUN_TIMEOUT, log))
        raise SystemExit(1)
    with open(log) as fh:
        txt = fh.read()
    if proc.returncode != 0:
        sys.stderr.write("ALeSc failed with exit code %d (log: %s)\n%s\n"
                         % (proc.returncode, log, txt[-2000:]))
        raise SystemExit(1)
    # successive construction prints one final per k, so the last one is the full set
    bests = BEST_SENS.findall(txt)
    shapes = re.findall(r"seeds:\n((?:[01]+\n)+)", txt)
    final = shapes[-1].split() if shapes else []
    return (float(bests[-1]) if bests else None), final


def main():
    wls = [int(a) for a in sys.argv[1:]] or [200, 100]
    os.makedirs(OUTDIR, exist_ok=True)
    for wl in wls:
        print("\n=== window length %d, m=1, p=%s, span <= %d, palindromic ==="
              % (wl, P, SPAN))
        print("%6s %6s %10s %6s %s" % ("k", "weight", "sens", "span", "shape"))
        for k in (1, 2, 3):
            # Each k gets its own sweep: a heavier k may clear where a lighter one did not.
            for weight in range(MAXWEIGHT, MINWEIGHT - 1, -1):
                sens, shapes = run_one(weight, k, wl)
                span = len(shapes[0]) if shapes else 0
                shown = sens if sens is not None else -1.0
                ok = "" if sens is None else ("  <= clears %.2f" % P if sens >= P else "")
                print("%6d %6d %10.4f %6d %s%s"
                      % (k, weight, shown, span,
                         shapes[0] if shapes else "-", ok))
                sys.stdout.flush()
                if sens is not None and sens >= P:
                    break


if __name__ == "__main__":
    main()
