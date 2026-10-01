# RSHit results: window 150, identity 92%, hit probability > 0.98

`sim = 0.92` is the per-base match probability of the homologous region; `p = 0.98`
is the hit probability the designed set must exceed. Both figures below were
re-checked by Monte Carlo over the full indexed set, reverses included.

## Set A: 7 gapped shapes, weight 31, m-core 18, palindromes forbidden

Hit probability 0.9822, Monte Carlo 0.9821 +/- 0.0002.

Designed shapes, the 7 charged against the budget of 8:

    1111111111111111110011001010110011110111
    1011100101011111100100111111111111111111
    1111101110001111111111111111110101101001
    1100111111111111111111010101001001111111
    1110011111011010110111111111111111111
    1111111111111111110010111000111111001011
    1111111111111111110101110110001001011111

Their reverses come free and are not charged, but do sit in the index, so the
index holds 14 distinct shapes and none of them is a palindrome. Every designed
shape has a core of exactly 18, so the guaranteed m-core is 18.

A sixth-shape version of the same configuration reached only 0.9804. That cleared
p by 0.0004, which is below the Monte Carlo standard error of 0.0003, so sampling
could not confirm it; the seventh shape widened the margin to 0.0022 at a
negligible cost in specificity (effective weight 29.2 -> 29.0).

## Set B: 1 palindromic shape, weight 25

Hit probability 0.9863, Monte Carlo 0.9863.

    111110101101001100111001100101101011111

Span 39, and it is its own reverse, so the index holds a single shape. One shape
sufficed by spending weight down from 32; weight 26 reached only 0.9797.

## Why core 18 and not 19

Every shape with core m needs m consecutive matches, so P(a run of m exists in
the window) is an exact ceiling on core m, whatever the weight, span or shape
count, and a solid m-mer attains it. At this window and similarity:

| core | ceiling |
|------|---------|
| 17   | 0.9942  |
| 18   | 0.9888  |
| 19   | 0.9805  |
| 20   | 0.9687  |

So core 20 is impossible outright at p > 0.98, and core 19 is possible only
within 0.0005 of its ceiling, which in practice forces the weight down to about
20. Weight 31 carries core 18, so the balanced choice keeps the weight: buying
that one extra core base would cost eleven units of weight and roughly 4^11
times more random hits. The `--core-cost` option sets this exchange rate and
defaults to 2 units of weight per core base.

## The two sets compared

A set of k shapes of weight w matches a random position with probability
k * 4^-w, so it behaves like a single shape of effective weight w - log4(k).

| set | weight | indexed shapes | effective weight | hit probability |
|-----|--------|----------------|------------------|-----------------|
| A   | 31     | 14             | 29.0             | 0.9822 |
| B   | 25     | 1              | 25.0             | 0.9863 |

Set B is more sensitive but about 4^4 = 256 times less specific. These rates
assume uniform independent bases; real genomes are biased and repetitive, so
absolute random-hit rates will be higher, though the comparison holds.
