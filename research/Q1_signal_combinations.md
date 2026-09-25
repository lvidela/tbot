# Q1 — Which COMBINATION of conditions produces positive net expected value?

**Date:** 2026-09-24  **Status:** COMPLETE — **negative result**
**Script:** `/home/lisandro/backtests/signal_combinations.py`  **Raw output:** `q1_output.txt`, `q1_results.json`
**Data:** local cache only (`/home/lisandro/data/cache/`). No Kraken calls, no orders.

---

## Bottom line

**No combination of the five conditions produces a positive net expected value that
survives honest statistical treatment.** Zero of 93 tests clear Bonferroni. A
schedule-preserving permutation test is worse than that: the observed maximum |t|
across the whole family (2.40) is *below the median* maximum |t| produced by random
asset selection (3.33), giving a family-wise p-value of **0.97**. The entire result
surface is indistinguishable from — in fact slightly weaker than — noise.

The three best-looking combinations all have **negative medians** and all collapse when
a **single asset-day (NILUSD, 2026-09-20, +96.8% 3-day excess)** is removed. This is the
same failure mode as R1/R2, one layer deeper.

---

## Method

**Decision timestamp.** `T` = the close of daily bar `t` (00:00 UTC). Every condition is
computed from bars that close at or before `T`. Forward returns run from `close_t` to
`close_{t+h}`, h in {1,2,3} days. No look-ahead.

**Conditions** (exactly as specified in the directive):

| name | definition, all measured at `T` |
|---|---|
| `vol_exp` | \|1d return\| / stdev of the **prior 30** daily returns (t−30 … t−1) ≥ 1.5 |
| `vol_conf` | 1d USD volume (volume x vwap) / mean USD volume over the **prior 30** days ≥ 3.0 |
| `momentum` | last 4h bar return ≥ +2% **AND** trailing 12h return > 0 (from 4h bars closing at T) |
| `breakout` | close ≥ lo30 + 0.95·(hi30 − lo30), (hi30 − lo30)/close ≥ 3%, and 1d return > 0 |
| `rel_str` | trailing 12h return − same-day cross-sectional **median** 12h return ≥ +3% |

Trailing vol and volume baselines deliberately **exclude** the current day so the ratio is
not mechanically bounded. The 30d high/low range includes the current day (it is known at
the close). "Positive momentum" in the breakout definition is read as 1d return > 0.

**Universe.** 32 pairs: all 37 cached pairs minus `USDTUSD`/`USDCUSD` (`is_stable`) minus
`EURUSD`, `GBPUSD`, `PAXGUSD`.

**Mandatory corrections applied.**
1. *Cross-sectional demeaning* — every forward return has the same-day equal-weight
   universe forward return subtracted (universe = all eligible pairs with data that day,
   not just the firing ones). This removes market beta; what is left is selection skill.
2. *Date clustering* — all events on one calendar day are averaged into **one** observation
   before any mean, median or t-statistic is computed. t = mean / (sd/sqrt(n_days)),
   p from Student-t with n_days−1 df.
3. *Costs* — NET excess = mean excess − **1.83%** (registry A1: 4 legs at 0.40% maker
   + ~5.4 bps/leg adverse selection).
4. *Multiple testing* — 31 subsets x 3 horizons = **93 tests**. Bonferroni alpha =
   0.05/93 = **5.376e-4**, i.e. a **|t| ≥ 3.461** threshold.
5. *Chronological split* — each subset's own computable date range is split 50/50;
   in-sample (IS) and out-of-sample (OOS) reported separately.

**Sample-window caveat (important).** 4h bars only exist from **2026-05-27** onward.
Any subset containing `momentum` or `rel_str` is therefore restricted to a **120-day**
window, while daily-only subsets (`vol_exp`, `vol_conf`, `breakout`) span **690 days**.
Cross-subset comparisons of net excess are *not* like-for-like, and the momentum/rel_str
subsets are badly underpowered — see the MDE column.

---

## Results — all 93 tests, sorted by NET excess

`MDE` = the mean excess that would have been required to reach the Bonferroni |t|
threshold given that cell's realised dispersion and n_days. It is the honest measure of
whether the test could ever have said yes.

