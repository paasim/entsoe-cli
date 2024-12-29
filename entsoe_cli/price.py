"""Methods for parsing the price elements."""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Self

from .enums import Resolution, Unit


@dataclass
class Price:
    """Energy price."""

    start_time: datetime
    resolution: Resolution
    price: float
    unit: Unit

    @classmethod
    def parse(
        cls, point: ET.Element, start_time: datetime, resolution: Resolution, unit: Unit
    ) -> Self:
        """Parse a Point element.

        In addition to the actual price, the point element contains a position
        which is combined with start_time and resolution (of the time series)
        to get the actual start time.
        """
        pos = point.findtext("{*}position")
        price = point.findtext("{*}price.amount")
        if pos is None or price is None:
            msg = "invalid price"
            raise ValueError(msg)
        start_time += resolution.to_timedelta() * (int(pos) - 1)
        return cls(start_time, resolution, float(price), unit)

    @property
    def end_time(self) -> datetime:
        """Return end time for the price."""
        return self.start_time + self.resolution.to_timedelta()

    def __str__(self) -> str:
        """Return string representation for the price."""
        end = self.start_time + self.resolution.to_timedelta()
        return f"{self.start_time} -- {end}: {self.price} {self.unit}"


def _prices_until(
    start_time: datetime, end: datetime, res: Resolution, price: float, unit: Unit
) -> Iterator[Price]:
    while start_time < end:
        yield Price(start_time, res, price, unit)
        start_time += res.to_timedelta()


def interpolate_prices(
    prices: Iterator[Price],
    start_time: datetime,
    end_time: datetime,
) -> Iterator[Price]:
    """Interpolate prices.

    The data might not contain repeated values. This means that the price
    needs to be repeated if the difference in position (= a multiplier for
    resolution) between two consecutive records is greater than one.
    """
    price0 = None
    # find first price
    for price in prices:
        price0 = price
        if price.start_time >= start_time:
            break
    if price0 is None or not (start_time <= price0.start_time < end_time):
        return

    (res, unit) = (price0.resolution, price0.unit)
    (prev_end, prev_price) = (price0.end_time, price0.price)
    yield from _prices_until(start_time, price0.start_time, res, prev_price, unit)
    yield price0

    for price in prices:
        yield from _prices_until(
            prev_end, min(price.start_time, end_time), res, prev_price, unit
        )
        if price.start_time >= end_time:
            return
        yield price
        (prev_end, prev_price) = (price.end_time, price.price)

    yield from _prices_until(prev_end, end_time, res, prev_price, unit)


def parse_time_series(
    time_series: ET.Element, start_time: datetime, end_time: datetime
) -> Iterator[Price]:
    """Parse a TimeSeries element."""
    period = time_series.find("{*}Period")
    if period is None:
        msg = "Time series period data missing"
        raise ValueError(msg)

    unit = Unit.parse(time_series)
    res = Resolution.parse(period)

    start = period.findtext("{*}timeInterval/{*}start")
    end = period.findtext("{*}timeInterval/{*}end")
    if start is None or end is None:
        msg = "start or end time missing from period"
        raise ValueError(msg)
    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)
    prices = (Price.parse(p, start, res, unit) for p in period.findall("{*}Point"))
    return interpolate_prices(prices, max(start, start_time), min(end, end_time))


def parse_prices(
    root: ET.Element, start_time: datetime, end_time: datetime
) -> Iterator[Price]:
    """Parse the prices.

    The API might return blocks that include more data than requested. The
    function filters out the data that is outside of the requested range.
    """
    for time_series in root.findall("{*}TimeSeries"):
        yield from parse_time_series(time_series, start_time, end_time)
