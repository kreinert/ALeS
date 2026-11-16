#!/usr/bin/env python3
"""Core-versus-weight frontier for Set A. Exploration only, not the design policy.

This measures what a longer core would cost in weight. The answer informed the default
of --core-cost in rshit.py: a core of 19 needs roughly weight 20, so one extra core base
costs about eleven units of weight, which Set A refuses. Use rshit.py to design; use this
only to re-measure the exchange rate at other parameters.

Every shape with core m needs m consecutive matches, so P(a run of m exists in the
window) is an exact ceiling on core m for any weight and any shape count. At wl=150,
sim=0.92 that ceiling is 0.9805 at m=19 and 0.9687 at m=20, so with p=0.98 the longest
conceivable core is 19 and core 20 is impossible outright.

Core 18 is already known feasible at the heaviest weight, and feasibility only improves
as weight falls, so the frontier is 18 or 19 everywhere and is pinned by one number: the
largest weight at which the longest reachable core still clears p. That is a single
bisection.

Set A forbids palindromes, which matters here: the solid m-mer attains the ceiling
exactly but is its own reverse, so weight must exceed m and some flank cost is
unavoidable.
"""
import sys

from rshit import (MODE_FORBID_PALINDROME, core_ceiling, longest_possible_core,
                   run)

WL, SIM, P, MS, SPAN = 150, 0.92, 0.98, 8, 40
TRIES = 250


def probe(weight, core):
    tag = "frontier_w%d_cl%d" % (weight, core)
    probs, shapes, span = run(weight, MS, SIM, WL, core, SPAN, True,
                              MODE_FORBID_PALINDROME, tag, target=P, tries=TRIES)
    top = probs[-1] if probs else -1.0
    ok = top > P
    print("  weight %2d core %d -> %.4f with %d designed shape(s) %s"
          % (weight, core, top, len(probs), "ok" if ok else "short"))
    sys.stdout.flush()
    return ok, top, shapes, span


def main():
    core = longest_possible_core(WL, SIM, P)
    ceiling = core_ceiling(WL, SIM, core)
    print("Frontier at wl=%d, sim=%s, p>%s, at most %d gapped shapes plus free reverses"
          % (WL, SIM, P, MS))
    print("core %d has an exact ceiling of %.4f, so this is the last reachable core"
          % (core, ceiling))
    cache = {}

    def feasible(w):
        if w not in cache:
            cache[w] = probe(w, core)
        return cache[w][0]

    # The solid core is its own reverse, so Set A needs weight > core. The heaviest
    # usable weight is the span bound itself; feasibility is monotone in weight.
    lo, hi = core + 1, SPAN
    if lo > hi:
        print("\nno non-palindromic weight can carry core %d within span %d" % (core, hi))
        return
    if not feasible(lo):
        print("\ncore %d is out of reach at every weight; the frontier is core %d "
              "from weight %d all the way to %d." % (core, core - 1, core, SPAN))
        return
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if feasible(mid):
            lo = mid
        else:
            hi = mid - 1
    ok, top, shapes, span = cache[lo]
    print("\nheaviest weight reaching core %d is %d (hit %.4f, %d designed shapes)"
          % (core, lo, top, len(shapes)))
    if lo < SPAN:
        print("so the frontier is: core %d for weight %d..%d, core %d for weight %d..%d"
              % (core, core + 1, lo, core - 1, lo + 1, SPAN))
    else:
        print("so the frontier is: core %d for weight %d..%d"
              % (core, core + 1, lo))
    for s in shapes:
        print("    %s  span=%d weight=%d core=%d"
              % (s, len(s), s.count("1"), max(len(r) for r in s.split("0"))))
    if shapes:
        print("    guaranteed m-core = %d"
              % min(max(len(r) for r in s.split("0")) for s in shapes))


if __name__ == "__main__":
    main()
