"""Command-line interface for gh-pr-comments."""

import json
import logging
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

    # Authentication
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

    # Date filter
    date_filter = DateFilter(since=since, until=until)
    if since or until:
        logger.info(f"Date filter: {since or 'start'} to {until or 'now'}")

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

    # Fetch data, saving after each repository
    logger.info(f"Fetching PR data for: {org}")
    try:
        for repo_name, prs in fetch_organization_data(client, org, date_filter):
            report["repositories"][repo_name] = prs
            report["generated_at"] = datetime.now(timezone.utc).isoformat()
            save_report()
            logger.info(f"Saved progress: {len(report['repositories'])} repos")
    except FetchError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    logger.info(f"Report written to: {output}")


if __name__ == "__main__":
    main()
