"""Fetch PR data using GitHub CLI (gh) instead of PyGithub.

This module provides an alternative fetcher that uses subprocess calls to the
GitHub CLI tool. This can be useful for EMU (Enterprise Managed Users)
organizations where PyGithub may have authentication issues.
"""

import json
import logging
import subprocess
import time
from collections.abc import Iterator

from .models import DateFilter, PREvent, PRRecord

logger = logging.getLogger(__name__)


class GhCliError(Exception):
    """Raised when a gh CLI command fails."""


class RateLimitError(GhCliError):
    """Raised when GitHub rate limit is hit."""


def _is_rate_limit_error(error_msg: str) -> bool:
    """Check if error message indicates a rate limit."""
    rate_limit_indicators = [
        "rate limit",
        "API rate limit",
        "secondary rate limit",
        "abuse detection",
        "403",
        "retry-after",
    ]
    error_lower = error_msg.lower()
    return any(indicator.lower() in error_lower for indicator in rate_limit_indicators)


def _run_gh_command(args: list[str], max_retries: int = 3) -> dict | list:
    """Run a gh command and return parsed JSON output with rate limit handling."""
    cmd = ["gh"] + args
    logger.debug(f"Running: {' '.join(cmd)}")

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                return []

            return json.loads(result.stdout)

        except FileNotFoundError as e:
            raise GhCliError("GitHub CLI (gh) not found. Install from https://cli.github.com/") from e
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)

            if _is_rate_limit_error(error_msg):
                if attempt < max_retries - 1:
                    wait_seconds = min(60 * (2 ** attempt), 300)
                    logger.warning(f"Rate limit hit. Waiting {wait_seconds}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_seconds)
                    continue
                raise RateLimitError(f"Rate limit exceeded after {max_retries} retries") from e

            raise GhCliError(f"gh command failed: {error_msg}") from e
        except json.JSONDecodeError as e:
            raise GhCliError(f"Failed to parse gh output: {e}") from e

    return []


def fetch_org_repos_gh(org_name: str) -> Iterator[str]:
    """Fetch all repository names in an organization using gh CLI."""
    logger.info(f"Fetching repositories for: {org_name}")

    try:
        repos = _run_gh_command([
            "repo", "list", org_name,
            "--json", "name",
            "--limit", "10000",
        ])
    except GhCliError as e:
        if "Could not resolve to an Organization" in str(e):
            raise GhCliError(f"Organization '{org_name}' not found") from e
        raise

    for repo in repos:
        logger.debug(f"Found repo: {repo['name']}")
        yield repo["name"]


def fetch_repo_prs_gh(
    org_name: str,
    repo_name: str,
    date_filter: DateFilter,
) -> Iterator[dict]:
    """Fetch PRs from a repository using gh CLI."""
    logger.info(f"Fetching PRs for: {repo_name}")

    full_repo = f"{org_name}/{repo_name}"

    prs = _run_gh_command([
        "pr", "list",
        "--repo", full_repo,
        "--state", "all",
        "--json", "number,title,createdAt,closedAt,mergedAt,state,author,mergedBy",
        "--limit", "10000",
    ])

    for pr in prs:
        created_at = pr.get("createdAt", "")
        if created_at:
            created_date_str = created_at[:10]  # YYYY-MM-DD
            from datetime import date as date_cls
            created_date = date_cls.fromisoformat(created_date_str)

            if date_filter.until and created_date > date_filter.until:
                continue
            if date_filter.since and created_date < date_filter.since:
                continue

        logger.debug(f"Found PR #{pr['number']}: {pr['title']}")
        yield pr


def fetch_pr_comments_gh(org_name: str, repo_name: str, pr_number: int) -> list[dict]:
    """Fetch review comments for a PR using gh API."""
    full_repo = f"{org_name}/{repo_name}"

    try:
        comments = _run_gh_command([
            "api",
            f"repos/{full_repo}/pulls/{pr_number}/comments",
            "--paginate",
        ])
        return comments if isinstance(comments, list) else []
    except GhCliError as e:
        logger.warning(f"Failed to fetch review comments for PR #{pr_number}: {e}")
        return []


def fetch_pr_issue_comments_gh(org_name: str, repo_name: str, pr_number: int) -> list[dict]:
    """Fetch issue comments for a PR using gh API."""
    full_repo = f"{org_name}/{repo_name}"

    try:
        comments = _run_gh_command([
            "api",
            f"repos/{full_repo}/issues/{pr_number}/comments",
            "--paginate",
        ])
        return comments if isinstance(comments, list) else []
    except GhCliError as e:
        logger.warning(f"Failed to fetch issue comments for PR #{pr_number}: {e}")
        return []


def fetch_pr_reviews_gh(org_name: str, repo_name: str, pr_number: int) -> list[dict]:
    """Fetch reviews for a PR using gh API."""
    full_repo = f"{org_name}/{repo_name}"

    try:
        reviews = _run_gh_command([
            "api",
            f"repos/{full_repo}/pulls/{pr_number}/reviews",
            "--paginate",
        ])
        return reviews if isinstance(reviews, list) else []
    except GhCliError as e:
        logger.warning(f"Failed to fetch reviews for PR #{pr_number}: {e}")
        return []


def fetch_pr_events_gh(
    org_name: str,
    repo_name: str,
    pr: dict,
    date_filter: DateFilter,
) -> list[PREvent]:
    """Fetch all events for a PR as a chronological list using gh CLI."""
    from datetime import datetime

    events: list[PREvent] = []
    pr_number = pr["number"]

    # Event: created
    author = pr.get("author", {})
    if author and author.get("login"):
        events.append({
            "type": "created",
            "date": pr["createdAt"],
            "person": author["login"],
        })

    # Events: review comments (inline code comments)
    for comment in fetch_pr_comments_gh(org_name, repo_name, pr_number):
        user = comment.get("user", {})
        created_at = comment.get("created_at", "")
        if user and user.get("login") and created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if date_filter.contains(dt):
                events.append({
                    "type": "comment",
                    "date": created_at,
                    "person": user["login"],
                })

    # Events: issue comments (general PR conversation)
    for comment in fetch_pr_issue_comments_gh(org_name, repo_name, pr_number):
        user = comment.get("user", {})
        created_at = comment.get("created_at", "")
        if user and user.get("login") and created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if date_filter.contains(dt):
                events.append({
                    "type": "comment",
                    "date": created_at,
                    "person": user["login"],
                })

    # Events: reviews (approvals, changes requested, and comments)
    for review in fetch_pr_reviews_gh(org_name, repo_name, pr_number):
        user = review.get("user", {})
        submitted_at = review.get("submitted_at", "")
        state = review.get("state", "")
        body = review.get("body", "")
        if not user or not user.get("login") or not submitted_at:
            continue

        # Capture approval/changes_requested regardless of date filter
        if state == "APPROVED":
            events.append({
                "type": "approved",
                "date": submitted_at,
                "person": user["login"],
            })
        elif state == "CHANGES_REQUESTED":
            events.append({
                "type": "changes_requested",
                "date": submitted_at,
                "person": user["login"],
            })

        # Capture review body as comment (date filtered)
        if body:
            dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            if date_filter.contains(dt):
                events.append({
                    "type": "comment",
                    "date": submitted_at,
                    "person": user["login"],
                })

    # Event: merged or closed
    state = pr.get("state", "").upper()
    if state == "MERGED":
        merged_by = pr.get("mergedBy", {})
        merged_at = pr.get("mergedAt", "")
        if merged_by and merged_by.get("login") and merged_at:
            events.append({
                "type": "merged",
                "date": merged_at,
                "person": merged_by["login"],
            })
    elif state == "CLOSED":
        closed_at = pr.get("closedAt", "")
        author = pr.get("author", {})
        if closed_at:
            events.append({
                "type": "closed",
                "date": closed_at,
                "person": author.get("login", "unknown") if author else "unknown",
            })

    # Sort by date
    events.sort(key=lambda e: e["date"])

    return events


def fetch_pr_record_gh(
    org_name: str,
    repo_name: str,
    pr: dict,
    date_filter: DateFilter,
) -> PRRecord:
    """Fetch a complete PR record with all events using gh CLI."""
    events = fetch_pr_events_gh(org_name, repo_name, pr, date_filter)
    return {
        "number": pr["number"],
        "title": pr["title"],
        "events": events,
    }


def fetch_organization_data_gh(
    org_name: str,
    date_filter: DateFilter,
    repo_filter: callable = None,
) -> Iterator[tuple[str, list[PRRecord]]]:
    """Fetch all PR data from all repos in an organization using gh CLI.

    Yields (repo_name, prs) tuples as each repository is processed.

    Args:
        org_name: GitHub organization name
        date_filter: Date range filter for PRs
        repo_filter: Optional callable(repo_name) -> bool, returns True if repo should be processed
    """
    for repo_name in fetch_org_repos_gh(org_name):
        # Skip repos that don't pass the filter
        if repo_filter and not repo_filter(repo_name):
            logger.info(f"Skipping filtered repository: {repo_name}")
            continue

        prs: list[PRRecord] = []

        try:
            for pr in fetch_repo_prs_gh(org_name, repo_name, date_filter):
                pr_record = fetch_pr_record_gh(org_name, repo_name, pr, date_filter)
                if pr_record["events"]:  # Only include PRs with events
                    prs.append(pr_record)
                    logger.debug(f"PR #{pr['number']}: {len(pr_record['events'])} events")
        except GhCliError as e:
            logger.warning(f"Failed to fetch PRs for {repo_name}: {e}")
            continue

        if prs:
            logger.info(f"{repo_name}: {len(prs)} PRs")
            yield repo_name, prs
