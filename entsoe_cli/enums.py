"""Enums."""

import xml.etree.ElementTree as ET
from datetime import timedelta
from enum import StrEnum
from typing import Self


class DocumentType(StrEnum):
    """Document type. Only Price Document (A44) is supported for now."""

    PriceDocument = "A44"

    def request_type(self) -> str:
        """Return legible request type for document type."""
        match self:
            case DocumentType.PriceDocument:
                return "Energy price"


class Domain(StrEnum):
    """Domain for the observation. Only Finland is supported for now."""

    Finland = "10YFI-1--------U"


class Unit(StrEnum):
    """Unit for the observation. Only EUR/MWh is supported for now."""

    EurMwh = "EUR/MWh"

    @classmethod
    def parse(cls, time_series: ET.Element) -> Self:
        """Parse unit from time series element."""
        currency = time_series.findtext("{*}currency_Unit.name")
        unit = time_series.findtext("{*}price_Measure_Unit.name")
        if currency is None or unit is None:
            msg = "unit missing"
            raise ValueError(msg)
        match currency.lower(), unit.lower():
            case ("eur", "mwh"):
                return cls("EUR/MWh")
            case _:
                msg = f"invalid unit {currency}/{unit}"
                raise ValueError(msg)


class Resolution(StrEnum):
    """Resolution for the observation. 60 and 15 min resolutions are supported."""

    QuarterHourly = "PT15M"
    Hourly = "PT60M"

    @classmethod
    def parse(cls, period: ET.Element) -> Self:
        """Parse resolution from period element."""
        resolution = period.findtext("{*}resolution")
        if resolution is None:
            msg = "resolution missing"
            raise ValueError(msg)
        return cls(resolution)

    def to_timedelta(self) -> timedelta:
        """Represent the resolution as timedelta."""
        match self:
            case Resolution.QuarterHourly:
                return timedelta(minutes=15)
            case Resolution.Hourly:
                return timedelta(minutes=60)
