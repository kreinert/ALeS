# RSHit results: window 150, similarity 0.9

The similarity `sim = 0.9` is the per-base match probability of the homologous
region; `p` is the hit probability the designed set must exceed. Every figure
below was re-checked by Monte Carlo on the full indexed set, reverses included.

## Set B: every shape a palindrome, no core, fewest shapes

One shape suffices at both targets, reached by spending weight downward rather
than adding a second palindrome, which is the intended preference order.

| p       | shapes | weight | span | DP     | Monte Carlo | shape |
|---------|--------|--------|------|--------|-------------|-------|
| > 0.98  | 1      | 22     | 40   | 0.9805 | 0.9804      | `1011100101101110001001000111011010011101` |
| > 0.99  | 1      | 20     | 40   | 0.9936 | 0.9938      | `1111010001010010011001100100101000101111` |

The neighbouring weights bound these from above: weight 23 reaches only 0.9727
and weight 21 only 0.9896, so 22 and 20 are the heaviest weights that work.

## Set A: palindromes forbidden, reverse-doubled, weight 31, span 40

Reverses are free and are not charged against the shape budget, so k designed
shapes put 2k distinct shapes in the index.

Measured ladder at core length 1:

| designed k | indexed 2k | hit probability |
|-----------|------------|-----------------|
| 1  | 2  | 0.8339 |
| 2  | 4  | 0.9045 |
| 3  | 6  | 0.9319 |
| 4  | 8  | 0.9470 |
| 5  | 10 | 0.9571 |
| 6  | 12 | 0.9634 |
| 7  | 14 | 0.9688 |
| 8  | 16 | 0.9724 |
| 13 | 26 | 0.9824 |

p > 0.98 is met by 13 designed shapes at 0.9824 (Monte Carlo 0.9825). Since
eight shapes reach only 0.9724, the minimum lies somewhere in 9..13; 13 is an
upper bound, not the minimum.

**This ladder is not a valid Set A answer.** It was designed with corelength 1,
so the cores it ended up with were incidental: they run 6..13 across the shapes,
and since every shape must carry the core the set only guarantees the minimum,
which is 6. Set A is supposed to maximise the core, so these runs answer a
different question -- how sensitivity grows with shape count -- and are kept only
for that curve.

The exact ceiling settles what a real Set A could reach here. Every shape with
core m needs m consecutive matches, so P(a run of m exists in the window) bounds
any set with that core regardless of weight or shape count. At similarity 0.90
that ceiling is 0.9863 at core 16 and 0.9746 at core 17, so with p > 0.98 the
longest attainable core is 16, and at p > 0.99 it is 15.

p > 0.99 was not reached at weight 31. The per-shape increment has collapsed to
roughly 0.005 by k=7, so it would need considerably more than 13 shapes.

Both Set A entries have core length 1, so the m-core constraint is unexercised
at these targets. A weight-31 shape with span <= 40 has a ceiling of 1.0000 at
this similarity, so 0.99 is not structurally blocked, only expensive.

## The gap between the two sets

A single palindrome of weight 20 beats 26 reverse-doubled shapes of weight 31.
The cause is weight, not palindromicity: at similarity 0.9 over 150 bases,
requiring 31 matches is simply demanding, and dropping to weight 20..22 buys
more than extra shapes can.
