"""Data platform HTTP contracts: sources, identity, conflicts, candle quality."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from arcturus_api.api.deps import get_identity_service, get_quality_service
from arcturus_api.application.identity.service import EntityResolutionService
from arcturus_api.application.market.service import MarketDataService
from arcturus_api.application.quality.service import DataQualityService
from arcturus_api.domain.data.conflicts import DataConflict, ResolutionStatus
from arcturus_api.domain.identity.models import (
    CompanyIdentity,
    IdentifierKey,
    IdentifierScheme,
    IdentitySyncPlan,
    IdentitySyncResult,
)
from arcturus_api.domain.identity.ports import CompanyIdentityRepository
from arcturus_api.domain.market.models import Candle, CandleSeries, Interval, Quote, Symbol
from arcturus_api.domain.market.ports import MarketDataProvider
from arcturus_api.domain.quality.models import DataQualityReport
from arcturus_api.main import create_app


class EmptyIdentityRepository(CompanyIdentityRepository):
    async def find(
        self, key: IdentifierKey, as_of: datetime | None = None
    ) -> CompanyIdentity | None:
        return None

    async def active_identifiers(self, schemes: set[IdentifierScheme]) -> dict[IdentifierKey, UUID]:
        return {}

    async def apply_sync(
        self,
        plan: IdentitySyncPlan,
        source_id: str,
        observed_at: datetime,
        quality: DataQualityReport,
    ) -> IdentitySyncResult:
        raise NotImplementedError

    async def list_conflicts(
        self, status: ResolutionStatus | None, limit: int, offset: int
    ) -> tuple[list[DataConflict], int]:
        return [], 0


class CleanCandles(MarketDataProvider):
    name = "yahoo"

    async def get_quote(self, symbol: Symbol) -> Quote:
        raise NotImplementedError

    async def get_candles(
        self, symbol: Symbol, interval: Interval, start: datetime, end: datetime
    ) -> CandleSeries:
        last = datetime.now(UTC) - timedelta(hours=2)
        candles = [
            Candle(
                timestamp=last - timedelta(days=29 - index),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=1000,
            )
            for index in range(30)
        ]
        return CandleSeries(symbol=symbol, interval=interval, candles=candles)


def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_identity_service] = lambda: EntityResolutionService(
        EmptyIdentityRepository()
    )
    app.dependency_overrides[get_quality_service] = lambda: DataQualityService(
        MarketDataService(CleanCandles())
    )
    return TestClient(app)


class TestDataPlatformApi:
    def test_sources_expose_hierarchy_and_licence_status(self) -> None:
        with client() as http:
            response = http.get("/api/v1/data/sources")
        assert response.status_code == 200
        sources = {source["source_id"]: source for source in response.json()}
        assert sources["nse_archives"]["trust_tier"] == 1
        assert sources["nse_website"]["license_status"] == "restricted"
        assert sources["x"]["trust_tier"] == 6
        assert sources["x"]["enabled"] is False

    def test_identity_rejects_vendor_tickers(self) -> None:
        with client() as http:
            response = http.get("/api/v1/companies/RELIANCE.NS/identity")
        assert response.status_code == 422

    def test_identity_unknown_company_is_404(self) -> None:
        with client() as http:
            response = http.get("/api/v1/companies/NSE:NOSUCHCO/identity")
        assert response.status_code == 404

    def test_conflicts_page(self) -> None:
        with client() as http:
            response = http.get("/api/v1/data/conflicts?status=open")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_candle_quality_report(self) -> None:
        with client() as http:
            response = http.get("/api/v1/market/quality/NSE:TEST")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "valid"
        assert body["source_id"] == "yahoo"
        assert body["rules_version"] == "1.0.0"
