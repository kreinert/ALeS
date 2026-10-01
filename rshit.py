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


def core_ceiling(wl, sim, m):
    """Exact probability that some run of m consecutive matches occurs in the window.

    Every shape with core m needs m matches in a row, so this bounds the hit probability
    of any set with that core, whatever its weight, span or shape count. The bound is
    tight: a solid m-mer attains it.
    """
    if m <= 1:
        return 1.0 - (1.0 - sim) ** wl
    state = [0.0] * m
    state[0] = 1.0
    reached = 0.0
    for _ in range(wl):
        nxt = [0.0] * m
        for r in range(m):
            v = state[r]
            if not v:
                continue
            if r + 1 >= m:
                reached += v * sim
            else:
                nxt[r + 1] += v * sim
            nxt[0] += v * (1.0 - sim)
        state = nxt
    return reached


def longest_possible_core(wl, sim, p):
    """Largest core whose ceiling still exceeds p. Longer cores are impossible."""
    m = 1
    while m < wl and core_ceiling(wl, sim, m + 1) > p:
        m += 1
    return m


def describe(shapes, indexed):
    for s in shapes:
        print("    %s  span=%d weight=%d core=%d palindrome=%s"
              % (s, len(s), s.count("1"), max(len(r) for r in s.split("0")),
                 s == s[::-1]))
    # Every shape carries the core, so the set only guarantees the shortest of them.
    if shapes:
        print("    guaranteed m-core = %d"
              % min(max(len(r) for r in s.split("0")) for s in shapes))
    print("    %d shape(s) in the index" % indexed)


def set_a(args):
    """A long core, but not bought at too high a price in weight.

    Both matter, so neither gets absolute priority. core_cost fixes the exchange rate: one
    extra core base may cost at most that many units of weight. At the default of 2, core
    18 at weight 31 comfortably beats core 19 at weight 20, since that single extra base
    would cost eleven units of weight and roughly 4^11 times more random hits.
    """
    print("\n=== Set A: longest m-core, palindromes forbidden, reverse-doubled ===")
    print("weight %d down to %d, window %d, similarity %s, need hit probability > %s, "
          "at most %d gapped shapes plus their free reverses"
          % (args.w1, args.minweight, args.wl, args.sim, args.p, args.ms))
    tag0 = "setA_sim%s_p%s_wl%d" % (str(args.sim).replace(".", ""),
                                    str(args.p).replace(".", ""), args.wl)

    def probe(weight, cl, tries):
        tag = "%s_w%d_cl%d_t%d" % (tag0, weight, cl, tries)
        probs, shapes, span = run(weight, args.ms, args.sim, args.wl, cl, args.span,
                                  True, MODE_FORBID_PALINDROME, tag,
                                  target=args.p, tries=tries)
        top = probs[-1] if probs else -1.0
        print("  weight %2d core %2d (%d tries) -> %.4f with %d designed shape(s) %s"
              % (weight, cl, tries, top, len(probs),
                 "ok" if top > args.p else "short"))
        sys.stdout.flush()
        return probs, shapes, span

    cache = {}

    def feasible(weight, cl):
        if (weight, cl) not in cache:
            cache[(weight, cl)] = probe(weight, cl, args.probe_tries)
        probs = cache[(weight, cl)][0]
        return bool(probs) and probs[-1] > args.p

    def confirm(weight, cl):
        probs, shapes, span = probe(weight, cl, args.confirm_tries)
        if probs and probs[-1] > args.p:
            cache[(weight, cl)] = (probs, shapes, span)
            return True
        return False

    # Step 1: the weight, judged at core 1 since that is the easiest core and so decides
    # whether a weight is usable at all.
    if feasible(args.w1, 1):
        weight = args.w1
    else:
        print("  weight %d falls short; re-checking with %d tries before giving it up"
              % (args.w1, args.confirm_tries))
        if confirm(args.w1, 1):
            weight = args.w1
        else:
            if not feasible(args.minweight, 1):
                print("  %s is out of reach even at weight %d with %d shapes."
                      % (args.p, args.minweight, args.ms))
                return None
            lo, hi = args.minweight, args.w1 - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if feasible(mid, 1):
                    lo = mid
                else:
                    hi = mid - 1
            print("  bisection says weight %d; re-checking %d..%d with %d tries"
                  % (lo, lo + 1, min(lo + args.guard, args.w1), args.confirm_tries))
            for wv in range(lo + 1, min(lo + args.guard, args.w1) + 1):
                if confirm(wv, 1):
                    lo = wv
            weight = lo
    print("  weight = %d" % weight)

    # Cores past the exact ceiling are impossible rather than merely hard, so cap there
    # instead of paying for probes that cannot succeed.
    ceiling = longest_possible_core(args.wl, args.sim, args.p)
    print("  core ceiling at this window and similarity allows at most %d" % ceiling)

    def longest_core_at(w):
        """Longest core weight w can carry, capped by the exact ceiling."""
        cap = min(w, ceiling)
        lo, hi = 1, cap
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if feasible(w, mid):
                lo = mid
            else:
                hi = mid - 1
        # A short probe that failed may simply not have searched hard enough, so re-check
        # the cores just above the boundary with a real budget before settling.
        for cl in range(lo + 1, min(lo + args.guard, cap) + 1):
            if confirm(w, cl):
                lo = cl
        return lo

    # Step 2: balance core against weight. A longer core is worth having, but not at any
    # price: core_cost says how many units of weight one extra core base may cost, so
    # core 18 at weight 31 beats core 19 at weight 20 by a wide margin.
    top = weight
    core = longest_core_at(top)

    def score(w, cl):
        return cl - (top - w) / float(args.core_cost)

    best = (score(top, core), top, core)
    print("  weight %d carries core %d (score %.2f)" % (top, core, best[0]))

    # Descend only while a lighter shape could still win. The core can never exceed the
    # ceiling, so once even a ceiling-length core cannot beat the incumbent, stop.
    w = top - 1
    while w >= args.minweight:
        bound = ceiling - (top - w) / float(args.core_cost)
        if bound <= best[0]:
            print("  weight %d could at best score %.2f, so no lighter shape can beat "
                  "%.2f; stopping the descent" % (w, bound, best[0]))
            break
        if feasible(w, 1):
            cl = longest_core_at(w)
            sc = score(w, cl)
            print("  weight %d carries core %d (score %.2f)" % (w, cl, sc))
            if sc > best[0]:
                best = (sc, w, cl)
        w -= 1

    _, weight, lo = best
    probs, shapes, span = cache[(weight, lo)]
    kmin = len(probs)
    print("  balanced choice: core %d at weight %d, needs %d designed shape(s)"
          % (lo, weight, kmin))
    print("  final run at core %d, %d shape(s), full budget, no early exit" % (lo, kmin))
    probs, shapes, span = run(weight, kmin, args.sim, args.wl, lo, span, True,
                              MODE_FORBID_PALINDROME,
                              "%s_w%d_cl%d_final" % (tag0, weight, lo),
                              tries=args.confirm_tries)
    print("  hit probability %.4f at span <= %d" % (probs[-1] if probs else -1, span))
    describe(shapes, 2 * len(shapes))
    return weight, lo, kmin, probs[-1] if probs else None, shapes


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
    ap.add_argument("--core-cost", type=float, default=2.0,
                    help="units of weight one extra core base may cost (Set A)")
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
