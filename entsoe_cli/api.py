"""Methods for interacting with the API."""

import os
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Self

from requests import get

from .enums import DocumentType, Domain
from .price import Price, parse_prices

URL = "https://web-api.tp.entsoe.eu/api"
MARKET_AGREEMENT_TYPE = "A01"  # DA, A07 is ID
TIMEOUT = 20
MAX_DAYS = 360  # one limit is really the max


class Params:
    """API request parameters."""

    document_type: DocumentType
    domain: Domain
    start_time: datetime
    end_time: datetime
    security_token: str

    @classmethod
    def price_request(
        cls,
        start_time: datetime,
        end_time: datetime,
        domain: Domain,
        security_token: str,
    ) -> Self:
        """Initialize an energy price request."""
        x = cls()
        x.document_type = DocumentType.PriceDocument
        x.start_time = start_time
        x.domain = domain
        x.set_period(start_time, end_time)
        x.security_token = security_token
        return x

    def set_period(self, start_time: datetime, end_time: datetime) -> None:
        """Ensure that the requested period is valid.

        - checks that start_time < end_time
        - sets end_time to be at most 360 days from start_time to match API limits
        """
        if start_time >= end_time:
            msg = "end time must be greater than start time"
            raise ValueError(msg)
        self.start_time = start_time
        self.end_time = min(end_time, self.start_time + timedelta(days=MAX_DAYS))

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Return iterator with request parameters."""
        yield ("documentType", self.document_type.value)
        yield ("periodStart", _format_dt_param_entsoe(self.start_time))
        yield ("periodEnd", _format_dt_param_entsoe(self.end_time))
        yield ("in_Domain", self.domain.value)
        yield ("out_Domain", self.domain.value)
        yield ("contract_MarketAgreement.type", MARKET_AGREEMENT_TYPE)
        yield ("securityToken", self.security_token)

    def __str__(self) -> str:
        """Return legible representation."""
        s = f"{self.document_type} for {self.domain}"
        s += f"\n between {self.start_time} and {self.end_time}"
        return s


def _format_dt_param_entsoe(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%d%H%M")


def _get_xml(params: Params) -> ET.Element:
    """Get the result as xml."""
    resp = get(URL, params=dict(params), timeout=TIMEOUT)
    resp.raise_for_status()
    return ET.fromstring(resp.content)  # noqa: S314


def _get_time_interval_end(root: ET.Element) -> None | datetime:
    """None effectively means end of data."""
    end = root.find("{*}period.timeInterval/{*}end")
    if end is None or end.text is None:
        return None
    return datetime.fromisoformat(end.text)


def get_paginated(
    params: Params,
    start_time: datetime,
    end_time: datetime,
) -> Iterator[Price]:
    """Split the query into chunks and combine the results."""
    xml = _get_xml(params)
    yield from parse_prices(xml, start_time, end_time)
    time_interval_end = _get_time_interval_end(xml)
    while time_interval_end is not None and time_interval_end < end_time:
        params.set_period(time_interval_end, end_time)
        xml = _get_xml(params)
        sleep(1)
        yield from parse_prices(xml, start_time, end_time)
        time_interval_end = _get_time_interval_end(xml)


def get_prices(
    start_time: datetime,
    end_time: datetime,
    domain: Domain = Domain.Finland,
    token: None | str = os.environ.get("ENTSOE_TOKEN"),
) -> Iterator[Price]:
    """Get an iterator for energy prices for the selected domain."""
    if token is None:
        msg = "security token missing"
        raise ValueError(msg)
    params = Params.price_request(start_time, end_time, domain, token)
    return get_paginated(params, start_time, end_time)
