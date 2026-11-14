# RULES_v2.md - Final test of the H4 false-breakout model

Written: 2026-11-12, BEFORE the final run.
Once this file is committed, nothing in sections 1-8 may change.
The only allowed edits are new dated lines in the Test Log (section 9)
and the Changelog (section 10).
RULES.md stays as it is. It is the history of ideas 1-9.

## 1. Why this file exists

The H4 run of idea 9 almost passed. It failed only Test B, by 0.0041 ATR.
But the way it was measured had problems (section 2). Instead of
patching the old result, we fix the measuring tools, write the pass marks
down again (stricter), and run ONE final time.

## 2. Honest record of what went wrong before

1. NZDUSD data exists but was left out of ideas 8 and 9. Rule 7 of
   RULES.md forbids dropping a pair.
2. The H4 run used a new exit (z = 0, stop 1.5 ATR, time limit) instead
   of the fixed 8-candle exit in RULES.md, after the H1 run had failed.
3. Idea 9 was run three ways (H1 fixed exit, H1 dynamic exit, H4 dynamic
   exit), but all were logged as k = 9, and the H1 dynamic result was
   never logged. The true k of the H4 run was at least 11.
4. The exit checked "target reached?" BEFORE "stop hit?". A candle that
   touched the stop and then closed at the target was booked as a win.
5. Test C flipped the direction of trades but kept their price moves.
   With stop and target exits, a flipped trade would have exited at a
   different place.
6. The scripts labelled weeks by number only (1-53), with no year, so the
   whole-weeks resampling in Test A mixed three years together.
7. The cost used the WORST M15 spread inside the H4 candle, not the
   spread at the moment of entry.
8. On H4 the rollover blackout (hours 21-23) never switches on, because
   H4 candles start at hours 0, 4, 8, 12, 16 and 20.

Problems 4 to 7 are measuring problems. They are fixed in sections 4 and 5.
The strategy itself is NOT changed. Problem 8 is a property of the entry
code, which is not changed. So we do not rely on the blackout: every entry
simply pays the real spread of its entry moment.

## 3. The model being tested (frozen)

- Timeframe: H4 only, built from complete M15 candles (16 per H4 candle,
  incomplete ones are dropped). H1 is closed and is NOT tested here.
- Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, NZDUSD, EURJPY. All six.
  None may be dropped.
- Entry: generate_trap_signals in app/entry/entry_rules.py with
  lookback 6 and max_cost_ratio 0.15, exactly as committed.
- Exit: check_stop_loss_exit and check_target_exit from
  app/exit/exit_rules.py. Stop = 1.5 x ATR (ATR of the signal candle).
  z-score = rolling_statistics(close, window 6). Time limit = 6 candles
  after the entry candle.
- The run is only allowed if app/entry, app/exit and app/market_analyzer
  have no uncommitted changes.
- Data: development data only (before 2025-09-14), using the default
  load_candles(). The hold-out is not touched.

## 4. How one trade is measured

1. The signal is made at the close of candle i. Entry is at the OPEN of
   candle i+1.
2. Starting at the entry candle, every candle is checked in this order:
   a. Gap: if the candle does not follow the last one back-to-back
      (weekend or missing data), exit at that candle's open.
   b. Stop FIRST: if the candle's open is already past the stop price,
      exit at the open (this is worse than the stop). Otherwise, if the
      candle's high or low touches the stop price, exit at the stop price.
   c. Target: if z has reached 0 at the close, exit at the close.
   d. Time limit: if 6 candles have passed since the entry candle,
      exit at the close.
3. Overlap: while a trade is open on a pair, new signals on that pair are
   skipped.
4. Outcome = (exit price - entry price) x direction / ATR(14) at the
   signal candle. The unit is ATR.
5. Cost = the spread of the FIRST M15 candle inside the entry H4 candle
   (what you pay when you enter at the open), in ATR. One spread per
   trade. The old worst-spread cost is printed beside it for information
   only. It is never used for a pass mark.
6. The week label includes the year.

## 5. The tests (development data only). k = 12

k = 12 because: the old sweep study (1) + ideas 2 to 8 (7) + three runs of
idea 9 (3) = 11 ideas already tried, and this final run is the 12th.

| Test | Question | Pass mark |
|------|----------|-----------|
| A. Pattern exists | Is the average outcome, before costs, above zero? | The (100 - 5/12)% = 99.58% range, made by resampling whole weeks (with year) 20,000 times, is entirely above zero |
| B. Beats costs | Is the outcome bigger than the cost, with a safety margin? | Average outcome minus 1.25 x average cost is above zero |
| C. Beats random | Does it beat random directions? | For every trade, also work out the result if it had gone the other way, with the same exit rules. Run 10,000 random-direction runs (coin flip per trade). The real average must beat at least 99.92% of them (9,992 of 10,000) |
| D. Repeats | Does it hold across pairs and time? | Average outcome above zero (before costs) in at least 4 of 6 pairs AND in at least 70% of calendar quarters |
| E. Enough data | Are there enough trades? | At least 300 trades in total |
| F. Hold-out | Does it hold on unseen data? | Run ONCE. Before-cost average above zero, at least half the size it had on development data, AND average outcome minus 1.25 x average cost above zero |

The 25% safety margin in B and F exists because the demo spread is not
the real-account spread, and stops fill worse than their price in fast
markets.

## 6. Checks before the numbers count

The run is INVALID if any of these fails:
- The last candle used is before 2025-09-14, and holdout_access.log has
  no new line.
- All six pairs have trades.
- No two trades overlap on the same pair, and every entry is exactly one
  candle after its signal.
- The tests of the new simulator pass, including a deliberate-break check
  that proves the stop-first test can catch a wrong order.
- The number of trades where the stop and the target were both triggered
  on the exit candle is printed.

If a run is invalid, only the failed check may be fixed, the fix is
written in the Test Log, and the fix must not be chosen by looking at
which way it moves the result.

## 7. Verdict

- Pass A, B, C, D and E -> run Test F once.
- Pass F too -> "edge candidate". This is NOT proof: the development data
  has been looked at 11 times already. The next step is a forward test on
  the demo account for at least 3 months, with real-account spreads
  checked, before any real money.
- Fail any test -> "this idea is closed". No new exit, no dropped pair,
  no re-run. Any new idea starts at k = 13.

## 8. Not allowed

- Changing any mark, setting, pair, exit or cost rule after seeing a result.
- Running the model on H1 or any other timeframe under this file.
- Looking at the hold-out before Test F, or running Test F twice.
- Leaving a run, valid or invalid, out of the Test Log.

## 9. Test Log

| Date | Idea | k | A | B | C | D | E | F | Notes |
|------|------|---|---|---|---|---|---|---|-------|
| 2026-11-12 | H4 false-breakout trap (24h fence, rho<0, toll guard, stop-first, spread_first) | 12 | FAIL | FAIL | FAIL | PASS | PASS | - | k=12, 6 pairs H4. Gross +0.0517 ATR, cost_first 0.0622 ATR, margin_net -0.0260 ATR. 19 stop-first corrections. Verdict: NO EDGE FOUND: failed A, B, C |

## 10. Changelog

- 2026-11-12: File created before the final run.
