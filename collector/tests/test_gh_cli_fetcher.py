"""Tests for gh CLI fetcher module."""

import json
import subprocess
from datetime import date

import pytest

from gh_pr_comments.gh_cli_fetcher import (
    GhCliError,
    RateLimitError,
    _is_rate_limit_error,
    _run_gh_command,
    fetch_org_repos_gh,
    fetch_organization_data_gh,
    fetch_pr_comments_gh,
    fetch_pr_events_gh,
    fetch_pr_issue_comments_gh,
    fetch_pr_record_gh,
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

    def test_raises_error_on_json_decode_failure(self, mocker):
        """Should raise GhCliError when JSON parsing fails."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gh", "api", "test"],
            returncode=0,
            stdout="not valid json {",
            stderr="",
        )

        with pytest.raises(GhCliError) as exc_info:
            _run_gh_command(["api", "test"])

        assert "Failed to parse" in str(exc_info.value)

    def test_retries_on_rate_limit(self, mocker):
        """Should retry when rate limit is hit."""
        mock_run = mocker.patch("subprocess.run")
        mock_sleep = mocker.patch("time.sleep")

        # First call fails with rate limit, second succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["gh", "api", "test"],
                stderr="API rate limit exceeded",
            ),
            subprocess.CompletedProcess(
                args=["gh", "api", "test"],
                returncode=0,
                stdout='{"success": true}',
                stderr="",
            ),
        ]

        result = _run_gh_command(["api", "test"])

        assert result == {"success": True}
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once()

    def test_raises_rate_limit_error_after_max_retries(self, mocker):
        """Should raise RateLimitError after exhausting retries."""
        mock_run = mocker.patch("subprocess.run")
        mock_sleep = mocker.patch("time.sleep")

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gh", "api", "test"],
            stderr="API rate limit exceeded",
        )

        with pytest.raises(RateLimitError) as exc_info:
            _run_gh_command(["api", "test"], max_retries=2)

        assert "Rate limit exceeded" in str(exc_info.value)
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once()


class TestIsRateLimitError:
    """Tests for _is_rate_limit_error function."""

    def test_detects_rate_limit_message(self):
        """Should detect 'rate limit' in error message."""
        assert _is_rate_limit_error("API rate limit exceeded") is True

    def test_detects_403_error(self):
        """Should detect 403 error code."""
        assert _is_rate_limit_error("Request failed with status 403") is True

    def test_detects_secondary_rate_limit(self):
        """Should detect secondary rate limit."""
        assert _is_rate_limit_error("secondary rate limit triggered") is True

    def test_detects_abuse_detection(self):
        """Should detect abuse detection message."""
        assert _is_rate_limit_error("abuse detection mechanism") is True

    def test_returns_false_for_other_errors(self):
        """Should return False for non-rate-limit errors."""
        assert _is_rate_limit_error("permission denied") is False
        assert _is_rate_limit_error("not found") is False


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

    def test_skips_pr_without_author(self, mocker):
        """Should skip created event when author is missing."""
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
            "author": None,
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        assert len(events) == 0

    def test_skips_comment_without_user(self, mocker):
        """Should skip comments when user is missing."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_comments_gh",
            return_value=[
                {
                    "user": None,
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

        comment_events = [e for e in events if e["type"] == "comment"]
        assert len(comment_events) == 0

    def test_skips_review_without_user_or_submitted_at(self, mocker):
        """Should skip reviews when user or submitted_at is missing."""
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
                    "user": None,
                    "state": "APPROVED",
                    "submitted_at": "2025-06-15T13:00:00Z",
                },
                {
                    "user": {"login": "reviewer"},
                    "state": "APPROVED",
                    "submitted_at": "",
                },
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
        assert len(approved_events) == 0

    def test_closed_pr_without_author(self, mocker):
        """Should handle closed PR when author is missing."""
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
            "author": None,
        }

        date_filter = DateFilter()
        events = fetch_pr_events_gh("test-org", "repo1", pr, date_filter)

        closed_events = [e for e in events if e["type"] == "closed"]
        assert len(closed_events) == 1
        assert closed_events[0]["person"] == "unknown"


class TestFetchPRCommentsGh:
    """Tests for fetch_pr_comments_gh function."""

    def test_returns_comments_list(self, mocker):
        """Should return list of comments."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"user": {"login": "reviewer"}, "body": "comment"},
            ],
        )

        comments = fetch_pr_comments_gh("test-org", "repo1", 1)

        assert len(comments) == 1
        assert comments[0]["user"]["login"] == "reviewer"

    def test_returns_empty_list_on_error(self, mocker):
        """Should return empty list when command fails."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            side_effect=GhCliError("Failed"),
        )

        comments = fetch_pr_comments_gh("test-org", "repo1", 1)

        assert comments == []

    def test_returns_empty_list_when_not_list(self, mocker):
        """Should return empty list when response is not a list."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value={"error": "unexpected"},
        )

        comments = fetch_pr_comments_gh("test-org", "repo1", 1)

        assert comments == []


class TestFetchPRIssueCommentsGh:
    """Tests for fetch_pr_issue_comments_gh function."""

    def test_returns_comments_list(self, mocker):
        """Should return list of issue comments."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"user": {"login": "commenter"}, "body": "discussion"},
            ],
        )

        comments = fetch_pr_issue_comments_gh("test-org", "repo1", 1)

        assert len(comments) == 1

    def test_returns_empty_list_on_error(self, mocker):
        """Should return empty list when command fails."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            side_effect=GhCliError("Failed"),
        )

        comments = fetch_pr_issue_comments_gh("test-org", "repo1", 1)

        assert comments == []


class TestFetchPRReviewsGh:
    """Tests for fetch_pr_reviews_gh function."""

    def test_returns_reviews_list(self, mocker):
        """Should return list of reviews."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"user": {"login": "reviewer"}, "state": "APPROVED"},
            ],
        )

        reviews = fetch_pr_reviews_gh("test-org", "repo1", 1)

        assert len(reviews) == 1

    def test_returns_empty_list_on_error(self, mocker):
        """Should return empty list when command fails."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            side_effect=GhCliError("Failed"),
        )

        reviews = fetch_pr_reviews_gh("test-org", "repo1", 1)

        assert reviews == []


class TestFetchRepoPRsGhAdditional:
    """Additional tests for fetch_repo_prs_gh function."""

    def test_yields_prs_without_created_at(self, mocker):
        """Should yield PRs even when createdAt is missing."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"number": 1, "title": "PR 1"},
            ],
        )

        date_filter = DateFilter(since=date(2025, 6, 1))
        prs = list(fetch_repo_prs_gh("test-org", "repo1", date_filter))

        assert len(prs) == 1

    def test_filters_prs_after_until_date(self, mocker):
        """Should filter out PRs created after until date."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            return_value=[
                {"number": 1, "title": "PR 1", "createdAt": "2025-12-15T10:00:00Z"},
            ],
        )

        date_filter = DateFilter(until=date(2025, 6, 30))
        prs = list(fetch_repo_prs_gh("test-org", "repo1", date_filter))

        assert len(prs) == 0


class TestFetchOrgReposGhAdditional:
    """Additional tests for fetch_org_repos_gh function."""

    def test_reraises_non_org_not_found_error(self, mocker):
        """Should re-raise errors that aren't organization-not-found."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher._run_gh_command",
            side_effect=GhCliError("Network error"),
        )

        with pytest.raises(GhCliError) as exc_info:
            list(fetch_org_repos_gh("test-org"))

        assert "Network error" in str(exc_info.value)