```
subset                                        h   nev  nday     mean   median      t       p      NET   P>c   ISmean    ISt  OOSmean   OOSt       MDE
-----------------------------------------------------------------------------------------------------------------------------------------------------
vol_exp+vol_conf+momentum+rel_str             3    35    23   +5.86%   -0.50%   1.27  0.2187   +4.03%  0.39   +1.71%   0.50   +8.07%   1.17   +16.01%
vol_conf+momentum+rel_str                     3    37    24   +4.87%   -1.21%   1.10  0.2830   +3.04%  0.33   -0.03%  -0.01   +7.33%   1.13   +15.35%
vol_exp+vol_conf+momentum                     3    64    24   +4.74%   -2.09%   1.07  0.2956   +2.91%  0.33   +1.71%   0.50   +6.25%   0.97   +15.31%
vol_conf+momentum+breakout+rel_str            3    14    10   +4.26%   -0.53%   1.10  0.2990   +2.43%  0.40   -7.36%    n/a   +5.55%   1.36   +13.39%
vol_exp+vol_conf+momentum+breakout+rel_str    3    14    10   +4.26%   -0.53%   1.10  0.2990   +2.43%  0.40   -7.36%    n/a   +5.55%   1.36   +13.39%
vol_conf+momentum                             3    73    26   +3.90%   -1.21%   0.96  0.3474   +2.07%  0.31   -0.03%  -0.01   +5.64%   0.98   +14.08%
vol_conf+breakout                             3   118    71   +3.28%   +0.17%   2.06  0.0435   +1.45%  0.39   +3.76%   1.55   +2.65%   1.39    +5.51%
vol_exp+vol_conf+momentum+breakout            3    19    11   +3.05%   -1.93%   0.86  0.4074   +1.22%  0.36   -7.36%    n/a   +4.09%   1.10   +12.21%
vol_exp+momentum+rel_str                      3    74    47   +3.02%   -0.61%   1.28  0.2071   +1.19%  0.38   +0.06%   0.03   +5.42%   1.35    +8.17%
vol_conf+momentum+breakout+rel_str            2    16    11   +2.84%   +1.37%   1.04  0.3226   +1.01%  0.45   -2.70%    n/a   +3.39%   1.15    +9.43%
vol_exp+vol_conf+momentum+breakout+rel_str    2    16    11   +2.84%   +1.37%   1.04  0.3226   +1.01%  0.45   -2.70%    n/a   +3.39%   1.15    +9.43%
vol_exp+vol_conf+rel_str                      3    67    35   +2.73%   -1.93%   1.40  0.1712   +0.90%  0.37   -0.29%  -0.08   +4.12%   1.76    +6.77%
vol_conf+momentum+breakout                    3    22    11   +2.67%   +0.87%   0.82  0.4297   +0.84%  0.45   -7.36%    n/a   +3.67%   1.08   +11.22%
vol_exp+momentum                              3   127    49   +2.34%   -0.77%   1.04  0.3031   +0.51%  0.37   +0.56%   0.33   +3.78%   0.98    +7.77%
vol_conf+breakout                             2   120    72   +2.16%   +0.82%   1.49  0.1399   +0.33%  0.42   +3.08%   1.30   +1.02%   0.73    +5.02%
vol_exp+momentum+rel_str                      2    77    48   +2.06%   +0.12%   1.63  0.1104   +0.23%  0.38   +0.83%   0.57   +3.02%   1.54    +4.38%
vol_exp+vol_conf+momentum+rel_str             2    38    24   +2.00%   +1.40%   1.15  0.2632   +0.17%  0.46   +3.27%   1.23   +1.37%   0.60    +6.04%
vol_exp+vol_conf+momentum                     2    68    25   +1.97%   +1.37%   1.24  0.2252   +0.14%  0.44   +3.27%   1.23   +1.36%   0.68    +5.48%
vol_conf+breakout+rel_str                     3    20    13   +1.79%   +0.08%   0.59  0.5645   -0.04%  0.38   -7.36%    n/a   +2.55%   0.80   +10.47%
vol_conf+momentum                             2    78    27   +1.74%   +1.28%   1.13  0.2672   -0.09%  0.41   +2.13%   0.84   +1.57%   0.81    +5.30%
vol_conf+rel_str                              3    82    41   +1.69%   -1.93%   1.04  0.3049   -0.14%  0.37   -0.95%  -0.42   +2.91%   1.37    +5.61%
vol_exp+momentum+breakout+rel_str             2    26    17   +1.68%   +1.28%   1.13  0.2753   -0.15%  0.41   -1.81%  -1.43   +3.58%   1.79    +5.14%
vol_exp+vol_conf+momentum+breakout            2    21    12   +1.67%   +1.33%   0.68  0.5082   -0.16%  0.42   -2.70%    n/a   +2.06%   0.78    +8.44%
vol_exp+vol_conf                              3   463   225   +1.62%   -0.33%   2.01  0.0457   -0.21%  0.38   +4.26%   3.16   -0.53%  -0.56    +2.80%
vol_exp+vol_conf+breakout+rel_str             3    19    13   +1.59%   -0.09%   0.53  0.6081   -0.24%  0.31   -7.36%    n/a   +2.34%   0.73   +10.48%
vol_exp+momentum                              2   131    50   +1.58%   +0.48%   1.46  0.1516   -0.25%  0.36   +0.86%   0.63   +2.14%   1.32    +3.75%
vol_exp+rel_str                               3   140    64   +1.53%   -0.20%   1.36  0.1775   -0.30%  0.36   -0.56%  -0.34   +3.04%   2.05    +3.87%
vol_conf                                      3   947   369   +1.49%   -0.37%   2.40  0.0167   -0.34%  0.38   +3.39%   3.68   -0.18%  -0.22    +2.15%
vol_exp+momentum+breakout+rel_str             3    24    16   +1.45%   -0.36%   0.73  0.4759   -0.38%  0.31   -2.28%  -1.07   +3.69%   1.35    +6.86%
vol_conf+momentum+rel_str                     2    40    25   +1.44%   +1.28%   0.87  0.3930   -0.39%  0.40   +2.13%   0.84   +1.12%   0.51    +5.73%
vol_exp+vol_conf                              2   469   226   +1.42%   +0.02%   2.16  0.0316   -0.41%  0.36   +3.23%   2.89   -0.05%  -0.06    +2.27%
momentum+breakout+rel_str                     2    29    18   +1.39%   +0.96%   1.00  0.3320   -0.44%  0.39   -1.09%  -0.84   +2.97%   1.46    +4.82%
vol_conf+breakout+rel_str                     2    22    14   +1.39%   +1.33%   0.66  0.5222   -0.44%  0.43   -2.70%    n/a   +1.70%   0.75    +7.32%
momentum+breakout+rel_str                     3    26    17   +1.24%   -1.09%   0.62  0.5430   -0.59%  0.35   -0.87%  -0.38   +2.72%   0.90    +6.91%
vol_exp+rel_str                               2   144    65   +1.20%   -0.21%   1.51  0.1362   -0.63%  0.35   -0.05%  -0.03   +2.08%   2.26    +2.74%
vol_exp+vol_conf+breakout+rel_str             2    21    14   +1.12%   +1.33%   0.54  0.5962   -0.71%  0.43   -2.70%    n/a   +1.41%   0.64    +7.13%
vol_conf                                      2   958   370   +1.11%   -0.19%   2.12  0.0348   -0.72%  0.35   +2.26%   2.85   +0.10%   0.15    +1.82%
breakout                                      3   418   179   +1.07%   +0.10%   1.60  0.1112   -0.76%  0.34   -0.09%  -0.12   +2.73%   2.35    +2.32%
vol_exp+rel_str                               1   145    66   +1.07%   +0.09%   1.52  0.1327   -0.76%  0.36   +1.25%   1.24   +0.94%   0.97    +2.43%
vol_exp+vol_conf+breakout                     3    99    62   +1.02%   -0.73%   0.80  0.4264   -0.81%  0.34   +0.74%   0.41   +1.35%   0.73    +4.43%
vol_conf+breakout                             1   120    72   +0.84%   -0.45%   0.90  0.3722   -0.99%  0.32   +2.22%   1.49   -0.88%  -0.94    +3.25%
vol_exp+vol_conf+rel_str                      2    71    36   +0.82%   +1.21%   0.73  0.4703   -1.01%  0.42   +0.66%   0.24   +0.89%   0.81    +3.91%
vol_exp+breakout+rel_str                      2    32    21   +0.82%   +0.63%   0.62  0.5399   -1.01%  0.38   -1.63%  -1.50   +2.04%   1.12    +4.54%
vol_exp+vol_conf                              1   472   227   +0.81%   +0.17%   2.34  0.0203   -1.02%  0.36   +1.64%   2.90   +0.15%   0.35    +1.20%
vol_exp+momentum+rel_str                      1    78    49   +0.80%   +0.21%   0.97  0.3350   -1.03%  0.43   +1.32%   1.13   +0.41%   0.35    +2.85%
vol_exp+momentum                              1   132    51   +0.79%   -0.05%   0.94  0.3523   -1.04%  0.35   +1.06%   0.96   +0.59%   0.48    +2.92%
breakout                                      2   423   180   +0.74%   +0.01%   1.40  0.1625   -1.09%  0.32   +0.44%   0.61   +1.15%   1.52    +1.82%
vol_conf+rel_str                              2    86    42   +0.71%   -0.21%   0.79  0.4360   -1.12%  0.38   +0.07%   0.04   +1.00%   0.97    +3.12%
vol_exp+vol_conf+rel_str                      1    72    37   +0.70%   +0.22%   0.71  0.4794   -1.13%  0.38   +1.45%   0.75   +0.38%   0.33    +3.38%
vol_conf+momentum+breakout                    2    24    12   +0.65%   +1.33%   0.30  0.7701   -1.18%  0.42   -2.70%    n/a   +0.95%   0.41    +7.51%
vol_exp                                       3  2577   501   +0.62%   -0.05%   1.89  0.0594   -1.21%  0.31   +1.16%   2.33   +0.11%   0.27    +1.14%
vol_conf                                      1   967   371   +0.60%   +0.10%   1.75  0.0802   -1.23%  0.31   +1.12%   2.44   +0.14%   0.29    +1.18%
vol_exp                                       2  2583   502   +0.59%   +0.03%   2.18  0.0297   -1.24%  0.28   +1.02%   2.34   +0.19%   0.57    +0.94%
momentum+rel_str                              3   124    69   +0.47%   -1.81%   0.28  0.7809   -1.36%  0.35   -2.49%  -2.14   +3.69%   1.16    +5.79%
vol_conf+rel_str                              1    89    43   +0.47%   +0.17%   0.59  0.5571   -1.36%  0.35   +1.61%   0.92   -0.03%  -0.03    +2.73%
vol_exp+breakout+rel_str                      3    30    20   +0.35%   -0.01%   0.20  0.8407   -1.48%  0.25   -1.89%  -1.03   +1.56%   0.63    +6.03%
breakout                                      1   423   180   +0.34%   +0.25%   0.95  0.3424   -1.49%  0.32   +0.39%   0.81   +0.27%   0.51    +1.24%
vol_exp+momentum+breakout                     2    35    19   +0.34%   +0.63%   0.25  0.8080   -1.49%  0.32   -1.76%  -1.36   +1.30%   0.70    +4.72%
vol_exp+vol_conf+momentum                     1    69    26   +0.33%   -0.02%   0.25  0.8017   -1.50%  0.38   +0.44%   0.24   +0.28%   0.16    +4.52%
vol_exp                                       1  2594   503   +0.21%   -0.01%   1.23  0.2189   -1.62%  0.22   +0.40%   1.57   +0.02%   0.09    +0.58%
vol_exp+breakout                              2   225   118   +0.17%   +0.38%   0.27  0.7896   -1.66%  0.32   +0.37%   0.40   -0.12%  -0.14    +2.23%
vol_exp+breakout                              3   223   117   +0.06%   -0.86%   0.08  0.9389   -1.77%  0.30   +0.03%   0.03   +0.10%   0.08    +2.73%
vol_exp+momentum+breakout                     3    33    18   +0.02%   -1.51%   0.01  0.9911   -1.81%  0.22   -2.11%  -0.97   +1.09%   0.42    +6.51%
vol_exp+vol_conf+breakout                     2   101    63   +0.02%   +0.40%   0.02  0.9848   -1.81%  0.40   -0.03%  -0.02   +0.07%   0.05    +3.29%
breakout+rel_str                              2    41    25   -0.02%   -1.76%  -0.02  0.9879   -1.85%  0.32   -1.94%  -1.77   +1.26%   0.69    +4.16%
vol_conf+momentum                             1    79    28   -0.05%   -0.02%  -0.05  0.9622   -1.88%  0.32   +0.59%   0.33   -0.31%  -0.22    +3.97%
momentum+rel_str                              2   129    70   -0.06%   -0.80%  -0.07  0.9466   -1.89%  0.31   -1.57%  -1.74   +1.54%   0.98    +3.15%
rel_str                                       3   302   108   -0.11%   -1.03%  -0.18  0.8575   -1.94%  0.29   -1.64%  -2.12   +1.54%   1.73    +2.09%
vol_exp+vol_conf+breakout                     1   101    63   -0.12%   -0.75%  -0.14  0.8858   -1.95%  0.30   +0.68%   0.55   -0.99%  -1.01    +2.76%
rel_str                                       1   316   110   -0.16%   -0.17%  -0.39  0.6985   -1.99%  0.26   -0.13%  -0.27   -0.18%  -0.28    +1.38%
momentum+breakout                             3    39    20   -0.27%   -1.51%  -0.15  0.8821   -2.10%  0.30   -0.72%  -0.31   -0.03%  -0.01    +6.21%
vol_exp+breakout                              1   225   118   -0.30%   -0.65%  -0.59  0.5573   -2.13%  0.29   +0.17%   0.24   -0.98%  -1.40    +1.77%
momentum+breakout                             2    43    21   -0.30%   -1.76%  -0.25  0.8033   -2.13%  0.29   -1.05%  -0.81   +0.07%   0.04    +4.18%
momentum                                      1   322    80   -0.36%   -0.19%  -0.72  0.4735   -2.19%  0.24   -0.34%  -0.52   -0.38%  -0.49    +1.74%
rel_str                                       2   308   109   -0.36%   -0.68%  -0.78  0.4342   -2.19%  0.26   -1.42%  -2.79   +0.76%   1.01    +1.59%
vol_exp+vol_conf+momentum+rel_str             1    39    25   -0.38%   +0.21%  -0.31  0.7567   -2.21%  0.36   +0.44%   0.24   -0.76%  -0.49    +4.18%
breakout+rel_str                              3    38    24   -0.39%   -0.51%  -0.24  0.8119   -2.22%  0.29   -1.76%  -1.02   +0.59%   0.24    +5.55%
vol_conf+momentum+rel_str                     1    41    26   -0.39%   -0.02%  -0.34  0.7377   -2.22%  0.35   +0.59%   0.33   -0.83%  -0.56    +3.99%
momentum                                      2   321    79   -0.46%   -0.85%  -0.81  0.4216   -2.29%  0.29   -1.41%  -2.04   +0.57%   0.63    +1.97%
momentum+rel_str                              1   130    71   -0.49%   -0.30%  -0.81  0.4233   -2.32%  0.30   -0.55%  -0.71   -0.43%  -0.45    +2.10%
momentum                                      3   312    78   -0.63%   -1.14%  -0.81  0.4178   -2.46%  0.28   -2.01%  -2.05   +0.90%   0.76    +2.68%
vol_conf+momentum+breakout+rel_str            1    16    11   -0.87%   -1.87%  -0.44  0.6659   -2.70%  0.18   -8.42%    n/a   -0.12%  -0.06    +6.77%
vol_exp+vol_conf+momentum+breakout+rel_str    1    16    11   -0.87%   -1.87%  -0.44  0.6659   -2.70%  0.18   -8.42%    n/a   -0.12%  -0.06    +6.77%
vol_exp+vol_conf+momentum+breakout            1    21    12   -0.90%   -1.45%  -0.50  0.6256   -2.73%  0.17   -8.42%    n/a   -0.21%  -0.12    +6.18%
momentum+breakout+rel_str                     1    29    18   -1.00%   +0.03%  -0.78  0.4463   -2.83%  0.22   -0.53%  -0.37   -1.30%  -0.67    +4.42%
vol_exp+momentum+breakout+rel_str             1    26    17   -1.14%   -0.06%  -0.86  0.4033   -2.97%  0.18   -1.07%  -0.70   -1.17%  -0.61    +4.58%
vol_exp+breakout+rel_str                      1    32    21   -1.30%   -0.31%  -1.14  0.2695   -3.13%  0.19   -0.40%  -0.28   -1.75%  -1.11    +3.97%
vol_exp+momentum+breakout                     1    35    19   -1.45%   -0.97%  -1.19  0.2487   -3.28%  0.16   -1.01%  -0.65   -1.65%  -0.99    +4.21%
momentum+breakout                             1    43    21   -1.48%   -0.97%  -1.31  0.2063   -3.31%  0.24   -0.48%  -0.34   -1.99%  -1.27    +3.93%
breakout+rel_str                              1    41    25   -1.51%   -0.61%  -1.57  0.1284   -3.34%  0.20   -0.63%  -0.54   -2.09%  -1.49    +3.31%
vol_exp+vol_conf+breakout+rel_str             1    21    14   -1.54%   -2.43%  -0.95  0.3582   -3.37%  0.14   -8.42%    n/a   -1.02%  -0.61    +5.61%
vol_conf+momentum+breakout                    1    24    12   -1.56%   -2.50%  -0.88  0.4000   -3.39%  0.17   -8.42%    n/a   -0.93%  -0.51    +6.15%
vol_conf+breakout+rel_str                     1    22    14   -1.57%   -2.60%  -0.97  0.3514   -3.40%  0.14   -8.42%    n/a   -1.04%  -0.63    +5.62%
```

