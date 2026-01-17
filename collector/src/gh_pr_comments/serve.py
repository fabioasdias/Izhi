"""HTTP server for the embedded dashboard."""

import http.server
import socketserver
import sys
import webbrowser
from functools import partial
from importlib.resources import files
from pathlib import Path

import click


def get_dashboard_path() -> Path:
    """Get path to embedded dashboard files."""
    return Path(str(files("gh_pr_comments").joinpath("dashboard")))


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, dashboard_path: Path, **kwargs):
        super().__init__(*args, directory=str(dashboard_path), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def serve_dashboard(port: int, no_browser: bool) -> None:
    """Serve dashboard on specified port."""
    dashboard_path = get_dashboard_path()

    if not (dashboard_path / "index.html").exists():
        raise FileNotFoundError(
            "Dashboard not found. Install from PyPI: pip install izhi"
        )

    handler = partial(DashboardHandler, dashboard_path=dashboard_path)

    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"Dashboard: {url}")
        print("Ctrl+C to stop")

        if not no_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped")


@click.command()
@click.option("--port", "-p", default=8080, help="Port (default: 8080)")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
def main(port: int, no_browser: bool) -> None:
    """Serve the Izhi dashboard."""
    try:
        serve_dashboard(port, no_browser)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except OSError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