class TestFetchPRRecordGh:
    """Tests for fetch_pr_record_gh function."""

    def test_returns_pr_record_with_events(self, mocker):
        """Should return a PRRecord dict with events."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_events_gh",
            return_value=[
                {"type": "created", "date": "2025-06-15T10:00:00Z", "person": "author"},
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
        record = fetch_pr_record_gh("test-org", "repo1", pr, date_filter)

        assert record["number"] == 1
        assert record["title"] == "Test PR"
        assert len(record["events"]) == 1


class TestFetchOrganizationDataGh:
    """Tests for fetch_organization_data_gh function."""

    def test_yields_repos_with_prs(self, mocker):
        """Should yield repos that have PRs."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_org_repos_gh",
            return_value=["repo1", "repo2"],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_repo_prs_gh",
            side_effect=[
                iter([{"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z", "state": "OPEN", "author": {"login": "author"}}]),
                iter([]),
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_record_gh",
            return_value={
                "number": 1,
                "title": "PR 1",
                "events": [{"type": "created", "date": "2025-06-15T10:00:00Z", "person": "author"}],
            },
        )

        date_filter = DateFilter()
        results = list(fetch_organization_data_gh("test-org", date_filter))

        assert len(results) == 1
        assert results[0][0] == "repo1"
        assert len(results[0][1]) == 1

    def test_skips_filtered_repos(self, mocker):
        """Should skip repos that don't pass the filter."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_org_repos_gh",
            return_value=["repo1", "ignored-repo"],
        )
        mock_fetch_prs = mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_repo_prs_gh",
            return_value=iter([{"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z", "state": "OPEN", "author": {"login": "author"}}]),
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_record_gh",
            return_value={
                "number": 1,
                "title": "PR 1",
                "events": [{"type": "created", "date": "2025-06-15T10:00:00Z", "person": "author"}],
            },
        )

        date_filter = DateFilter()
        repo_filter = lambda name: not name.startswith("ignored")
        results = list(fetch_organization_data_gh("test-org", date_filter, repo_filter))

        assert len(results) == 1
        assert results[0][0] == "repo1"
        # fetch_repo_prs_gh should only be called for repo1
        assert mock_fetch_prs.call_count == 1

    def test_continues_on_fetch_error(self, mocker):
        """Should continue to next repo when fetching PRs fails."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_org_repos_gh",
            return_value=["repo1", "repo2"],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_repo_prs_gh",
            side_effect=[
                GhCliError("Failed to fetch"),
                iter([{"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z", "state": "OPEN", "author": {"login": "author"}}]),
            ],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_record_gh",
            return_value={
                "number": 1,
                "title": "PR 1",
                "events": [{"type": "created", "date": "2025-06-15T10:00:00Z", "person": "author"}],
            },
        )

        date_filter = DateFilter()
        results = list(fetch_organization_data_gh("test-org", date_filter))

        assert len(results) == 1
        assert results[0][0] == "repo2"

    def test_skips_prs_without_events(self, mocker):
        """Should skip PRs that have no events."""
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_org_repos_gh",
            return_value=["repo1"],
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_repo_prs_gh",
            return_value=iter([{"number": 1, "title": "PR 1", "createdAt": "2025-06-15T10:00:00Z", "state": "OPEN", "author": {"login": "author"}}]),
        )
        mocker.patch(
            "gh_pr_comments.gh_cli_fetcher.fetch_pr_record_gh",
            return_value={
                "number": 1,
                "title": "PR 1",
                "events": [],
            },
        )

        date_filter = DateFilter()
        results = list(fetch_organization_data_gh("test-org", date_filter))

        # Repo should not be yielded since its only PR has no events
        assert len(results) == 0