```
SAMPLE WINDOWS (days on which the subset is computable at all):
  breakout                                     2024-11-03 .. 2026-09-24  (691 days)
  breakout+rel_str                             2026-05-28 .. 2026-09-24  (120 days)
  momentum                                     2026-05-28 .. 2026-09-24  (120 days)
  momentum+breakout                            2026-05-28 .. 2026-09-24  (120 days)
  momentum+breakout+rel_str                    2026-05-28 .. 2026-09-24  (120 days)
  momentum+rel_str                             2026-05-28 .. 2026-09-24  (120 days)
  rel_str                                      2026-05-28 .. 2026-09-24  (120 days)
  vol_conf                                     2024-11-03 .. 2026-09-24  (691 days)
  vol_conf+breakout                            2024-11-03 .. 2026-09-24  (691 days)
  vol_conf+breakout+rel_str                    2026-05-28 .. 2026-09-24  (120 days)
  vol_conf+momentum                            2026-05-28 .. 2026-09-24  (120 days)
  vol_conf+momentum+breakout                   2026-05-28 .. 2026-09-24  (120 days)
  vol_conf+momentum+breakout+rel_str           2026-05-28 .. 2026-09-24  (120 days)
  vol_conf+momentum+rel_str                    2026-05-28 .. 2026-09-24  (120 days)
  vol_conf+rel_str                             2026-05-28 .. 2026-09-24  (120 days)
  vol_exp                                      2024-11-04 .. 2026-09-24  (690 days)
  vol_exp+breakout                             2024-11-04 .. 2026-09-24  (690 days)
  vol_exp+breakout+rel_str                     2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+momentum                             2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+momentum+breakout                    2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+momentum+breakout+rel_str            2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+momentum+rel_str                     2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+rel_str                              2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf                             2024-11-04 .. 2026-09-24  (690 days)
  vol_exp+vol_conf+breakout                    2024-11-04 .. 2026-09-24  (690 days)
  vol_exp+vol_conf+breakout+rel_str            2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf+momentum                    2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf+momentum+breakout           2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf+momentum+breakout+rel_str   2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf+momentum+rel_str            2026-05-28 .. 2026-09-24  (120 days)
  vol_exp+vol_conf+rel_str                     2026-05-28 .. 2026-09-24  (120 days)
```

