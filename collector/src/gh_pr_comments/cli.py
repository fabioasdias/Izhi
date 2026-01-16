"""Command-line interface for gh-pr-comments."""

import fnmatch
import json
import logging
import signal
import sys
from datetime import date, datetime, timezone

import click
from dotenv import load_dotenv

from .auth import (
    AuthenticationError,
    get_github_client_from_app,
    get_github_client_from_token,
    get_github_client_unauthenticated,
)
from .fetcher import FetchError, fetch_organization_data
from .gh_cli_fetcher import GhCliError, fetch_organization_data_gh
from .models import DateFilter

load_dotenv()

logger = logging.getLogger(__name__)


def parse_date(ctx: click.Context, param: click.Parameter, value: str | None) -> date | None:
    """Parse a date string in YYYY-MM-DD format."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise click.BadParameter(f"Invalid date format. Use YYYY-MM-DD: {e}") from e


@click.command()
@click.option("--org", required=True, help="GitHub organization name")
@click.option("--output", "-o", type=click.Path(dir_okay=False, writable=True), help="Output JSON file")
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub Personal Access Token")
@click.option("--app-id", type=int, envvar="GITHUB_APP_ID", help="GitHub App ID")
@click.option("--private-key", type=click.Path(exists=True), envvar="GITHUB_APP_PRIVATE_KEY", help="GitHub App private key")
@click.option("--installation-id", type=int, envvar="GITHUB_APP_INSTALLATION_ID", help="GitHub App installation ID")
@click.option("--since", callback=parse_date, help="Start date (YYYY-MM-DD)")
@click.option("--until", callback=parse_date, help="End date (YYYY-MM-DD)")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--use-gh-cli", is_flag=True, default=False, help="Use gh CLI instead of PyGithub (useful for EMU orgs)")
@click.option("--include-repo", multiple=True, help="Only include repos matching pattern, supports wildcards like '*api*' (can be repeated)")
@click.option("--ignore-repo", multiple=True, help="Exclude repos matching pattern, supports wildcards like '*test*' (can be repeated)")
def main(
    org: str,
    output: str | None,
    token: str | None,
    app_id: int | None,
    private_key: str | None,
    installation_id: int | None,
    since: date | None,
    until: date | None,
    verbose: bool,
    use_gh_cli: bool,
    include_repo: tuple[str, ...],
    ignore_repo: tuple[str, ...],
) -> None:
    """Fetch PR events from a GitHub organization."""
    # Configure logging
    log_file = f"{org}.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(file_handler)

    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        root_logger.addHandler(console_handler)

    if output is None:
        output = f"{org}.json"

    # Authentication (not needed for gh CLI mode)
    client = None
    if not use_gh_cli:
        has_token = token is not None
        has_app_auth = all([app_id, private_key, installation_id])

        if any([app_id, private_key, installation_id]) and not has_app_auth:
            click.echo("Error: GitHub App auth requires --app-id, --private-key, and --installation-id", err=True)
            sys.exit(1)

        try:
            if has_app_auth:
                logger.info("Authenticating with GitHub App")
                client = get_github_client_from_app(app_id, private_key, installation_id)
            elif has_token:
                logger.info("Authenticating with Personal Access Token")
                client = get_github_client_from_token(token)
            else:
                logger.info("Using unauthenticated access (60 req/hr limit)")
                client = get_github_client_unauthenticated()
        except AuthenticationError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        logger.info("Using gh CLI for data fetching")

    # Date filter
    date_filter = DateFilter(since=since, until=until)
    if since or until:
        logger.info(f"Date filter: {since or 'start'} to {until or 'now'}")

    # Repository filter patterns
    include_patterns = list(include_repo)
    exclude_patterns = list(ignore_repo)

    if include_patterns:
        logger.info(f"Including only repositories matching: {', '.join(include_patterns)}")
    if exclude_patterns:
        logger.info(f"Excluding repositories matching: {', '.join(exclude_patterns)}")

    def should_process_repo(repo_name: str) -> bool:
        """Check if a repository should be processed based on include/exclude patterns."""
        # If include patterns specified, repo must match at least one
        if include_patterns:
            if not any(fnmatch.fnmatch(repo_name, p) for p in include_patterns):
                return False
        # If exclude patterns specified, repo must not match any
        if exclude_patterns:
            if any(fnmatch.fnmatch(repo_name, p) for p in exclude_patterns):
                return False
        return True

    # Build report structure
    report = {
        "organization": org,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_range": {
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        },
        "repositories": {},
    }

    def save_report() -> None:
        """Save current report to file."""
        with open(output, "w") as f:
            json.dump(report, f, indent=2)

    # Track if we were interrupted
    interrupted = False

    def handle_interrupt(signum: int, frame) -> None:
        """Handle Ctrl+C by setting interrupted flag."""
        nonlocal interrupted
        interrupted = True
        logger.info("Interrupt received, finishing current operation...")
        click.echo("\nInterrupt received, saving progress...", err=True)

    # Set up signal handler for graceful shutdown
    original_handler = signal.signal(signal.SIGINT, handle_interrupt)

    # Fetch data, saving after each repository
    logger.info(f"Fetching PR data for: {org}")
    try:
        if use_gh_cli:
            data_iterator = fetch_organization_data_gh(org, date_filter, should_process_repo)
        else:
            data_iterator = fetch_organization_data(client, org, date_filter, should_process_repo)

        for repo_name, prs in data_iterator:
            if interrupted:
                break
            report["repositories"][repo_name] = prs
            report["generated_at"] = datetime.now(timezone.utc).isoformat()
            save_report()
            logger.info(f"Saved progress: {len(report['repositories'])} repos")
    except (FetchError, GhCliError) as e:
        click.echo(f"Error: {e}", err=True)
        save_report()
        logger.info(f"Partial report saved to: {output}")
        sys.exit(1)
    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_handler)

    if interrupted:
        logger.info(f"Interrupted. Partial report saved to: {output}")
        click.echo(f"Partial report saved to: {output}", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    else:
        logger.info(f"Report written to: {output}")


if __name__ == "__main__":
    main()
