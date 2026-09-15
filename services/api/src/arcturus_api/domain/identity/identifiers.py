"""Identifier parsing and validation (pure)."""

import re

from arcturus_api.domain.identity.models import (
    IdentifierKey,
    IdentifierScheme,
    InvalidIdentifierError,
)

_ISIN_PATTERN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
_ISIN_PAYLOAD_PATTERN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}")


def isin_check_digit(payload: str) -> int:
    """ISO 6166 check digit for the first 11 ISIN characters.

    Letters expand to two digits (A=10 … Z=35); a Luhn pass then doubles every
    second digit starting from the rightmost.
    """
    if not _ISIN_PAYLOAD_PATTERN.fullmatch(payload):
        raise ValueError(f"not an ISIN payload: {payload!r}")
    digits = "".join(str(int(char, 36)) for char in payload)
    total = 0
    for position, char in enumerate(reversed(digits)):
        digit = int(char)
        if position % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10


def is_valid_isin(value: str) -> bool:
    if not _ISIN_PATTERN.fullmatch(value):
        return False
    return isin_check_digit(value[:-1]) == int(value[-1])


def parse_identifier(raw: str) -> IdentifierKey:
    """Accept ``NSE:SYMBOL``, ``BSE:SCRIPCODE`` or a bare ISIN.

    Vendor tickers (``RELIANCE.NS``) are deliberately not accepted: vendor
    formats stay quarantined in adapters (ADR-006).
    """
    value = raw.strip().upper()
    if ":" in value:
        prefix, rest = value.split(":", 1)
        if prefix == "NSE" and rest:
            return IdentifierKey(scheme=IdentifierScheme.NSE_SYMBOL, value=rest)
        if prefix == "BSE" and rest.isdigit():
            return IdentifierKey(scheme=IdentifierScheme.BSE_CODE, value=rest)
        raise InvalidIdentifierError(raw)
    if is_valid_isin(value):
        return IdentifierKey(scheme=IdentifierScheme.ISIN, value=value)
    raise InvalidIdentifierError(raw)
