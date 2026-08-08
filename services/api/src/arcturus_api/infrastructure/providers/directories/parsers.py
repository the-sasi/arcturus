"""Pure parsers for exchange listing files (unit-testable, no I/O).

Sources:
- NSE `EQUITY_L.csv` — all NSE-listed equities.
- Nasdaq Trader `nasdaqlisted.txt` / `otherlisted.txt` — NASDAQ, NYSE, AMEX.
"""

import csv
import io

from arcturus_api.domain.market.models import AssetClass, Exchange, Instrument, Symbol

# NSE series that represent normally tradable equity
_NSE_EQUITY_SERIES = {"EQ", "BE", "SM"}

_OTHER_LISTED_EXCHANGES = {"N": Exchange.NYSE, "A": Exchange.AMEX}


def parse_nse_equity_csv(text: str) -> list[Instrument]:
    reader = csv.DictReader(io.StringIO(text))
    instruments: list[Instrument] = []
    for row in reader:
        cleaned = {key.strip(): (value or "").strip() for key, value in row.items() if key}
        ticker = cleaned.get("SYMBOL", "")
        name = cleaned.get("NAME OF COMPANY", "")
        series = cleaned.get("SERIES", "")
        if not ticker or not name or series not in _NSE_EQUITY_SERIES:
            continue
        instruments.append(
            Instrument(
                symbol=Symbol(exchange=Exchange.NSE, ticker=ticker.upper()),
                name=name,
                asset_class=AssetClass.EQUITY,
                currency="INR",
                attributes={"series": series},
            )
        )
    return instruments


def _parse_pipe_file(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line and "|" in line]
    if not lines:
        return []
    header = [column.strip() for column in lines[0].split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if line.startswith("File Creation Time"):
            continue
        values = line.split("|")
        if len(values) != len(header):
            continue
        rows.append(dict(zip(header, (value.strip() for value in values), strict=True)))
    return rows


def parse_nasdaq_listed(text: str) -> list[Instrument]:
    instruments: list[Instrument] = []
    for row in _parse_pipe_file(text):
        ticker = row.get("Symbol", "")
        name = row.get("Security Name", "")
        if not ticker or not name or row.get("Test Issue") == "Y":
            continue
        is_etf = row.get("ETF") == "Y"
        instruments.append(
            Instrument(
                symbol=Symbol(exchange=Exchange.NASDAQ, ticker=ticker.upper()),
                name=name,
                asset_class=AssetClass.ETF if is_etf else AssetClass.EQUITY,
                currency="USD",
            )
        )
    return instruments


def parse_other_listed(text: str) -> list[Instrument]:
    """NYSE + AMEX come from `otherlisted.txt` (Exchange column N / A)."""
    instruments: list[Instrument] = []
    for row in _parse_pipe_file(text):
        exchange = _OTHER_LISTED_EXCHANGES.get(row.get("Exchange", ""))
        ticker = row.get("ACT Symbol", "")
        name = row.get("Security Name", "")
        if exchange is None or not ticker or not name or row.get("Test Issue") == "Y":
            continue
        is_etf = row.get("ETF") == "Y"
        instruments.append(
            Instrument(
                symbol=Symbol(exchange=exchange, ticker=ticker.upper()),
                name=name,
                asset_class=AssetClass.ETF if is_etf else AssetClass.EQUITY,
                currency="USD",
            )
        )
    return instruments
