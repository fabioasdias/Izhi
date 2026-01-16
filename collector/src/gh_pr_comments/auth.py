"""GitHub authentication handlers for PAT and GitHub App."""

from pathlib import Path

from github import Auth, Github, GithubException, GithubIntegration


class AuthenticationError(Exception):
    """Raised when GitHub authentication fails."""


def get_github_client_unauthenticated() -> Github:
    """
    Create an unauthenticated GitHub client for public repo access.

    Note: Rate limited to 60 requests/hour.

    Returns:
        Unauthenticated Github client
    """
    return Github()


def get_github_client_from_token(token: str) -> Github:
    """
    Create a GitHub client using a Personal Access Token.

    Args:
        token: GitHub Personal Access Token

    Returns:
        Authenticated Github client

    Raises:
        AuthenticationError: If authentication fails
    """
    auth = Auth.Token(token)
    client = Github(auth=auth)

    try:
        # Verify the token works by fetching the authenticated user
        client.get_user().login
    except GithubException as e:
        raise AuthenticationError(f"Failed to authenticate with token: {e.data.get('message', str(e))}") from e

    return client


def get_github_client_from_app(
    app_id: int,
    private_key_path: str,
    installation_id: int,
) -> Github:
    """
    Create a GitHub client using GitHub App authentication.

    Args:
        app_id: GitHub App ID
        private_key_path: Path to the GitHub App private key PEM file
        installation_id: GitHub App installation ID

    Returns:
        Authenticated Github client

    Raises:
        AuthenticationError: If authentication fails
        FileNotFoundError: If private key file doesn't exist
    """
    key_path = Path(private_key_path)
    if not key_path.exists():
        raise FileNotFoundError(f"Private key file not found: {private_key_path}")

    private_key = key_path.read_text()

    try:
        auth = Auth.AppAuth(app_id, private_key)
        integration = GithubIntegration(auth=auth)
        installation_auth = integration.get_access_token(installation_id)
        client = Github(auth=Auth.Token(installation_auth.token))

        # Verify the client works
        client.get_user().login
    except GithubException as e:
        raise AuthenticationError(
            f"Failed to authenticate with GitHub App: {e.data.get('message', str(e))}"
        ) from e
    except Exception as e:
        raise AuthenticationError(f"Failed to authenticate with GitHub App: {e}") from e

    return client
