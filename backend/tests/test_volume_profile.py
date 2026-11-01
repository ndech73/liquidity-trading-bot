import pandas as pd
import pytest

from app.market_analyzer.volume_profile import value_area, volume_profile, vpoc


# Four candles that we can check by hand, with buckets 1.0 wide.
CANDLES = pd.DataFrame(
    {
        "low":    [10.2, 10.5, 11.1, 11.0],
        "high":   [10.8, 12.5, 11.9, 13.0],
        "volume": [40,   300,  50,   90],
    }
)


def make_profile(volumes) -> pd.DataFrame:
    """A profile with buckets 1.0 wide, starting at price 10."""
    count = len(volumes)
    return pd.DataFrame(
        {
            "price_low": [10.0 + i for i in range(count)],
            "price_high": [11.0 + i for i in range(count)],
            "volume": volumes,
        }
    )


# ---------------------------------------------------------------
# Volume profile
# ---------------------------------------------------------------

def test_profile_matches_hand_calculation():
    # Candle 0: touches bucket 10 only          -> 40 in bucket 10
    # Candle 1: touches buckets 10, 11, 12      -> 300 / 3 = 100 in each
    # Candle 2: touches bucket 11 only          -> 50 in bucket 11
    # Candle 3: touches buckets 11, 12, 13      -> 90 / 3 = 30 in each
    #
    # Bucket 10: 40 + 100       = 140
    # Bucket 11: 100 + 50 + 30  = 180
    # Bucket 12: 100 + 30       = 130
    # Bucket 13: 30             = 30
    profile = volume_profile(CANDLES, bin_size=1.0)

    assert profile["price_low"].tolist() == pytest.approx([10, 11, 12, 13])
    assert profile["price_high"].tolist() == pytest.approx([11, 12, 13, 14])
    assert profile["volume"].tolist() == pytest.approx([140, 180, 130, 30])


def test_profile_keeps_all_the_volume():
    # Spreading volume around must never create or lose any of it.
    # 40 + 300 + 50 + 90 = 480
    profile = volume_profile(CANDLES, bin_size=1.0)
    assert profile["volume"].sum() == pytest.approx(480)


def test_price_exactly_on_a_bucket_edge_goes_in_the_upper_bucket():
    # Low 12.5 is in bucket 12. High 13.0 is exactly on the edge,
    # so it counts as bucket 13. Two buckets -> 5 volume in each.
    candles = pd.DataFrame({"low": [12.5], "high": [13.0], "volume": [10]})
    profile = volume_profile(candles, bin_size=1.0)

    assert profile["price_low"].tolist() == pytest.approx([12, 13])
    assert profile["volume"].tolist() == pytest.approx([5, 5])


def test_forex_sized_prices_land_in_the_right_buckets():
    # Buckets of 1 pip (0.0001). Low 1.1000 and high 1.1002 touch
    # buckets 1.1000, 1.1001 and 1.1002 -> 30 / 3 = 10 in each.
    candles = pd.DataFrame({"low": [1.1000], "high": [1.1002], "volume": [30]})
    profile = volume_profile(candles, bin_size=0.0001)

    assert len(profile) == 3
    assert profile["price_low"].iloc[0] == pytest.approx(1.1000)
    assert profile["volume"].tolist() == pytest.approx([10, 10, 10])


def test_vpoc_matches_hand_calculation():
    # The fullest bucket is 11 to 12 (volume 180). Its middle is 11.5.
    profile = volume_profile(CANDLES, bin_size=1.0)
    assert vpoc(profile) == pytest.approx(11.5)


def test_vpoc_tie_picks_the_lowest_price():
    # Two candles with the same volume, far apart. Bucket 11 stays empty.
    # Buckets 10 and 12 are tied at 50, so the lower one (10 to 11) wins.
    candles = pd.DataFrame(
        {"low": [10.1, 12.1], "high": [10.9, 12.9], "volume": [50, 50]}
    )
    profile = volume_profile(candles, bin_size=1.0)

    assert profile["volume"].tolist() == pytest.approx([50, 0, 50])
    assert vpoc(profile) == pytest.approx(10.5)


