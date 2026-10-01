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


def run_one(weight, k, wl):
    tag = "palB_k%d_w%d_n%d" % (k, weight, wl)
    log = os.path.join(OUTDIR, tag + ".log")
    cmd = [BIN, str(weight), str(k), str(P), str(wl), "1", str(SPAN), "0", "1"]
    with open(log, "w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=False)
    txt = open(log).read()
    # successive construction prints one final per k, so the last one is the full set
    bests = re.findall(r"Best sensitivity is ([0-9.]+)", txt)
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
            for weight in range(MAXWEIGHT, MINWEIGHT - 1, -1):
                sens, shapes = run_one(weight, k, wl)
                span = len(shapes[0]) if shapes else 0
                ok = "" if sens is None else ("  <= clears 0.9" if sens >= 0.9 else "")
                print("%6d %6d %10.4f %6d %s%s"
                      % (k, weight, sens if sens else -1, span,
                         shapes[0] if shapes else "-", ok))
                sys.stdout.flush()
                if sens is not None and sens >= 0.90:
                    break
            else:
                continue
            break


if __name__ == "__main__":
    main()
