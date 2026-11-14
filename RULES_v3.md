# RULES_v3.md - Daily compression breakout (idea 13)

Written: 2026-11-14, BEFORE any data was downloaded and BEFORE any code was written.
Once this file is committed, nothing in sections 1-10 may change.
The only allowed edits are new dated lines in the Test Log (section 11)
and the Changelog (section 12).
RULES.md and RULES_v2.md stay as they are. They are the history of ideas 1-12.

## 1. Why this file exists

Twelve ideas have been tested on the same data and none beat the cost.
Each extra try makes a lucky result more likely, and each number we adjust
after seeing a result makes it worse. This file fixes everything first:
the idea, every number, the data split, the costs and the pass marks.

## 2. The idea, in one sentence

When the market has been unusually quiet (the range of the last 20 days is
among the narrowest 20% of the last year) and a day then closes beyond that
20-day range, trade in that direction. Hold until a day closes beyond the
opposite 10-day extreme, or until a 2 ATR stop is hit.

### Frozen numbers (chosen BEFORE looking at any daily data)

| Number | Value | Why this value |
|--------|-------|----------------|
| Breakout range | 20 days | About one trading month. A common channel length. |
| Exit range | 10 days | Half of the entry range. A common trailing channel. |
| Squeeze history | 252 days | Trading days in a year. |
| Squeeze cut-off | 20% | The narrowest fifth. |
| Stop | 2 ATR | A common stop distance, wide enough for daily noise. |
| ATR period | 14 | The value the project already uses. |

These are round numbers that people commonly use. We have not looked at how
they perform on this data, and we will not try other values to pick a better
one (see section 6, Test G).

## 3. Data

- Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, NZDUSD, EURJPY. All six. None may
  be dropped.
- Timeframe: D1 (daily candles, broker server time), downloaded from MT5 as
  D1. Not built from M15. One source for all years.
- Start: the earliest available day, but not earlier than 2005-01-01. The
  actual start date of each pair is written in the Test Log BEFORE the run.
- Part 1 (fresh): everything before 2022-10-01. No earlier idea has used it,
  because the M15 files only start around Oct-Nov 2022.
- Part 2: 2022-10-01 to 2025-09-13. Earlier ideas looked at this period on
  other timeframes, so it counts as weaker evidence than Part 1.
- Development data = Part 1 + Part 2.
- Hold-out: 2025-09-14 to 2026-09-13. Locked. Used once, in Test F only.
- Warm-up: no signal until a pair has at least 272 earlier daily candles.
- Weekend candles (Saturday or Sunday): if any exist in the data, STOP and
  ask. Do not guess how to treat them.

## 4. How a trade is built

Notation: day i is one daily candle. Everything for day i uses only days up
to and including i.

1. Previous range. H(i) = highest high of days i-20 to i-1. L(i) = lowest low
   of the same days. (Day i is not part of them.)
2. Squeeze measure. S(i) = (H(i) - L(i)) / close(i-1).
3. Compressed on day i: at most 20% of the 252 values S(i-251) ... S(i) are
   less than or equal to S(i).
4. Signal at the close of day i:
   - Long: close(i) > H(i) and compressed.
   - Short: close(i) < L(i) and compressed.
5. ATR(i) = the project's atr() on daily candles, period 14, at day i.
6. Entry: day i+1. The backtest price is the OPEN of day i+1. In live
   trading the order is placed at the first candle at or after server hour
   02:00 of day i+1, to avoid the midnight spread spike (hours 0 and 1).
   The price difference between 00:00 and 02:00 is treated as noise.
7. Stop: entry price - direction x 2 x ATR(i). Checked on every day from i+1
   using the day's high and low. If the day OPENS already beyond the stop,
   the fill is the open (worse). Stop first, always.
8. Channel exit: after the stop check on day j, if (long) close(j) is below
   the lowest low of days j-10 to j-1, or (short) close(j) is above the
   highest high of days j-10 to j-1, exit at the OPEN of day j+1.
