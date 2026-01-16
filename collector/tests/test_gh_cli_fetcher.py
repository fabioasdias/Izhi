"""Tests for gh CLI fetcher module."""

import json
import subprocess
from datetime import date

import pytest

from gh_pr_comments.gh_cli_fetcher import (
    GhCliError,
    _run_gh_command,
    fetch_org_repos_gh,
    fetch_pr_comments_gh,
    fetch_pr_events_gh,
    fetch_pr_issue_comments_gh,
    fetch_pr_reviews_gh,
    fetch_repo_prs_gh,
)
from gh_pr_comments.models import DateFilter


class TestRunGhCommand:
    """Tests for _run_gh_command function."""

    def test_returns_parsed_json(self, mocker):
        """Should return parsed JSON output."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gh", "repo", "list"],
            returncode=0,
            stdout='[{"name": "repo1"}]',
            stderr="",
        )

        result = _run_gh_command(["repo", "list"])

        assert result == [{"name": "repo1"}]
        mock_run.assert_called_once()

    def test_returns_empty_list_for_empty_output(self, mocker):
        """Should return empty list when output is empty."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gh", "repo", "list"],
            returncode=0,
            stdout="",
            stderr="",
        )

        result = _run_gh_command(["repo", "list"])

        assert result == []

    def test_raises_error_when_gh_not_found(self, mocker):
        """Should raise GhCliError when gh CLI is not installed."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(GhCliError) as exc_info:
            _run_gh_command(["repo", "list"])

        assert "not found" in str(exc_info.value).lower()

    def test_raises_error_on_command_failure(self, mocker):
        """Should raise GhCliError when command fails."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gh", "repo", "list"],
            stderr="permission denied",
        )

        with pytest.raises(GhCliError) as exc_info:
            _run_gh_command(["repo", "list"])

        assert "permission denied" in str(exc_info.value)