---

## Multiple testing

- Bonferroni: alpha = 5.376e-4, **|t| ≥ 3.461**. **0 of 93 tests survive.**
  The largest |t| anywhere in the family is 2.40 (`vol_conf`, h=3) — and that one has a
  *negative* NET (−0.34%), so it is not even a candidate edge.
- The 93 tests are heavily correlated (nested subsets, overlapping horizons), so Bonferroni
  is conservative. I therefore ran a **schedule-preserving permutation test** (2,000 draws):
  for every test the realised (day → number of events) schedule is held fixed and the
  *selected assets* are re-drawn at random from that day's eligible pool. This preserves
  date clustering, event counts and cross-sectional correlation, and destroys only the
  signal→asset link.

| statistic | value |
|---|---|
| observed max \|t\| over all 93 tests | **2.404** |
| null median max \|t\| | 3.329 |
| null 95th percentile max \|t\| | 4.692 |
| **family-wise p-value** | **0.971** |

Read that carefully: random selection *typically* produces a stronger-looking best result
than the real signals do. The signal family is not merely insignificant, it is unremarkable
even by the standards of pure noise. The reason is the long right tail of crypto returns
combined with small n_days — a handful of random picks on a day with one 100% mover
generates large |t| easily.

---

## The top 3 combinations, dissected

