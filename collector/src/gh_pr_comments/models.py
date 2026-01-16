"""Data models for PR comment analysis."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, TypedDict


class DateRange(TypedDict, total=False):
    """Date range for filtering."""

    since: str | None
    until: str | None


class PREvent(TypedDict):
    """A single event on a PR."""

    type: Literal["created", "comment", "merged", "closed"]
    date: str
    person: str


class PRRecord(TypedDict):
    """A pull request with its events."""

    number: int
    title: str
    events: list[PREvent]


class AnalysisReport(TypedDict):
    """Complete analysis report structure."""

    organization: str
    generated_at: str
    date_range: DateRange
    repositories: dict[str, list[PRRecord]]


@dataclass
class DateFilter:
    """Date range filter for PR queries."""

    since: date | None = None
    until: date | None = None

    def contains(self, dt: datetime) -> bool:
        """Check if a datetime falls within this filter's range."""
        if dt is None:
            return True

        check_date = dt.date() if isinstance(dt, datetime) else dt

        if self.since and check_date < self.since:
            return False
        if self.until and check_date > self.until:
            return False
        return True
