"""Tests for fetcher module."""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from gh_pr_comments.fetcher import (
    FetchError,
    _handle_rate_limit,
    fetch_org_repos,
    fetch_pr_events,
    fetch_pr_record,
    fetch_repo_prs,
    fetch_organization_data,
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

    def test_other_github_error_raises_fetch_error(self):
        """Other GitHub errors should raise FetchError."""
        from github import GithubException

        mock_client = MagicMock()
        mock_client.get_organization.side_effect = GithubException(
            status=403,
            data={"message": "Forbidden"},
            headers={},
        )

        with pytest.raises(FetchError) as exc_info:
            list(fetch_org_repos(mock_client, "test-org"))

        assert "Failed to access" in str(exc_info.value)


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

    def test_fetches_approved_event(self):
        """Should include approved event for approval reviews."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []

        mock_review = MagicMock()
        mock_review.user.login = "reviewer"
        mock_review.body = "LGTM!"
        mock_review.state = "APPROVED"
        mock_review.submitted_at = datetime(2025, 6, 15, 11, 0, 0)
        mock_pr.get_reviews.return_value = [mock_review]

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        approved_events = [e for e in events if e["type"] == "approved"]
        assert len(approved_events) == 1
        assert approved_events[0]["person"] == "reviewer"

    def test_fetches_changes_requested_event(self):
        """Should include changes_requested event for change request reviews."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []

        mock_review = MagicMock()
        mock_review.user.login = "reviewer"
        mock_review.body = "Please fix this"
        mock_review.state = "CHANGES_REQUESTED"
        mock_review.submitted_at = datetime(2025, 6, 15, 11, 0, 0)
        mock_pr.get_reviews.return_value = [mock_review]

        date_filter = DateFilter()
        events = fetch_pr_events(mock_pr, date_filter)

        cr_events = [e for e in events if e["type"] == "changes_requested"]
        assert len(cr_events) == 1
        assert cr_events[0]["person"] == "reviewer"

    def test_approval_not_filtered_by_date(self):
        """Approval events should be captured regardless of date filter."""
        mock_pr = MagicMock()
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []

        mock_review = MagicMock()
        mock_review.user.login = "reviewer"
        mock_review.body = "LGTM!"
        mock_review.state = "APPROVED"
        mock_review.submitted_at = datetime(2025, 1, 1, 11, 0, 0)  # Before date filter
        mock_pr.get_reviews.return_value = [mock_review]

        date_filter = DateFilter(since=date(2025, 6, 1))
        events = fetch_pr_events(mock_pr, date_filter)

        # Approval should be captured
        approved_events = [e for e in events if e["type"] == "approved"]
        assert len(approved_events) == 1
        # Comment from body should NOT be captured (date filtered)
        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 0


class TestHandleRateLimit:
    """Tests for _handle_rate_limit function."""

    def test_raises_error_at_max_retries(self):
        """Should raise FetchError when max retries reached."""
        with pytest.raises(FetchError) as exc_info:
            _handle_rate_limit(3, max_retries=3)

        assert "max retries" in str(exc_info.value).lower()

    def test_sleeps_with_backoff(self, mocker):
        """Should sleep with exponential backoff."""
        mock_sleep = mocker.patch("gh_pr_comments.fetcher.time.sleep")

        _handle_rate_limit(0, max_retries=3)

        mock_sleep.assert_called_once()
        # First attempt should wait 60 seconds
        assert mock_sleep.call_args[0][0] == 60

    def test_backoff_increases_with_attempts(self, mocker):
        """Backoff should increase with each attempt."""
        mock_sleep = mocker.patch("gh_pr_comments.fetcher.time.sleep")

        _handle_rate_limit(1, max_retries=3)

        # Second attempt should wait 120 seconds
        assert mock_sleep.call_args[0][0] == 120


class TestFetchPRRecord:
    """Tests for fetch_pr_record function."""

    def test_returns_pr_record(self):
        """Should return a PRRecord with events."""
        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        date_filter = DateFilter()
        record = fetch_pr_record(mock_pr, date_filter)

        assert record["number"] == 123
        assert record["title"] == "Test PR"
        assert len(record["events"]) == 1


class TestFetchOrganizationData:
    """Tests for fetch_organization_data function."""

    def test_yields_repo_prs(self):
        """Should yield repo name and PRs for each repository."""
        mock_client = MagicMock()
        mock_org = MagicMock()

        mock_repo = MagicMock()
        mock_repo.name = "test-repo"

        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        mock_repo.get_pulls.return_value = [mock_pr]
        mock_org.get_repos.return_value = [mock_repo]
        mock_client.get_organization.return_value = mock_org

        date_filter = DateFilter()
        results = list(fetch_organization_data(mock_client, "test-org", date_filter))

        assert len(results) == 1
        repo_name, prs = results[0]
        assert repo_name == "test-repo"
        assert len(prs) == 1

    def test_applies_repo_filter(self):
        """Should skip repos that don't pass the filter."""
        mock_client = MagicMock()
        mock_org = MagicMock()

        mock_repo1 = MagicMock()
        mock_repo1.name = "include-me"
        mock_repo2 = MagicMock()
        mock_repo2.name = "exclude-me"

        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        mock_repo1.get_pulls.return_value = [mock_pr]
        mock_repo2.get_pulls.return_value = [mock_pr]
        mock_org.get_repos.return_value = [mock_repo1, mock_repo2]
        mock_client.get_organization.return_value = mock_org

        date_filter = DateFilter()
        repo_filter = lambda name: name.startswith("include")
        results = list(fetch_organization_data(mock_client, "test-org", date_filter, repo_filter))

        assert len(results) == 1
        assert results[0][0] == "include-me"

    def test_skips_repos_with_errors(self, mocker):
        """Should continue processing when a repo fails."""
        from github import GithubException

        mock_client = MagicMock()
        mock_org = MagicMock()

        mock_repo1 = MagicMock()
        mock_repo1.name = "good-repo"
        mock_repo2 = MagicMock()
        mock_repo2.name = "bad-repo"

        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.user.login = "author"
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        mock_repo1.get_pulls.return_value = [mock_pr]
        mock_repo2.get_pulls.side_effect = GithubException(
            status=500,
            data={"message": "Internal error"},
            headers={},
        )
        mock_org.get_repos.return_value = [mock_repo2, mock_repo1]  # bad repo first
        mock_client.get_organization.return_value = mock_org

        date_filter = DateFilter()
        results = list(fetch_organization_data(mock_client, "test-org", date_filter))

        # Should still get the good repo
        assert len(results) == 1
        assert results[0][0] == "good-repo"

    def test_skips_prs_with_no_events(self):
        """Should skip PRs that have no events."""
        mock_client = MagicMock()
        mock_org = MagicMock()

        mock_repo = MagicMock()
        mock_repo.name = "test-repo"

        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.user = None  # No user, so no created event
        mock_pr.created_at = datetime(2025, 6, 15, 10, 0, 0)
        mock_pr.state = "open"
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        mock_repo.get_pulls.return_value = [mock_pr]
        mock_org.get_repos.return_value = [mock_repo]
        mock_client.get_organization.return_value = mock_org

        date_filter = DateFilter()
        results = list(fetch_organization_data(mock_client, "test-org", date_filter))

        # Should be empty since PR has no events
        assert len(results) == 0
