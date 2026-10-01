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
largest weight at which core 19 still clears p. That is a single bisection.

Set A forbids palindromes, which matters here: the solid 19-mer attains the ceiling
exactly but is its own reverse, so weight must exceed 19 and some flank cost is
unavoidable.
"""
import sys

from rshit import MODE_FORBID_PALINDROME, run

WL, SIM, P, CORE, MS, SPAN = 150, 0.92, 0.98, 19, 8, 40
TRIES = 250


def probe(weight):
    tag = "frontier_w%d_cl%d" % (weight, CORE)
    probs, shapes, span = run(weight, MS, SIM, WL, CORE, SPAN, True,
                              MODE_FORBID_PALINDROME, tag, target=P, tries=TRIES)
    top = probs[-1] if probs else -1.0
    ok = top > P
    print("  weight %2d core %d -> %.4f with %d designed shape(s) %s"
          % (weight, CORE, top, len(probs), "ok" if ok else "short"))
    sys.stdout.flush()
    return ok, top, shapes, span


def main():
    print("Frontier at wl=%d, sim=%s, p>%s, at most %d gapped shapes plus free reverses"
          % (WL, SIM, P, MS))
    print("core %d has an exact ceiling of 0.9805, so this is the last reachable core"
          % CORE)
    cache = {}

    def feasible(w):
        if w not in cache:
            cache[w] = probe(w)
        return cache[w][0]

    lo, hi = 20, 31          # 20 is the lightest non-palindromic option, 31 known short
    if not feasible(lo):
        print("\ncore %d is out of reach at every weight; the frontier is core 18 "
              "from weight %d all the way to 31." % (CORE, lo))
        return
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if feasible(mid):
            lo = mid
        else:
            hi = mid - 1
    ok, top, shapes, span = cache[lo]
    print("\nheaviest weight reaching core %d is %d (hit %.4f, %d designed shapes)"
          % (CORE, lo, top, len(shapes)))
    print("so the frontier is: core %d for weight 20..%d, core 18 for weight %d..31"
          % (CORE, lo, lo + 1))
    for s in shapes:
        print("    %s  span=%d weight=%d core=%d"
              % (s, len(s), s.count("1"), max(len(r) for r in s.split("0"))))
    if shapes:
        print("    guaranteed m-core = %d"
              % min(max(len(r) for r in s.split("0")) for s in shapes))


if __name__ == "__main__":
    main()
