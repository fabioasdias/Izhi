"""Tests for models module."""

from datetime import date, datetime

import pytest

from gh_pr_comments.models import DateFilter


class TestDateFilter:
    """Tests for DateFilter class."""

    def test_contains_with_none_datetime_returns_true(self):
        """Should return True when datetime is None."""
        df = DateFilter(since=date(2025, 1, 1))
        assert df.contains(None) is True

    def test_contains_with_no_filters_returns_true(self):
        """Should return True when no date filters are set."""
        df = DateFilter()
        dt = datetime(2025, 6, 15, 12, 0, 0)
        assert df.contains(dt) is True

    def test_contains_with_since_filter_accepts_date_after(self):
        """Should return True for dates after since."""
        df = DateFilter(since=date(2025, 1, 1))
        dt = datetime(2025, 6, 15, 12, 0, 0)
        assert df.contains(dt) is True

    def test_contains_with_since_filter_rejects_date_before(self):
        """Should return False for dates before since."""
        df = DateFilter(since=date(2025, 6, 1))
        dt = datetime(2025, 1, 15, 12, 0, 0)
        assert df.contains(dt) is False

    def test_contains_with_until_filter_accepts_date_before(self):
        """Should return True for dates before until."""
        df = DateFilter(until=date(2025, 12, 31))
        dt = datetime(2025, 6, 15, 12, 0, 0)
        assert df.contains(dt) is True

    def test_contains_with_until_filter_rejects_date_after(self):
        """Should return False for dates after until."""
        df = DateFilter(until=date(2025, 6, 1))
        dt = datetime(2025, 12, 15, 12, 0, 0)
        assert df.contains(dt) is False

    def test_contains_with_both_filters_accepts_date_in_range(self):
        """Should return True for dates within the range."""
        df = DateFilter(since=date(2025, 1, 1), until=date(2025, 12, 31))
        dt = datetime(2025, 6, 15, 12, 0, 0)
        assert df.contains(dt) is True

    def test_contains_with_both_filters_rejects_date_outside_range(self):
        """Should return False for dates outside the range."""
        df = DateFilter(since=date(2025, 6, 1), until=date(2025, 6, 30))
        dt = datetime(2025, 1, 15, 12, 0, 0)
        assert df.contains(dt) is False
