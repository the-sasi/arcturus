"""Listing-file validation before rows are used as identity evidence.

WARNING (row rejected from identity linking, listing itself still usable):
  missing ISIN · malformed ISIN / bad check digit · symbol or ISIN duplicated
  within the batch (every row sharing the key is rejected)
INVALID (no identity changes at all):
  empty batch · more than 10% of rows rejected — a format change at the source
  must never flood the entity graph with bad links or false conflicts
"""

from collections import Counter
from datetime import datetime

from arcturus_api.domain.identity.identifiers import is_valid_isin
from arcturus_api.domain.identity.models import ListingIdentity
from arcturus_api.domain.market.models import Instrument
from arcturus_api.domain.quality.models import (
    DataQualityReport,
    QualityDimension,
    QualityIssue,
    QualityStatus,
    build_report,
)

LISTING_RULES_VERSION = "1.0.0"
_MAX_REJECTED_SHARE = 0.10
_MAX_EXAMPLES = 5


def assess_listings(
    listings: list[Instrument], source_id: str, checked_at: datetime
) -> tuple[DataQualityReport, list[ListingIdentity]]:
    missing: list[str] = []
    malformed: list[str] = []
    candidates: list[ListingIdentity] = []

    for item in listings:
        isin = (item.isin or "").strip().upper()
        if not isin:
            missing.append(str(item.symbol))
        elif not is_valid_isin(isin):
            malformed.append(f"{item.symbol} ({isin})")
        else:
            candidates.append(ListingIdentity(symbol=item.symbol, isin=isin, name=item.name))

    symbol_counts = Counter(str(row.symbol) for row in candidates)
    isin_counts = Counter(row.isin for row in candidates)
    duplicated = [
        row for row in candidates if symbol_counts[str(row.symbol)] > 1 or isin_counts[row.isin] > 1
    ]
    accepted = [row for row in candidates if row not in duplicated]

    issues: list[QualityIssue] = []
    warning = QualityStatus.WARNING
    if missing:
        issues.append(
            _issue(
                "missing_isin",
                QualityDimension.COMPLETENESS,
                warning,
                "row(s) without an ISIN",
                missing,
            )
        )
    if malformed:
        issues.append(
            _issue(
                "invalid_isin",
                QualityDimension.VALIDITY,
                warning,
                "row(s) with a malformed ISIN",
                malformed,
            )
        )
    if duplicated:
        labels = [f"{row.symbol} ({row.isin})" for row in duplicated]
        issues.append(
            _issue(
                "duplicate_identifier",
                QualityDimension.DUPLICATION,
                warning,
                "row(s) sharing a symbol or ISIN",
                labels,
            )
        )

    rejected = len(listings) - len(accepted)
    if not listings:
        issues.append(
            QualityIssue(
                check="empty_listing",
                dimension=QualityDimension.COMPLETENESS,
                severity=QualityStatus.INVALID,
                message="listing contained no rows",
                count=1,
            )
        )
    elif rejected / len(listings) > _MAX_REJECTED_SHARE:
        issues.append(
            QualityIssue(
                check="rejected_share",
                dimension=QualityDimension.COMPLETENESS,
                severity=QualityStatus.INVALID,
                message=(
                    f"{rejected} of {len(listings)} rows rejected (over "
                    f"{_MAX_REJECTED_SHARE:.0%}) — possible source format change"
                ),
                count=rejected,
            )
        )

    report = build_report(
        dataset="instrument_listings",
        subject=source_id,
        source_id=source_id,
        checked=[
            QualityDimension.COMPLETENESS,
            QualityDimension.VALIDITY,
            QualityDimension.DUPLICATION,
        ],
        issues=issues,
        records_checked=len(listings),
        rules_version=LISTING_RULES_VERSION,
        checked_at=checked_at,
    )
    return report, accepted


def _issue(
    check: str, dimension: QualityDimension, severity: QualityStatus, what: str, hits: list[str]
) -> QualityIssue:
    return QualityIssue(
        check=check,
        dimension=dimension,
        severity=severity,
        message=f"{len(hits)} {what}",
        count=len(hits),
        examples=hits[:_MAX_EXAMPLES],
    )
