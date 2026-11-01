import pandas as pd

from app.market_analyzer.liquidity import (
    active_levels,
    liquidity_levels,
    swing_points,
)


def make_candles(highs, lows) -> pd.DataFrame:
    return pd.DataFrame({"high": highs, "low": lows})


# Seven candles, numbered 0 to 6, that we can check by hand.
HIGHS = [10, 12, 11, 15, 13, 14, 9]
LOWS = [8, 6, 7, 9, 5, 7, 6]


# ---------------------------------------------------------------
# Swing points
# ---------------------------------------------------------------

def test_swing_highs_match_hand_calculation():
    # left = 1, right = 1: a candle must beat the one before and the one after.
    # Candle 0: no candle before it         -> not a swing
    # Candle 1: 12 beats 10 and 11          -> swing high
    # Candle 2: 11 does not beat 12         -> no
    # Candle 3: 15 beats 11 and 13          -> swing high
    # Candle 4: 13 does not beat 15         -> no
    # Candle 5: 14 beats 13 and 9           -> swing high
    # Candle 6: no candle after it          -> not a swing
    result = swing_points(make_candles(HIGHS, LOWS), left=1, right=1)
    assert list(result["is_swing_high"]) == [
        False, True, False, True, False, True, False,
    ]


def test_swing_lows_match_hand_calculation():
    # A candle must have a LOWER low than the one before and the one after.
    # Candle 1: 6 is lower than 8 and 7     -> swing low
    # Candle 2: 7 is not lower than 6       -> no
    # Candle 3: 9 is not lower than 7       -> no
    # Candle 4: 5 is lower than 9 and 7     -> swing low
    # Candle 5: 7 is not lower than 5       -> no
    # Candles 0 and 6 are at the edges      -> not swings
    result = swing_points(make_candles(HIGHS, LOWS), left=1, right=1)
    assert list(result["is_swing_low"]) == [
        False, True, False, False, True, False, False,
    ]


def test_candles_near_the_edges_are_never_swings():
    # left = 2, right = 2: a candle must beat 2 candles on each side.
    # Only candle 3 (high 15) beats candles 1, 2, 4 and 5.
    # Candle 5 (high 14) has only one candle after it, so it can't be confirmed.
    result = swing_points(make_candles(HIGHS, LOWS), left=2, right=2)
    assert list(result["is_swing_high"]) == [
        False, False, False, True, False, False, False,
    ]


def test_equal_highs_are_not_swings():
    # Candles 1 and 2 both have a high of 12.
    # Neither is STRICTLY higher than the other, so neither is a swing high.
    candles = make_candles([10, 12, 12, 9], [8, 9, 9, 7])
    result = swing_points(candles, left=1, right=1)
    assert list(result["is_swing_high"]) == [False, False, False, False]


# ---------------------------------------------------------------
# Liquidity levels
# ---------------------------------------------------------------

def test_liquidity_levels_match_hand_calculation():
    # Same candles, left = 1, right = 1. The swings are:
    #   swing highs at candles 1 (12), 3 (15), 5 (14)
    #   swing lows  at candles 1 (6),  4 (5)
    # known_at = position + 1.
    # Which levels were swept?
    #   High 12 (candle 1): candle 3 has a high of 15, which is above 12 -> swept at 3
    #   Low 6   (candle 1): candle 4 has a low of 5, which is below 6   -> swept at 4
    #   High 15 (candle 3): later highs are 13, 14, 9 -> never swept
    #   Low 5   (candle 4): later lows are 7, 6       -> never swept
    #   High 14 (candle 5): later high is 9           -> never swept
    levels = liquidity_levels(make_candles(HIGHS, LOWS), left=1, right=1)

    assert levels["position"].tolist() == [1, 1, 3, 4, 5]
    assert levels["kind"].tolist() == [
        "swing_high", "swing_low", "swing_high", "swing_low", "swing_high",
    ]
    assert levels["price"].tolist() == [12.0, 6.0, 15.0, 5.0, 14.0]
    assert levels["known_at"].tolist() == [2, 2, 4, 5, 6]
    assert levels["swept_at"].isna().tolist() == [False, False, True, True, True]
    assert levels["swept_at"].iloc[:2].tolist() == [3, 4]


def test_active_levels_change_as_time_moves_forward():
    levels = liquidity_levels(make_candles(HIGHS, LOWS), left=1, right=1)

    # At candle 2: the first two levels are known and not yet swept.
    assert active_levels(levels, at=2)["price"].tolist() == [12.0, 6.0]

    # At candle 3: the high at 12 was just swept by candle 3. Only the low at 6 is left.
    assert active_levels(levels, at=3)["price"].tolist() == [6.0]

    # At candle 4: the low at 6 was swept by candle 4. The high at 15 is now known.
    assert active_levels(levels, at=4)["price"].tolist() == [15.0]

    # At candle 6: everything is known. The three levels never swept remain.
    assert active_levels(levels, at=6)["price"].tolist() == [15.0, 5.0, 14.0]


def test_levels_are_not_visible_before_they_are_confirmed():
    # The swing at candle 1 is only known at candle 2 (known_at = 2).
    # Looking at candle 0 or 1 must show nothing: that would be peeking ahead.
    levels = liquidity_levels(make_candles(HIGHS, LOWS), left=1, right=1)
    assert len(active_levels(levels, at=0)) == 0
    assert len(active_levels(levels, at=1)) == 0


def test_touching_a_level_exactly_is_not_a_sweep():
    # Candle 1 is a swing high at 12. Candle 3 reaches 12 exactly, but does not
    # go BEYOND it, so the level is NOT swept.
    candles = make_candles([10, 12, 11, 12, 9], [8, 9, 8, 9, 7])
    levels = liquidity_levels(candles, left=1, right=1)

    first_high = levels[(levels["kind"] == "swing_high") & (levels["position"] == 1)]
    assert first_high["swept_at"].isna().tolist() == [True]
