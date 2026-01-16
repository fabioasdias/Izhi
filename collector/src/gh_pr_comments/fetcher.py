"""Fetch PR data from GitHub API."""

import logging
import time
from collections.abc import Iterator

from github import Github, GithubException, RateLimitExceededException
from github.PullRequest import PullRequest
from github.Repository import Repository

from .models import DateFilter, PREvent, PRRecord

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when fetching data from GitHub fails."""


def _handle_rate_limit(attempt: int, max_retries: int = 3) -> None:
    """Handle rate limit with exponential backoff."""
    if attempt >= max_retries:
        raise FetchError("Rate limit exceeded and max retries reached")

    wait_seconds = min(60 * (2 ** attempt), 900)
    logger.warning(f"Rate limit hit. Waiting {wait_seconds}s (attempt {attempt + 1}/{max_retries})")
    time.sleep(wait_seconds)


def fetch_org_repos(client: Github, org_name: str) -> Iterator[Repository]:
    """Fetch all repositories in an organization."""
    try:
        org = client.get_organization(org_name)
    except GithubException as e:
        if e.status == 404:
            raise FetchError(f"Organization '{org_name}' not found") from e
        raise FetchError(f"Failed to access organization: {e}") from e

    logger.info(f"Fetching repositories for: {org_name}")
    for repo in org.get_repos():
        logger.debug(f"Found repo: {repo.name}")
        yield repo


def fetch_repo_prs(
    repo: Repository,
    date_filter: DateFilter,
) -> Iterator[PullRequest]:
    """Fetch PRs from a repository within date range."""
    logger.info(f"Fetching PRs for: {repo.name}")

    for pr in repo.get_pulls(state="all", sort="created", direction="desc"):
        # Skip PRs after until date
        if date_filter.until and pr.created_at.date() > date_filter.until:
            continue

        # Stop at PRs before since date
        if date_filter.since and pr.created_at.date() < date_filter.since:
            logger.debug(f"Reached PRs older than {date_filter.since}, stopping")
            break

        logger.debug(f"Found PR #{pr.number}: {pr.title}")
        yield pr


def fetch_pr_events(pr: PullRequest, date_filter: DateFilter) -> list[PREvent]:
    """Fetch all events for a PR as a chronological list."""
    events: list[PREvent] = []
    max_retries = 3

    # Event: created
    if pr.user:
        events.append({
            "type": "created",
            "date": pr.created_at.isoformat(),
            "person": pr.user.login,
        })

    # Events: review comments (inline code comments)
    for attempt in range(max_retries):
        try:
            for comment in pr.get_review_comments():
                if comment.user and date_filter.contains(comment.created_at):
                    events.append({
                        "type": "comment",
                        "date": comment.created_at.isoformat(),
                        "person": comment.user.login,
                    })
            break
        except RateLimitExceededException:
            _handle_rate_limit(attempt, max_retries)

    # Events: issue comments (general PR conversation)
    for attempt in range(max_retries):
        try:
            for comment in pr.get_issue_comments():
                if comment.user and date_filter.contains(comment.created_at):
                    events.append({
                        "type": "comment",
                        "date": comment.created_at.isoformat(),
                        "person": comment.user.login,
                    })
            break
        except RateLimitExceededException:
            _handle_rate_limit(attempt, max_retries)

    # Events: review body comments
    for attempt in range(max_retries):
        try:
            for review in pr.get_reviews():
                if review.user and review.body and date_filter.contains(review.submitted_at):
                    events.append({
                        "type": "comment",
                        "date": review.submitted_at.isoformat(),
                        "person": review.user.login,
                    })
            break
        except RateLimitExceededException:
            _handle_rate_limit(attempt, max_retries)

    # Event: merged or closed
    if pr.state == "closed":
        if pr.merged and pr.merged_by:
            events.append({
                "type": "merged",
                "date": pr.merged_at.isoformat() if pr.merged_at else pr.closed_at.isoformat(),
                "person": pr.merged_by.login,
            })
        elif pr.closed_at:
            # GitHub doesn't expose who closed a non-merged PR without timeline API
            # Use the PR author as fallback
            events.append({
                "type": "closed",
                "date": pr.closed_at.isoformat(),
                "person": pr.user.login if pr.user else "unknown",
            })

    # Sort by date
    events.sort(key=lambda e: e["date"])

    return events


def fetch_pr_record(pr: PullRequest, date_filter: DateFilter) -> PRRecord:
    """Fetch a complete PR record with all events."""
    events = fetch_pr_events(pr, date_filter)
    return {
        "number": pr.number,
        "title": pr.title,
        "events": events,
    }


def fetch_organization_data(
    client: Github,
    org_name: str,
    date_filter: DateFilter,
) -> Iterator[tuple[str, list[PRRecord]]]:
    """Fetch all PR data from all repos in an organization.

    Yields (repo_name, prs) tuples as each repository is processed.
    """
    for repo in fetch_org_repos(client, org_name):
        prs: list[PRRecord] = []

        try:
            for pr in fetch_repo_prs(repo, date_filter):
                pr_record = fetch_pr_record(pr, date_filter)
                if pr_record["events"]:  # Only include PRs with events
                    prs.append(pr_record)
                    logger.debug(f"PR #{pr.number}: {len(pr_record['events'])} events")
        except GithubException as e:
            logger.warning(f"Failed to fetch PRs for {repo.name}: {e}")
            continue

        if prs:
            logger.info(f"{repo.name}: {len(prs)} PRs")
            yield repo.name, prs
