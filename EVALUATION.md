# Evaluation: QMC estimator + racing

Built with `make ALeSc` (macOS, 10 OpenMP threads unless noted).
Baseline = the binary shipped before this change.

## QMC estimator: accuracy and cost

`ALESC_REPORT_BOTH=1` prints the exact DP and QMC sensitivities of the final set.

| config (w k sim N core ub sym) | exact | QMC | delta | exact time | QMC time |
|---|---|---|---|---|---|
| 31 1 0.90 100 19 39 1 | 0.624475 | 0.622597 | -0.00188 | 0.00065 s | 0.0093 s |
| 31 1 0.90 100 19 39 1 | 0.621988 | 0.620903 | -0.00109 | 0.00061 s | 0.0093 s |
| 31 1 0.90 100 19 39 1 | 0.621131 | 0.619370 | -0.00176 | 0.00060 s | 0.0093 s |
| 28 1 0.92 70 10 45 0 | 0.659855 | 0.659870 | +0.00001 | 0.00384 s | 0.0029 s |

Mean |delta| ~0.0016 (~0.25% relative). The QMC sample is 2^18 = 262144 windows
versus the old 10^8 (a 381x reduction in scan work and ~1.5 GB less memory).

## Estimator-heavy case (long seeds force the fallback)

`./ALeSc 62 1 0.90 100 10 84`, `OMP_NUM_THREADS=2`, 10 tries, 120 s timeout:

| binary | result |
|---|---|
| baseline (10^8 iid windows) | timed out after 120 s |
| new (2^18 QMC + racing) | 2.0 - 3.3 s |

In a longer baseline run of the w=23,k=2 grid, a single estimator fallback during
final polish took ~60 s; with the new estimator that stage completes in seconds.

## Interpretation

The QMC estimator is a clear win: ~0.25% ranking error at 381x less work, with
common random numbers keeping candidate comparisons stable. For a borderline
feasibility target, raise `ALESC_EST_SAMPLES` back up for the final verification.

## Sliding-window DP + racing in polish

- The DP now keeps only `maxDelta+1` rows (power-of-two, bitmask-indexed) instead of
  `(N+1)`, making DP memory independent of N. Correctness was checked with
  `ALESC_SEED` + `OMP_NUM_THREADS=1` against a reference binary with the old DP:
  **9/9 deterministic runs matched to the last digit** (k=1/2/4, N=100/300).
- Wall time vs the old DP at N=300, 10 tries, single thread: 15.1 s (new) vs
  15.1 s (old) — neutral on time, with a much smaller memory footprint.
- Racing thresholds are now also passed into `greedy_tail_ascent`,
  `greedy_core_slide`, `local_search_from_best` and `findOptimal`, so estimator
  fallbacks during polish abandon hopeless candidates too.
- Parallelizing the polish sweeps (candidate-level and seed-level) was attempted
  and reverted: with these set sizes it changed the hill-climbing trajectory and
  cost 2-4x more DP calls, so the serial polish was kept.

## Standard grid (final binary)

`w=31, p=0.90, N=100, upperBound=39, k=1..4, core=19/21/23/25`, 100 tries,
`OMP_NUM_THREADS=4`, 32 configs, total 49 s. Output in `grid_results_eval/`
(existing `grid_results/` was left untouched).

| core \ k | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 19 (no sym) | 0.4982 | 0.6244 | 0.6664 | 0.6919 |
| 21 (no sym) | 0.4772 | 0.6003 | 0.6292 | 0.6468 |
| 23 (no sym) | 0.4454 | 0.5504 | 0.5691 | 0.5848 |
| 25 (no sym) | 0.4070 | 0.4860 | 0.4990 | 0.5083 |
| 19 (sym) | 0.6220 | 0.6942 | 0.7281 | 0.7462 |
| 21 (sym) | 0.5989 | 0.6487 | 0.6738 | 0.6854 |
| 23 (sym) | 0.5501 | 0.5845 | 0.5996 | 0.6055 |
| 25 (sym) | 0.4871 | 0.5100 | 0.5152 | 0.5179 |
