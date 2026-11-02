# RULES.md - Rules for deciding if the model has an edge

Written: 2026-11-02, BEFORE any edge test was run.
Do not change anything in sections 1-7 after a result has been seen.
The only allowed edits are new dated lines in the Test Log (section 8)
and the Changelog (section 9).

## 1. Why this file exists

Random results sometimes look good by luck. If we choose the pass marks
after seeing a result, we will (without meaning to) choose marks that
the result passes. So the marks are fixed here, first.

## 2. Data

- Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, NZDUSD, EURJPY
- Timeframe: M15
- Source: FBS-Demo via MT5, saved in backend/data_files/
- Development data: everything up to and including 2025-09-13.
  All building, tuning and testing happens here.
- Hold-out data: 2025-09-14 to 2026-09-13.
  Nobody looks at it, plots it, or tunes on it. It is used exactly ONCE
  (Test F), at the very end. Candles after 2026-09-13 are ignored.
- Times are broker server time, not UTC. Convert before any session rule.

## 3. Fixed settings (chosen before testing)

- Signal: a rule that, at the close of a candle, says long, short or
  nothing, using only candles up to and including that one.
- Entry: the open of the NEXT candle.
- Primary horizon: 8 candles (2 hours) after entry.
- Outcome of one trade: price change from entry to the close 8 candles
  later, in the signal's direction, divided by ATR(14) at the signal
  candle. The unit is ATR. Other horizons may be reported, but they are
  never used to pass a test.
- Overlap: if a signal fires on a pair while an earlier trade on that
  pair is still open (within 8 candles), the new signal is skipped.
- Cost: the spread recorded in the data at the entry candle, converted
  to ATR. One spread is paid per round trip. The demo account has no
  commission. Real-account costs must be re-checked before real money.

## 4. The tests (all on development data only)

k = the number of ideas tested on this data, including the current one.

| Test | Question | Pass mark |
|------|----------|-----------|
| A. Pattern exists | Is the average outcome, before costs, above zero? | The interval of (100 - 5/k)% (95% when k = 1, made by resampling whole weeks) is entirely above zero |
| B. Beats costs | Is the average outcome bigger than the average cost? | Average outcome minus average cost is above zero |
| C. Beats random | Does the real average beat random directions on the same entries? | Beats at least (100 - 1/k)% of 1,000 random-direction runs (use 10,000 runs when k is above 10) |
| D. Repeats | Does it hold across pairs and time? | Average above zero (before costs) in at least 4 of 6 pairs AND in at least 70% of calendar quarters |
| E. Enough data | Are there enough trades to trust the numbers? | At least 300 trades in total. Fewer means "not enough data", which is NOT a pass |
| F. Hold-out | Does it hold on data it has never seen? | Run once. Average outcome above zero, and at least half the size it had on development data |

## 5. Verdict

- Pass A, B, C, D and E on development data -> run Test F once.
- Pass F too -> "edge candidate". This is NOT proof. The next step is a
  forward test on the demo account for at least 3 months before any
  real money.
- Fail any test -> "no edge found for this idea". We change the idea,
  not just the settings, and the idea counter goes up.

## 6. The many-ideas rule

Every extra idea or setting we try makes a lucky result more likely.
So the count k goes into the pass marks above.

- Ideas already tested on this same data before this file: 1
  (the M15 liquidity-sweep reversal event study, Sep 2022 to Sep 2025,
  which found no better than chance).
- So the next idea tested is idea number 2 (k = 2).
- Every different idea, and every different setting we compare, counts
  as one more toward k.
- Every run is written in the Test Log, including the failures.

## 7. Not allowed

- Changing a pass mark, the horizon, the data split or the cost rule
  after seeing a result.
- Dropping a pair, a quarter or a trade because it looks bad.
- Looking at the hold-out data before Test F, or re-running Test F.
- Tuning any setting on the hold-out data.
- Leaving a failed run out of the Test Log.

## 8. Test Log

| Date | Idea | k | A | B | C | D | E | F | Notes |
|------|------|---|---|---|---|---|---|---|-------|
| 2026-11-02 | Failed auction: sweep swing low & close > VAL (long); sweep swing high & close < VAH (short) | 2 | PASS | FAIL | PASS | PASS | PASS | - | Pattern exists (+0.061 ATR, 6/6 pairs, 92% Qs), but 0.253 ATR spread cost eats the edge. Failed B. |
| 2026-11-02 | Session-filtered failed auction: 10:00-19:00 server time, sweep low & close > VAL (long); sweep high & close < VAH (short) | 3 | FAIL | FAIL | FAIL | FAIL | PASS | - | Cost dropped to 0.157 ATR, but gross outcome dropped to +0.035 ATR (EURJPY negative). Failed A, B, C, D. |
| 2026-11-02 | Major structural failed auction: sweep major swing low (left=10, right=10) & close > VAL (long); sweep major swing high (left=10, right=10) & close < VAH (short) | 4 | FAIL | FAIL | FAIL | PASS | PASS | - | Pattern stronger in USD majors (+0.10 to +0.14 ATR, D passed), but NZDUSD/EURJPY negative and spread costs (0.233 ATR) exceed outcome. Failed A, B, C. |
| 2026-11-02 | Session momentum breakout: 10:00-19:00 server time, sweep major swing high (left=10, right=10) & close > VAH (long); sweep major swing low & close < VAL (short) | 5 | FAIL | FAIL | FAIL | FAIL | PASS | - | Strong positive net edge on EURJPY (+0.055 ATR) and GBPUSD (+0.022 ATR), but aggregate outcome (+0.040 ATR) fails cost (0.144 ATR) and quarters 67% vs 70%. Failed A, B, C, D. |
| 2026-11-02 | Asian range sweep at London open: 08:00-12:00 server time, sweep Asian low & close > low (long); sweep Asian high & close < high (short) | 6 | running | running | running | running | running | - | Registered before execution. |





## 9. Changelog

- 2026-11-02: File created before any test was run.
