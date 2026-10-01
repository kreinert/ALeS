#!/usr/bin/env python3
"""RSHit: shape sets whose hit probability on a sequence window exceeds a target.

Two probabilities are involved and they are deliberately named apart:

  sim  the similarity of the homologous region, i.e. the per-base match probability
  p    the required hit probability, which the designed set must exceed

Set A  long m-core, palindromes forbidden, scored together with the reverses.
       Maximise the core length, using at most ms designed shapes.
Set B  no core (m=1), every shape a palindrome.
       Minimise the shape count; spend weight down to minweight before adding a shape.

Both searches lean on exact monotonicity: hit probability is non-increasing in the core
length and in the weight, and non-decreasing in the shape count, so each dimension can
be bisected instead of swept.

A failed heuristic run is not a proof of infeasibility, so probes use a reduced restart
budget and the boundary is re-checked with a larger one before being reported.
"""
import argparse
import os
import re
import subprocess
import sys

BIN = "./ALeSc"
OUTDIR = "rshit_results"

MODE_FORBID_PALINDROME = "2"
MODE_REQUIRE_PALINDROME = "1"

OUT_OF_REACH = re.compile(r"Re-run with an upper bound of (\d+)")


def run(weight, k, sim, wl, cl, span, symmetry, mode, tag, target=None, tries=None):
    """One ALeSc invocation. Returns (hit probability per shape count, shapes, span).

    A target makes the search stop at the first set clearing the bar, which turns a
    feasibility question from minutes into fractions of a second. Leave it off for the
    final run so the chosen configuration is actually optimised.
    """
    log = os.path.join(OUTDIR, tag + ".log")
    env = dict(os.environ)
    for key, val in (("ALESC_TARGET_SENS", target), ("ALESC_MAX_TRIES", tries)):
        if val:
            env[key] = str(val)
        else:
            env.pop(key, None)
    while True:
        cmd = [BIN, str(weight), str(k), str(sim), str(wl), str(cl), str(span),
               "1" if symmetry else "0", mode]
        with open(log, "w") as fh:
            subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=False, env=env)
        txt = open(log).read()
        hit = OUT_OF_REACH.search(txt)
        if hit:
            # The DP automaton grows like 2^(span-weight); retry at the span it allows.
            span = int(hit.group(1))
            continue
        break
    probs = [float(x) for x in re.findall(r"Best sensitivity is ([0-9.]+)", txt)]
    blocks = re.findall(r"designed:\n((?:[01]+\n)+)", txt)
    if not blocks:
        blocks = re.findall(r"seeds:\n((?:[01]+\n)+)", txt)
    shapes = blocks[-1].split() if blocks else []
    return probs, shapes, span


def describe(shapes, indexed):
    for s in shapes:
        print("    %s  span=%d weight=%d core=%d palindrome=%s"
              % (s, len(s), s.count("1"), max(len(r) for r in s.split("0")),
                 s == s[::-1]))
    print("    %d shape(s) in the index" % indexed)


def set_a(args):
    """Largest core length whose hit probability still exceeds p."""
    print("\n=== Set A: longest m-core, palindromes forbidden, reverse-doubled ===")
    print("weight %d, window %d, similarity %s, need hit probability > %s, "
          "at most %d designed shapes" % (args.w1, args.wl, args.sim, args.p, args.ms))
    tag0 = "setA_sim%s_p%s_wl%d" % (str(args.sim).replace(".", ""),
                                    str(args.p).replace(".", ""), args.wl)

    def probe(cl, tries):
        tag = "%s_cl%d_t%d" % (tag0, cl, tries)
        probs, shapes, span = run(args.w1, args.ms, args.sim, args.wl, cl, args.span,
                                  True, MODE_FORBID_PALINDROME, tag,
                                  target=args.p, tries=tries)
        top = probs[-1] if probs else -1.0
        print("  core %2d (%d tries) -> %.4f with %d shape(s) %s"
              % (cl, tries, top, len(probs), "ok" if top > args.p else "short"))
        sys.stdout.flush()
        return probs, shapes, span

    cache = {}

    def feasible(cl):
        if cl not in cache:
            cache[cl] = probe(cl, args.probe_tries)
        probs = cache[cl][0]
        return bool(probs) and probs[-1] > args.p

    if not feasible(1):
        # The entry condition decides whether Set A exists at all, so never settle it on
        # the cheap budget.
        print("  core 1 fell short on the probe budget; re-checking with %d tries"
              % args.confirm_tries)
        cache[1] = probe(1, args.confirm_tries)
        if not feasible(1):
            print("  hit probability %s is out of reach at weight %d with %d shapes "
                  "(best %.4f)." % (args.p, args.w1, args.ms, cache[1][0][-1]))
            print("  raise --ms, lower --w1, or widen --span.")
            return None

    lo, hi = 1, args.w1          # lo is known feasible, hi is unknown
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if feasible(mid):
            lo = mid
        else:
            hi = mid - 1

    # A short probe that failed may simply not have searched hard enough, so re-check the
    # cores just above the boundary with a real budget before settling.
    print("  bisection says core %d; re-checking %d..%d with %d tries"
          % (lo, lo + 1, min(lo + args.guard, args.w1), args.confirm_tries))
    for cl in range(lo + 1, min(lo + args.guard, args.w1) + 1):
        probs, shapes, span = probe(cl, args.confirm_tries)
        if probs and probs[-1] > args.p:
            lo = cl
            cache[cl] = (probs, shapes, span)

    probs, shapes, span = cache[lo]
    kmin = len(probs)
    print("  longest core = %d, needs %d designed shape(s)" % (lo, kmin))
    print("  final run at core %d, %d shape(s), full budget, no early exit" % (lo, kmin))
    probs, shapes, span = run(args.w1, kmin, args.sim, args.wl, lo, span, True,
                              MODE_FORBID_PALINDROME, "%s_cl%d_final" % (tag0, lo), tries=args.confirm_tries)
    print("  hit probability %.4f at span <= %d" % (probs[-1] if probs else -1, span))
    describe(shapes, 2 * len(shapes))
    return lo, kmin, probs[-1] if probs else None, shapes