def test_empty_candles_give_an_empty_profile_and_no_vpoc():
    empty = pd.DataFrame({"low": [], "high": [], "volume": []})
    profile = volume_profile(empty, bin_size=1.0)

    assert profile.empty
    assert vpoc(profile) is None


def test_bin_size_must_be_bigger_than_zero():
    with pytest.raises(ValueError):
        volume_profile(CANDLES, bin_size=0)


# ---------------------------------------------------------------
# Value area
# ---------------------------------------------------------------

def test_value_area_matches_hand_calculation():
    # Profile volumes: [140, 180, 130, 30]. Total 480. Target = 70% = 336.
    # Start at the fullest bucket (11 to 12): collected 180.
    # Below is 140, above is 130 -> take the one below. Collected 320.
    # 320 is still under 336, and there is nothing below bucket 10 anymore.
    # Take the one above (130). Collected 450. Enough!
    # The zone covers buckets 10, 11 and 12 -> from 10 up to 13.
    profile = volume_profile(CANDLES, bin_size=1.0)
    assert value_area(profile, share=0.70) == pytest.approx((10.0, 13.0))


def test_value_area_small_share_is_just_the_vpoc_bucket():
    # Target = 30% of 480 = 144. The fullest bucket alone has 180,
    # which is already enough. The zone is just bucket 11 to 12.
    profile = volume_profile(CANDLES, bin_size=1.0)
    assert value_area(profile, share=0.30) == pytest.approx((11.0, 12.0))


def test_value_area_full_share_covers_everything():
    # Target = 100% of 480 = 480. Every bucket is needed:
    # 180 + 140 + 130 + 30 = 480 -> the zone runs from 10 up to 14.
    profile = volume_profile(CANDLES, bin_size=1.0)
    assert value_area(profile, share=1.0) == pytest.approx((10.0, 14.0))


def test_value_area_tie_goes_to_the_lower_side():
    # Volumes: [50, 100, 50]. Total 200. Target = 140.
    # Start at the middle bucket (100). Below is 50, above is 50: a tie,
    # so the lower bucket is added. Collected 150, which is enough.
    # The zone covers buckets 10 and 11 -> from 10 up to 12.
    profile = make_profile([50, 100, 50])
    assert value_area(profile, share=0.70) == pytest.approx((10.0, 12.0))


def test_value_area_uses_other_side_when_one_side_runs_out():
    # Volumes: [60, 20, 20]. Total 100. Target = 70.
    # Start at the fullest bucket 10 to 11 (60). Nothing is below it.
    # Take the bucket above (20). Collected 80, which is enough.
    # The zone covers buckets 10 and 11 -> from 10 up to 12.
    profile = make_profile([60, 20, 20])
    assert value_area(profile, share=0.70) == pytest.approx((10.0, 12.0))


def test_value_area_holds_at_least_the_share_of_volume():
    # Whatever the zone is, the volume inside it must reach the target.
    profile = volume_profile(CANDLES, bin_size=1.0)
    low, high = value_area(profile, share=0.70)

    inside = profile[(profile["price_low"] >= low) & (profile["price_high"] <= high)]
    assert inside["volume"].sum() >= 0.70 * profile["volume"].sum()


def test_value_area_with_no_volume_gives_none():
    empty = pd.DataFrame({"low": [], "high": [], "volume": []})
    assert value_area(volume_profile(empty, bin_size=1.0)) is None

    # Buckets exist, but nobody traded in them.
    assert value_area(make_profile([0, 0, 0])) is None


def test_value_area_share_must_be_between_zero_and_one():
    profile = make_profile([50, 100, 50])
    with pytest.raises(ValueError):
        value_area(profile, share=0)
    with pytest.raises(ValueError):
        value_area(profile, share=1.5)