Ranked by NET excess (all at h=3d):

| rank | combination | n_ev | n_days | mean | **median** | t | NET | P(excess>1.83%) | IS mean (t) | OOS mean (t) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | vol_exp+vol_conf+momentum+rel_str | 35 | 23 | +5.86% | **−0.50%** | 1.27 | **+4.03%** | 0.39 | +1.71% (0.50) | +8.07% (1.17) |
| 2 | vol_conf+momentum+rel_str | 37 | 24 | +4.87% | **−1.21%** | 1.10 | **+3.04%** | 0.33 | −0.03% (−0.01) | +7.33% (1.13) |
| 3 | vol_exp+vol_conf+momentum | 64 | 24 | +4.74% | **−2.09%** | 1.07 | **+2.91%** | 0.33 | +1.71% (0.50) | +6.25% (0.97) |

Every one of them fails on its own terms:

**Negative medians.** The typical firing loses money relative to the universe *before*
paying 1.83%. P(excess > cost) is 0.33–0.39, so roughly two trades in three are losers
after costs. The positive mean is an artefact of a right tail you cannot rely on.

**One day is the entire result.** Leave-one-day-out on the clustered series:

| combination | full mean (t) | drop best day (t) | drop worst day (t) |
|---|---|---|---|
| vol_exp+vol_conf+momentum+rel_str | +5.86% (1.27) | **+1.72% (0.79)** | +6.58% (1.38) |
| vol_conf+momentum+rel_str | +4.87% (1.10) | **+0.88% (0.44)** | +5.52% (1.20) |
| vol_exp+vol_conf+momentum | +4.74% (1.07) | **+0.73% (0.37)** | +5.35% (1.17) |
| vol_conf+momentum | +3.90% (0.96) | **+0.18% (0.10)** | +4.43% (1.06) |

