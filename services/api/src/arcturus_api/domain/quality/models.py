"""Data quality report contract.

Status semantics:
- VALID: every check passed.
- WARNING: usable, but consumers (UI, future agents) must see the issues.
- INVALID: must not be used for computation (e.g. backtests refuse it).

There is deliberately no single numeric quality score: a weighted number would
imply precision the rules do not have. The per-dimension statuses are the
component scores, and the rules version records which rules produced them.
"""

from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QualityStatus(StrEnum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


_SEVERITY: dict[QualityStatus, int] = {
    QualityStatus.VALID: 0,
    QualityStatus.WARNING: 1,
    QualityStatus.INVALID: 2,
}


def worst(statuses: Iterable[QualityStatus]) -> QualityStatus:
    return max(statuses, key=_SEVERITY.__getitem__, default=QualityStatus.VALID)


class QualityDimension(StrEnum):
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    FRESHNESS = "freshness"
    DUPLICATION = "duplication"
    REFERENTIAL_INTEGRITY = "referential_integrity"


class QualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    check: str
    dimension: QualityDimension
    severity: QualityStatus
    message: str
    count: int = Field(ge=1)
    examples: list[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def _issue_is_not_valid(cls, value: QualityStatus) -> QualityStatus:
        if value == QualityStatus.VALID:
            raise ValueError("an issue must be a WARNING or INVALID")
        return value


class DataQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset: str
    subject: str
    source_id: str | None
    status: QualityStatus
    dimensions: dict[QualityDimension, QualityStatus]
    issues: list[QualityIssue]
    records_checked: int
    rules_version: str
    checked_at: datetime

    def summary(self) -> str:
        if not self.issues:
            return "all checks passed"
        return "; ".join(issue.message for issue in self.issues)


def build_report(
    *,
    dataset: str,
    subject: str,
    source_id: str | None,
    checked: Iterable[QualityDimension],
    issues: list[QualityIssue],
    records_checked: int,
    rules_version: str,
    checked_at: datetime,
) -> DataQualityReport:
    dimensions = dict.fromkeys(checked, QualityStatus.VALID)
    for issue in issues:
        dimensions[issue.dimension] = worst(
            (dimensions.get(issue.dimension, QualityStatus.VALID), issue.severity)
        )
    return DataQualityReport(
        dataset=dataset,
        subject=subject,
        source_id=source_id,
        status=worst(dimensions.values()),
        dimensions=dimensions,
        issues=issues,
        records_checked=records_checked,
        rules_version=rules_version,
        checked_at=checked_at,
    )


class DataQualityError(Exception):
    """Raised when a computation refuses INVALID input."""

    def __init__(self, report: DataQualityReport) -> None:
        super().__init__(f"Data failed quality checks for {report.subject}: {report.summary()}")
        self.report = report
