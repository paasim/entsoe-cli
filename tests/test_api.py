from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from requests import HTTPError

from entsoe_cli import get_prices

FI = ZoneInfo("Europe/Helsinki")

HOUR_SECONDS = 3600
QUARTER_SECONDS = 900


def test_invalid_range():
    """Invalid range results in an error"""
    start = datetime.now(tz=FI)
    with pytest.raises(ValueError, match="end time must be greater"):
        get_prices(start, start)


def test_missing_apikey():
    """No security token results in an error"""
    start = datetime.now(tz=FI)
    with pytest.raises(ValueError, match="security token missing"):
        get_prices(start, start + timedelta(hours=1), token=None)


def test_invalid_apikey():
    """Invalid security token results in an error"""
    start = datetime.now(tz=FI)
    prices = get_prices(start, start + timedelta(hours=1), token="invalid_apikey")  # noqa: S106
    with pytest.raises(HTTPError):
        list(prices)


def test_get_prices_one():
    """get_prices works for single price"""
    start_time = datetime(2024, 12, 20, 5, tzinfo=FI)
    end_time = datetime(2024, 12, 20, 6, tzinfo=FI)
    prices = list(get_prices(start_time, end_time))
    price_exp = 10.99
    assert len(prices) == 1
    assert prices[0].start_time == start_time
    assert prices[0].end_time == end_time
    assert prices[0].price == price_exp


def test_get_prices_long_period():
    """get_prices works for a longer period"""
    start_time = datetime(2024, 1, 20, tzinfo=FI)
    end_time = datetime(2024, 6, 20, tzinfo=FI)
    prices = list(get_prices(start_time, end_time))
    # expected number or prices
    len_exp = (end_time.timestamp() - start_time.timestamp()) // HOUR_SECONDS
    assert len(prices) == len_exp
    # no duplicates
    assert len(prices) == len({p.start_time for p in prices})
    # in order
    assert [p.start_time for p in prices] == sorted(p.start_time for p in prices)


def test_quarterly_prices():
    """get_prices works for a quarterly prices, even if the frequqnce changes"""
    start_time = datetime(2025, 10, 1, tzinfo=FI)
    end_time = datetime(2025, 10, 2, tzinfo=FI)
    prices = list(get_prices(start_time, end_time))
    # first price is hourly, next are quarterly
    assert (prices[1].start_time - prices[0].start_time).total_seconds() == HOUR_SECONDS
    for i in range(1, len(prices) - 1):
        diff = prices[i + 1].start_time - prices[i].start_time
        assert diff.total_seconds() == QUARTER_SECONDS
    # last price is for the last quarter
    assert (end_time - prices[-1].start_time).total_seconds() == QUARTER_SECONDS
    # no duplicates
    assert len(prices) == len({p.start_time for p in prices})
    # in order
    assert [p.start_time for p in prices] == sorted(p.start_time for p in prices)