def set_b(args):
    """Fewest palindromes; prefer dropping weight over adding a shape."""
    print("\n=== Set B: palindromic, m=1, fewest shapes ===")
    print("weight %d down to %d, window %d, similarity %s, need hit probability > %s"
          % (args.w2, args.minweight, args.wl, args.sim, args.p))
    tag0 = "setB_sim%s_p%s_wl%d" % (str(args.sim).replace(".", ""),
                                    str(args.p).replace(".", ""), args.wl)

    for k in range(1, args.ms + 1):
        cache = {}

        def probe(weight, tries):
            tag = "%s_k%d_w%d_t%d" % (tag0, k, weight, tries)
            probs, shapes, span = run(weight, k, args.sim, args.wl, 1, args.span,
                                      False, MODE_REQUIRE_PALINDROME, tag,
                                      target=args.p, tries=tries)
            top = probs[-1] if probs else -1.0
            print("  k=%d weight %2d (%d tries) -> %.4f %s"
                  % (k, weight, tries, top, "ok" if top > args.p else "short"))
            sys.stdout.flush()
            return probs, shapes, span

        def feasible(weight):
            if weight not in cache:
                cache[weight] = probe(weight, args.probe_tries)
            probs = cache[weight][0]
            return bool(probs) and probs[-1] > args.p

        # Probe the ceiling first: it is both the preferred answer and by far the cheapest
        # to score, since a sparse shape blows up the DP automaton.
        if feasible(args.w2):
            lo = args.w2
        else:
            # The lightest allowed shape is the easiest; if even that falls short, no
            # weight in range will do and k has to grow.
            if not feasible(args.minweight):
                print("  k=%d cannot exceed %s even at weight %d"
                      % (k, args.p, args.minweight))
                continue
            lo, hi = args.minweight, args.w2 - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if feasible(mid):
                    lo = mid
                else:
                    hi = mid - 1
            print("  bisection says weight %d; re-checking %d..%d with %d tries"
                  % (lo, lo + 1, min(lo + args.guard, args.w2), args.confirm_tries))
            for weight in range(lo + 1, min(lo + args.guard, args.w2) + 1):
                probs, shapes, span = probe(weight, args.confirm_tries)
                if probs and probs[-1] > args.p:
                    lo = weight
                    cache[weight] = (probs, shapes, span)

        print("  %d palindromic shape(s), weight %d" % (k, lo))
        print("  final run at weight %d, %d shape(s), full budget, no early exit"
              % (lo, k))
        probs, shapes, span = run(lo, k, args.sim, args.wl, 1, args.span, False,
                                  MODE_REQUIRE_PALINDROME, "%s_k%d_w%d_final" % (tag0, k, lo), tries=args.confirm_tries)
        print("  hit probability %.4f at span <= %d" % (probs[-1] if probs else -1, span))
        describe(shapes, len(shapes))
        return k, lo, probs[-1] if probs else None, shapes
    print("  no palindromic set up to %d shapes exceeded %s" % (args.ms, args.p))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wl", type=int, required=True, help="sequence window length")
    ap.add_argument("--sim", type=float, default=0.9,
                    help="similarity of the region, i.e. per-base match probability")
    ap.add_argument("--p", type=float, required=True,
                    help="required hit probability, which the set must exceed")
    ap.add_argument("--ms", type=int, default=4, help="maximum number of shapes")
    ap.add_argument("--w1", type=int, default=31, help="weight of the m-core set")
    ap.add_argument("--w2", type=int, default=32, help="starting weight of the palindromic set")
    ap.add_argument("--minweight", type=int, default=15)
    ap.add_argument("--span", type=int, default=40, help="seed length upper bound to try")
    ap.add_argument("--probe-tries", type=int, default=600,
                    help="restart budget for feasibility probes")
    ap.add_argument("--confirm-tries", type=int, default=4000,
                    help="restart budget for re-checking the boundary")
    ap.add_argument("--guard", type=int, default=2,
                    help="how far past the boundary to re-check with the larger budget")
    ap.add_argument("--only", choices=["a", "b"])
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    print("RSHit: window %d, similarity %s, hit probability must exceed %s, "
          "at most %d shapes" % (args.wl, args.sim, args.p, args.ms))
    if args.only != "b":
        set_a(args)
    if args.only != "a":
        set_b(args)


if __name__ == "__main__":
    main()
