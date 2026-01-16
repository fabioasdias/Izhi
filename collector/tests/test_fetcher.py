"""Tests for fetcher module."""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from gh_pr_comments.fetcher import (
    FetchError,
    fetch_org_repos,
    fetch_pr_events,
    fetch_repo_prs,
)
from gh_pr_comments.models import DateFilter


class TestFetchOrgRepos:
    """Tests for fetch_org_repos function."""

    def test_valid_org_yields_repos(self):
        """Valid organization should yield repositories."""
        mock_client = MagicMock()
        mock_org = MagicMock()
        mock_repo1 = MagicMock()
        mock_repo1.name = "repo1"
        mock_repo2 = MagicMock()
        mock_repo2.name = "repo2"
        mock_org.get_repos.return_value = [mock_repo1, mock_repo2]
        mock_client.get_organization.return_value = mock_org

        repos = list(fetch_org_repos(mock_client, "test-org"))

        assert len(repos) == 2
        assert repos[0].name == "repo1"
        assert repos[1].name == "repo2"

    def test_nonexistent_org_raises_fetch_error(self):
        """Nonexistent organization should raise FetchError."""
        from github import GithubException

        mock_client = MagicMock()
        mock_client.get_organization.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"},
            headers={},
        )

        with pytest.raises(FetchError) as exc_info:
            list(fetch_org_repos(mock_client, "nonexistent-org"))

        assert "not found" in str(exc_info.value).lower()


class TestFetchRepoPRs:
    """Tests for fetch_repo_prs function."""

    def test_fetches_prs_within_date_range(self):
        """Should yield PRs within the specified date range."""
        mock_repo = MagicMock()
        mock_pr1 = MagicMock()
        mock_pr1.number = 1
        mock_pr1.title = "PR 1"
        mock_pr1.created_at = datetime(2025, 6, 15)

        mock_pr2 = MagicMock()
        mock_pr2.number = 2
        mock_pr2.title = "PR 2"
        mock_pr2.created_at = datetime(2025, 1, 1)  # Before date range

        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2]

        date_filter = DateFilter(since=date(2025, 6, 1), until=date(2025, 12, 31))
        prs = list(fetch_repo_prs(mock_repo, date_filter))

        # Should stop at mock_pr2 since it's before since date
        assert len(prs) == 1
        assert prs[0].number == 1

    def test_fetches_all_prs_without_date_filter(self):
        """Should yield all PRs when no date filter is provided."""
        mock_repo = MagicMock()
        mock_pr1 = MagicMock()
        mock_pr1.number = 1
        mock_pr1.created_at = datetime(2025, 6, 15)

        mock_pr2 = MagicMock()
        mock_pr2.number = 2
        mock_pr2.created_at = datetime(2024, 1, 1)

        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2]

        date_filter = DateFilter()
        prs = list(fetch_repo_prs(mock_repo, date_filter))

        assert len(prs) == 2


class TestFetchPREvents:
    """Tests for fetch_pr_events function."""

    def test_fetches_created_event(self):
        """Should include created event."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        assert len(events) == 1
        assert events[0]["type"] == "created"
        assert events[0]["person"] == "author"

    def test_fetches_comment_events(self):
        """Should include comment events from all sources."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"

        # Review comment
        mock_review_comment = MagicMock()
        mock_review_comment.user.login = "reviewer1"
        mock_review_comment.created_at = datetime(2025, 6, 15, 11, 0, 0)
        mock_pr.get_review_comments.return_value = [mock_review_comment]

        # Issue comment
        mock_issue_comment = MagicMock()
        mock_issue_comment.user.login = "reviewer2"
        mock_issue_comment.created_at = datetime(2025, 6, 15, 12, 0, 0)
        mock_pr.get_issue_comments.return_value = [mock_issue_comment]

        # Review with body
        mock_review = MagicMock()
        mock_review.user.login = "reviewer1"
        mock_review.body = "LGTM!"
        mock_review.submitted_at = datetime(2025, 6, 15, 13, 0, 0)
        mock_pr.get_reviews.return_value = [mock_review]

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        assert len(events) == 4  # created + 3 comments
        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 3

    def test_fetches_merged_event(self):
        """Should include merged event for merged PRs."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "closed"
        mock_pr.merged = True
        mock_pr.merged_by.login = "merger"
        mock_pr.merged_at = datetime(2025, 6, 16, 10, 0, 0)
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        assert len(events) == 2  # created + merged
        assert events[-1]["type"] == "merged"
        assert events[-1]["person"] == "merger"

    def test_fetches_closed_event(self):
        """Should include closed event for closed-without-merge PRs."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.closed_at = datetime(2025, 6, 16, 10, 0, 0)
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        assert len(events) == 2  # created + closed
        assert events[-1]["type"] == "closed"

    def test_events_sorted_by_date(self):
        """Events should be sorted chronologically."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"

        # Comment before created (edge case)
        mock_comment = MagicMock()
        mock_comment.user.login = "reviewer"
        mock_comment.created_at = datetime(2025, 6, 15, 11, 0, 0)
        mock_pr.get_review_comments.return_value = [mock_comment]
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        dates = [e["date"] for e in events]
        assert dates == sorted(dates)

    def test_skips_reviews_without_body(self):
        """Should skip reviews that have no body text."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []

        # Review without body
        mock_review = MagicMock()
        mock_review.user.login = "reviewer"
        mock_review.body = None
        mock_review.submitted_at = datetime(2025, 6, 15, 11, 0, 0)
        mock_pr.get_reviews.return_value = [mock_review]

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        assert len(events) == 1  # only created
        assert events[0]["type"] == "created"

    def test_filters_comments_by_date(self):
        """Should only include comments within the date range."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"

        mock_comment1 = MagicMock()
        mock_comment1.user.login = "reviewer1"
        mock_comment1.created_at = datetime(2025, 6, 15, 11, 0, 0)

        mock_comment2 = MagicMock()
        mock_comment2.user.login = "reviewer2"
        mock_comment2.created_at = datetime(2025, 1, 1, 11, 0, 0)  # Before range

        mock_pr.get_review_comments.return_value = [mock_comment1, mock_comment2]
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter(since=date(2025, 6, 1))
        events = fetch_pr_events(mock_pr, date_filter)

        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 1
        assert comment_events[0]["person"] == "reviewer1"