The best day is the same one in all four: **2026-09-20, NILUSD, +96.8% 3-day excess**
(raw +104.4%). Remove that one asset-day and every top combination goes **net negative**
(+1.72% − 1.83% = −0.11%, and worse below it). Day-level hit rate for combination 1 is
**11 positive days out of 23** — a coin flip.

**The correction cascade** reproduces the R1/R2 pathology exactly:

| combination (h=3) | naive raw, per-event | demeaned, per-event | demeaned + clustered |
|---|---|---|---|
| vol_exp+vol_conf+momentum+rel_str | +11.72% (t=2.82) | +5.74% (t=1.65) | +5.86% (t=1.27) |
| vol_conf+momentum+rel_str | +10.79% (t=2.71) | +4.96% (t=1.48) | +4.87% (t=1.10) |
| vol_exp+vol_conf+momentum | +8.71% (t=3.52) | +2.20% (t=1.08) | +4.74% (t=1.07) |
| vol_conf+momentum | +8.07% (t=3.60) | +1.76% (t=0.97) | +3.90% (t=0.96) |

Roughly **half** the naive return is market beta (killed by demeaning) and most of the
remaining significance is pseudo-replication (killed by clustering). Anyone reporting the
first column would claim a +8% to +12% three-day edge at t > 2.7. There is no such edge.

