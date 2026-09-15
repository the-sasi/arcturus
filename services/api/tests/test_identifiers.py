import pytest

from arcturus_api.domain.identity.identifiers import (
    is_valid_isin,
    isin_check_digit,
    parse_identifier,
)
from arcturus_api.domain.identity.models import IdentifierScheme, InvalidIdentifierError


class TestIsin:
    @pytest.mark.parametrize("isin", ["INE002A01018", "INE467B01029", "US0378331005"])
    def test_published_isins_validate(self, isin: str) -> None:
        assert is_valid_isin(isin)

    def test_check_digit_matches_published_value(self) -> None:
        assert isin_check_digit("INE002A0101") == 8  # Reliance Industries: INE002A01018

    @pytest.mark.parametrize(
        "value", ["INE002A01019", "INE002A0101", "ine002a01018", "IN-002A01018", ""]
    )
    def test_rejects_bad_check_digit_and_format(self, value: str) -> None:
        assert not is_valid_isin(value)

    def test_check_digit_needs_a_payload(self) -> None:
        with pytest.raises(ValueError, match="payload"):
            isin_check_digit("12345")


class TestParseIdentifier:
    def test_nse_symbol_is_normalised(self) -> None:
        key = parse_identifier(" nse:reliance ")
        assert key.scheme == IdentifierScheme.NSE_SYMBOL
        assert key.value == "RELIANCE"
        assert str(key) == "NSE_SYMBOL:RELIANCE"

    def test_bare_isin(self) -> None:
        assert parse_identifier("INE002A01018").scheme == IdentifierScheme.ISIN

    def test_bse_scrip_code(self) -> None:
        key = parse_identifier("BSE:500325")
        assert (key.scheme, key.value) == (IdentifierScheme.BSE_CODE, "500325")

    @pytest.mark.parametrize(
        "raw", ["RELIANCE", "NSE:", "BSE:RELIANCE", "RELIANCE.NS", "INE002A01019", "NASDAQ:AAPL"]
    )
    def test_rejects_ambiguous_vendor_or_invalid_input(self, raw: str) -> None:
        with pytest.raises(InvalidIdentifierError):
            parse_identifier(raw)