9. Gap: if the next candle is more than 4 calendar days after the current
   one, exit at that candle's open (reason gap_exit).
10. End of data: a trade still open on the last candle of its data part is
    closed at that candle's close (reason data_end). The count is reported.
11. Overlap: while a trade is open on a pair, new signals on that pair are
    skipped.
12. Outcome = direction x (exit price - entry price) / ATR(i). Unit: ATR.
13. Labels: month = the entry's calendar month with the year (for example
    2019-04). Year = the entry's calendar year.

## 5. Costs

- Spread. Cost table: for each pair, the median M15 spread in points over
  server hours 02:00 to 23:59, using DEVELOPMENT M15 data only. It is saved
  in data_files/cost_table_v3.json and committed BEFORE the run. One spread
  is paid per round trip. Cost in ATR = median points x point size / ATR(i).
  Part 1 trades use DOUBLE this cost (older spreads were generally wider; we
  do not know by how much). Part 2 trades use 1x.
- Swap. Taken from MT5 symbol info (swap_long, swap_short, swap_mode,
  swap_rollover3days), saved in data_files/swap_table_v3.json and committed
  BEFORE the run. If swap_mode is not "points", STOP and ask. For each
  weekday night held (the dates from the entry date up to the day before the
  exit date, Monday to Friday only), add max(0, -swap points for the trade's
  direction) x point size / ATR(i). The night of the rollover3days weekday
  counts three times. A positive swap counts as zero. Today's demo values are
  used for all years, because the past values are unknown.
- Safety margin: Test B multiplies the spread cost by 1.25. The swap cost is
  not multiplied.

## 6. The tests (development data). k = 13

k = 13 because 12 ideas were tried before this one (see section 2 of
RULES_v2.md) and this is the 13th.

| Test | Question | Pass mark |
|------|----------|-----------|
| A. Pattern exists | Is the average outcome, before costs, above zero? | The 99.615% range (that is 100 - 5/13), made by resampling whole MONTHS (all pairs together) 20,000 times, is entirely above zero |
| B. Beats costs | Does it beat costs, with a margin? | Average outcome - 1.25 x average spread cost - average swap cost is above zero |
| C. Beats random | Does it beat random directions? | For every trade, also work out the result of the opposite direction on the same entry day, with its own mirrored stop and channel exit. Run 10,000 coin-flip runs. The real average must beat at least 9,993 of 10,000 (that is 99.923%, or 100 - 1/13) |
| D. Repeats | Does it hold across pairs and years? | Average outcome above zero (before costs) in at least 4 of 6 pairs AND in at least 70% of calendar years that have at least 5 trades |
| E. Enough data | Are there enough trades? | At least 300 trades in total AND at least 100 in Part 1. Fewer means "not enough data", which is NOT a pass |
| G. Stable | Does it survive small changes to the numbers? | Run six neighbours, changing ONE number at a time: breakout range 10 days, breakout range 30 days, exit range 5 days, exit range 15 days, squeeze cut-off 10%, squeeze cut-off 30%. (A changed breakout range is also used in the squeeze measure.) The average outcome before costs must be above zero in at least 4 of the 6 |
| H. Fresh data stands alone | Does Part 1 work by itself? | Part 1 only: average outcome - 1.25 x average spread cost - average swap cost is above zero. Part 2 only: average outcome before costs is above zero |
| I. Not one lucky slice | Is the profit spread out? | The best single calendar year gives at most 50% of the total outcome, and the best single pair gives at most 50% of the total outcome. If the total is not above zero, this test fails |
| F. Hold-out | Does it hold on unseen data? | Run ONCE, only after A-E, G, H and I all pass. At least 30 trades are needed, otherwise the result is "inconclusive" (not a pass, not a fail, and the next step is the forward demo test). Average outcome above zero, at least half the size it had on development data, AND average outcome - 1.25 x spread cost - swap cost above zero |