---

## Out-of-sample split

Nothing passes. For the top 3, IS is flat-to-nothing (+1.71%, −0.03%, +1.71%, all |t| < 0.6)
and the apparent result lives entirely in OOS (+8.07%, +7.33%, +6.25%, all |t| ≈ 1.0–1.2,
none significant). That is the wrong shape for an edge — and it is the same shape you get
when one late outlier (2026-09-20) lands in the second half. Combinations whose IS half
contains almost no events are marked `n/a` for IS t.

The only combination with a respectable event count *and* consistent sign across halves is
`vol_conf+breakout` h=3 (118 events / 71 days, IS +3.76% t=1.55, OOS +2.65% t=1.39, NET
+1.45%, median +0.17%). It is the least bad candidate in the study. It still fails
Bonferroni by a wide margin (t=2.06 vs 3.461 required), its single-test permutation p is
0.048 — exactly what you expect to see 4 or 5 times when you run 93 tests — and its median
day is +0.17%, i.e. essentially zero before the 1.83% cost. It is not evidence.

---

## Power: could this study have said yes?

The MDE column is the mean excess required to reach t = 3.461. For the momentum/rel_str
subsets it is **+8% to +16% per 3-day trade**. No realistic crypto cross-sectional signal
delivers that. For the wide-sample subsets it is +4.4% to +5.5%, still implausible.