class TestFetchOrgReposGh:
    """Tests for fetch_org_repos_gh function."""

    def test_yields_repo_names(self, mocker):
        """Should yield repository names from organization."""
        mock_run = mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[{"name": "repo1"}, {"name": "repo2"}],
        )

        repos = list(fetch_org_repos_gh("test-org"))

        assert repos == ["repo1", "repo2"]
        mock_run.assert_called_once()

    def test_raises_error_for_nonexistent_org(self, mocker):
        """Should raise GhCliError for nonexistent organization."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            side_effect=GhCliError("Could not resolve to an Organization"),
        )

        with pytest.raises(GhCliError) as exc_info:
            list(fetch_org_repos_gh("nonexistent-org"))

        assert "not found" in str(exc_info.value).lower()


class TestFetchRepoPRsGh:
    """Tests for fetch_repo_prs_gh function."""

    def test_yields_prs_within_date_range(self, mocker):
        """Should yield PRs within the specified date range."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z"},
                {"number": 2, "title": "PR 2", "createdAt": "2025-01-01T10:00:00Z"},
            ],
        )

        date_filter = DateFilter(since=date(2025, 6, 1), until=date(2025, 12, 31))
        prs = list(fetch_repo_prs_gh("test-org", "repo1", date_filter))

        assert len(prs) == 1
        assert prs[0]["number"] == 1

    def test_yields_all_prs_without_date_filter(self, mocker):
        """Should yield all PRs when no date filter is provided."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z"},
                {"number": 2, "title": "PR 2", "createdAt": "2024-01-01T10:00:00Z"},
            ],
        )

        date_filter = DateFilter()
        prs = list(fetch_repo_prs_gh("test-org", "repo1", date_filter))

        assert len(prs) == 2


class TestFetchPREventsGh:
    """Tests for fetch_pr_events_gh function."""

    def test_fetches_created_event(self, mocker):
        """Should include created event."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        assert len(events) == 1
        assert events[0]["type"] == "created"
        assert events[0]["person"] == "author"

    def test_fetches_comment_events(self, mocker):
        """Should include comment events from all sources."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[
                {
                    "user": {"login": "reviewer1"},
                    "created_at": "2025-06-15T11:00:00Z",
                }
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[
                {
                    "user": {"login": "reviewer2"},
                    "created_at": "2025-06-15T12:00:00Z",
                }
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[
                {
                    "user": {"login": "reviewer1"},
                    "body": "LGTM!",
                    "state": "COMMENTED",
                    "submitted_at": "2025-06-15T13:00:00Z",
                }
            ],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        assert len(events) == 4  # created + 3 comments
        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 3

    def test_fetches_approved_event(self, mocker):
        """Should include approved event for approval reviews."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[
                {
                    "user": {"login": "reviewer"},
                    "body": "LGTM!",
                    "state": "APPROVED",
                    "submitted_at": "2025-06-15T13:00:00Z",
                }
            ],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        approved_events = [e for e in events if e["type"] == "approved"]
        assert len(approved_events) == 1
        assert approved_events[0]["person"] == "reviewer"

    def test_fetches_changes_requested_event(self, mocker):
        """Should include changes_requested event for change request reviews."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[
                {
                    "user": {"login": "reviewer"},
                    "body": "Please fix this",
                    "state": "CHANGES_REQUESTED",
                    "submitted_at": "2025-06-15T13:00:00Z",
                }
            ],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        cr_events = [e for e in events if e["type"] == "changes_requested"]
        assert len(cr_events) == 1
        assert cr_events[0]["person"] == "reviewer"

    def test_approval_not_filtered_by_date(self, mocker):
        """Approval events should be captured regardless of date filter."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[
                {
                    "user": {"login": "reviewer"},
                    "body": "LGTM!",
                    "state": "APPROVED",
                    "submitted_at": "2025-01-01T13:00:00Z",  # Before date filter
                }
            ],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter(since=date(2025, 6, 1))
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        # Approval should be captured even though it's before date filter
        approved_events = [e for e in events if e["type"] == "approved"]
        assert len(approved_events) == 1
        # But the comment from review body should NOT be captured (date filtered)
        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 0

    def test_fetches_merged_event(self, mocker):
        """Should include merged event for merged PRs."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "mergedAt": "2025-06-16T10:00:00Z",
            "state": "MERGED",
            "author": {"login": "author"},
            "mergedBy": {"login": "merger"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        assert len(events) == 2  # created + merged
        assert events[-1]["type"] == "merged"
        assert events[-1]["person"] == "merger"

    def test_fetches_closed_event(self, mocker):
        """Should include closed event for closed-without-merge PRs."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "closedAt": "2025-06-16T10:00:00Z",
            "state": "CLOSED",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        assert len(events) == 2  # created + closed
        assert events[-1]["type"] == "closed"

    def test_events_sorted_by_date(self, mocker):
        """Events should be sorted chronologically."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[
                {
                    "user": {"login": "reviewer"},
                    "created_at": "2025-06-15T11:00:00Z",
                }
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        dates = [e["date"] for e in events]
        assert dates == sorted(dates)

    def test_filters_comments_by_date(self, mocker):
        """Should only include comments within the date range."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[
                {
                    "user": {"login": "reviewer1"},
                    "created_at": "2025-06-15T11:00:00Z",
                },
                {
                    "user": {"login": "reviewer2"},
                    "created_at": "2025-01-01T11:00:00Z",  # Before range
                },
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_issue_comments_gh",
            return_value=[],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_reviews_gh",
            return_value=[],
        )

        pr = {
            "number": 1,
            "title": "Test PR",
            "createdAt": "2025-06-15T10:00:00Z",
            "state": "OPEN",
            "author": {"login": "author"},
        }

        date_filter = DateFilter(since=date(2025, 6, 1))
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 1
        assert comment_events[0]["person"] == "reviewer1"