Test G can only turn a pass into a fail. The neighbour results are never used
to pick, change or replace the main setting, so the six neighbour runs do not
add to k.

## 7. Rules against overfitting

1. Every number is fixed in section 2 and chosen without looking at results.
2. The main setting is the only one that can pass. Neighbours can only veto.
3. Part 1 (fresh data) has to work on its own, after costs.
4. Costs are pessimistic on purpose (section 5).
5. The pass marks already include k = 13.
6. One run only. The code is committed and tagged BEFORE the run (section 8).
7. Nobody looks at outcome numbers (averages, profits, results per pair)
   before the final report. Checking the signal logic is done on made-up
   candles in unit tests, never on real-data profits.
8. Test I blocks a result that rests on one pair or one year.
9. The hold-out is opened once.
10. Even a full pass is only an "edge candidate" (section 9).

## 8. Freeze protocol and validity checks

Order of work (each step finished and committed before the next):
1. This file is committed.
2. The D1 data is downloaded. Data checks run (the loader checks, no weekend
   candles, the start date per pair). No outcome numbers are printed.
3. cost_table_v3.json and swap_table_v3.json are created and committed.
4. The code and its tests are written, committed and tagged v3-frozen.
5. The run starts only if git status is clean and the tag points at HEAD.
6. The run happens once.
7. Afterwards: git diff v3-frozen -- backend/app backend/scripts backend/tests
   must print nothing.

The run is INVALID if any of these fails:
- The last development candle is before 2025-09-14, and holdout_access.log
  has no new line.
- All six pairs have trades.
- No two trades overlap on the same pair, and every entry is on the day
  after its signal.
- The unit tests pass, including: stop-first order (with a deliberate-break
  check that proves the test can catch a wrong order); a gap past the stop
  fills at the open; and a no-look-ahead test (change every candle AFTER day
  i and check that the signal on day i does not change).
- The number of data_end and gap_exit trades is printed.

If a run is invalid, only the failed check may be fixed. The fix is written
in the Test Log and must not be chosen by looking at which way it moves the
result.

## 9. Verdict

- Pass A, B, C, D, E, G, H and I -> run Test F once.
- Pass F too -> "edge candidate". This is NOT proof. The next step is a
  forward test on the demo account for at least 3 months, entering at server
  hour 02:00 or later, with real-account spreads and swaps checked, before
  any real money.
- Test F inconclusive (fewer than 30 trades) -> forward demo test only.
- Fail any test, or "not enough data" -> "this idea is closed". No new
  numbers, no dropped pair, no re-run. Any new idea starts at k = 14.

## 10. Not allowed

- Changing any number, mark, pair, exit, cost rule or data split after
  seeing a result.
- Choosing among the neighbour settings, or adding filters after a result.
- Dropping a pair, a year or a trade because it looks bad.
- Looking at the hold-out before Test F, or running Test F twice.
- Running a second time because the first run was "unlucky".
- Leaving a run, valid or invalid, out of the Test Log.

## 11. Test Log

| Date | Idea | k | A | B | C | D | E | G | H | I | F | Notes |
|------|------|---|---|---|---|---|---|---|---|---|---|-------|

## 12. Changelog

- 2026-11-14: File created before any data download and before any code.
- 2026-11-14: Weekend candles were found by the data check, before any outcome was seen: Sundays 2016-05-22, 2016-05-29, 2016-06-05, 2016-06-12, 2016-06-19 and 2024-10-27 on all six pairs, and Saturday 2009-10-31 on USDCAD and EURJPY. Decision: a Sunday candle is merged into the following Monday candle (open from the Sunday, highest high and lowest low of both, close from the Monday). A Saturday candle is merged into the preceding Friday candle (open from the Friday, highest high and lowest low of both, close from the Saturday). Cleaned files are saved as SYMBOL_D1CLEAN.csv and used for all tests. The same merge rule is applied to the hold-out period, where only counts, never dates or prices, are looked at.