So the honest statement is twofold: (a) nothing passed, and (b) with a 120-day 4h window
and 10–26 clustered observations, **only an absurd effect could have passed**. This study
cannot distinguish "small real edge" from "no edge" for any subset containing `momentum`
or `rel_str`. It *can* say, with 690 days of data, that `vol_exp`, `vol_conf`, `breakout`
and their pairs carry nothing exploitable: their NET excess is negative at every horizon
except `vol_conf+breakout` h=2/h=3.

---

## Answer to Q1

**No combination produces a reliable positive net EV at a 1.83% round-trip cost.**

Ordering by NET excess ranks combinations by their exposure to a single September outlier,
not by skill. Confluence (requirement A2, "≥3 independent conditions") does *raise* mean
excess — the 3-, 4- and 5-condition subsets do sit at the top of the table — but it does so
by shrinking the sample to 10–26 days and concentrating it into fat-tailed events, and the
medians stay negative throughout. Confluence buys lottery tickets, not edge. That is a
direct empirical qualification of A2: it was derived from R1/R2 as "single signals carry no
edge", which remains true, but the inference that combinations therefore do carry edge is
**not supported**.

### Recommendation on tactical mode

**Tactical mode cannot be justified at a 1.83% round-trip cost on this evidence.** The
argument is not "the t-stats are too low" — it is structural:

1. The best achievable mean excess in the entire 93-cell surface, taken at face value and
   ignoring all corrections, is +5.86%/3d — and 70% of it is one asset-day.
2. The **median** trade in every top combination is negative *before* costs. A strategy
   whose median outcome is a loss needs the tail to pay for everything, and the tail here
   is 1 day in 23. On a ~$55 account, position-sizing that tail is not possible: you must
   take all 23 trades, paying 23 x 1.83% = 42% of turnover in costs, to catch one NILUSD.
3. The permutation test says the whole family underperforms random selection.

Tactical mode could only have positive EV if the cost side changes, not the signal side.
That makes **Q3 (can execution cost be structurally reduced below 4 legs?)** the binding
question, and I would stop spending effort on signal search until Q3 is answered. If cost
fell to ~0.8% (2 legs), `vol_conf+breakout` h=3 would show NET +2.48% with median +0.17% —
still not significant, but at least worth a properly powered re-test. At 1.83% there is
nothing to re-test.

### What would change my mind

- A combination with a **positive median** excess above cost and n_days ≥ 50 in the
  daily-only sample.
- Extending the 4h cache back 12+ months so the momentum/rel_str subsets get an MDE under
  ~4%, then re-running with the same corrections and finding survivors.
- Cost falling below ~1.0% round trip (Q3), which would move several cells from clearly
  negative to arguably marginal.

### Known weaknesses of this study

- 4h history is only 120 days; momentum and rel_str subsets are underpowered, and the
  120-day window happens to contain an unusual altcoin melt-up (mid-Aug to late-Sep 2026).
- Forward windows at h=2 and h=3 still overlap across *consecutive* days within a subset.
  Date clustering fixes same-day pseudo-replication but not serial overlap; the true
  standard errors are therefore somewhat **larger** than reported, which only strengthens
  the negative conclusion.
- Execution is assumed to be a flat 1.83% at the daily close with a perfect fill. Real
  tactical entries on volatility-expansion days would fill worse (registry R5).
- Condition thresholds were taken as given from the directive; I did not tune them, which
  is methodologically correct but means the study tests these five specific rules, not the
  general concepts behind them.

---

## Registry entry proposed

> **R6. Signal combinations (Q1).** *Rejected 2026-09-24.* All 31 subsets of
> {vol_expansion, volume_confirmation, momentum, breakout, relative_strength} x {1d,2d,3d},
> cross-sectionally demeaned and date-clustered, 32-asset universe. **0 of 93 tests survive
> Bonferroni (|t| ≥ 3.461); max |t| anywhere = 2.40.** A schedule-preserving permutation
> test gives family-wise p = 0.97 — the observed family is weaker than random selection.
> Top 3 by NET (+4.03%, +3.04%, +2.91%) all have negative medians and all collapse to
> ≈0 net when the single day 2026-09-20 (NILUSD, +96.8% 3d excess) is dropped. Confluence
> raises the mean by concentrating fat tails, not by adding skill. *Do not cite any
> positive NET figure from this study as evidence.*
