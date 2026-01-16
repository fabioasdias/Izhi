"""Tests for authentication module."""

import pytest
from unittest.mock import MagicMock, patch

from gh_pr_comments.auth import (
    AuthenticationError,
    get_github_client_from_token,
    get_github_client_from_app,
)


class TestGetGithubClientFromToken:
    """Tests for PAT authentication."""

    def test_valid_token_returns_client(self):
        """Valid token should return an authenticated client."""
        with patch("gh_pr_comments.auth.Github") as mock_github:
            mock_client = MagicMock()
            mock_client.get_user.return_value.login = "testuser"
            mock_github.return_value = mock_client

            client = get_github_client_from_token("valid_token")

            assert client == mock_client
            mock_client.get_user.assert_called_once()

    def test_invalid_token_raises_auth_error(self):
        """Invalid token should raise AuthenticationError."""
        from github import GithubException

        with patch("gh_pr_comments.auth.Github") as mock_github:
            mock_client = MagicMock()
            mock_client.get_user.side_effect = GithubException(
                status=401,
                data={"message": "Bad credentials"},
                headers={},
            )
            mock_github.return_value = mock_client

            with pytest.raises(AuthenticationError) as exc_info:
                get_github_client_from_token("invalid_token")

            assert "Bad credentials" in str(exc_info.value)


class TestGetGithubClientFromApp:
    """Tests for GitHub App authentication."""

    def test_missing_private_key_file_raises_error(self, tmp_path):
        """Missing private key file should raise FileNotFoundError."""
        nonexistent_path = str(tmp_path / "nonexistent.pem")

        with pytest.raises(FileNotFoundError) as exc_info:
            get_github_client_from_app(
                app_id=12345,
                private_key_path=nonexistent_path,
                installation_id=67890,
            )

        assert "not found" in str(exc_info.value)

    def test_valid_app_credentials_returns_client(self, tmp_path):
        """Valid app credentials should return an authenticated client."""
        # Create a mock private key file
        key_file = tmp_path / "private-key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----")

        with patch("gh_pr_comments.auth.GithubIntegration") as mock_integration, \
             patch("gh_pr_comments.auth.Github") as mock_github, \
             patch("gh_pr_comments.auth.Auth") as mock_auth:

            mock_token = MagicMock()
            mock_token.token = "installation_token"
            mock_integration.return_value.get_access_token.return_value = mock_token

            mock_client = MagicMock()
            mock_client.get_user.return_value.login = "app[bot]"
            mock_github.return_value = mock_client

            client = get_github_client_from_app(
                app_id=12345,
                private_key_path=str(key_file),
                installation_id=67890,
            )

            assert client == mock_client

    def test_invalid_app_credentials_raises_auth_error(self, tmp_path):
        """Invalid app credentials should raise AuthenticationError."""
        from github import GithubException

        key_file = tmp_path / "private-key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----")

        with patch("gh_pr_comments.auth.GithubIntegration") as mock_integration, \
             patch("gh_pr_comments.auth.Auth"):

            mock_integration.return_value.get_access_token.side_effect = GithubException(
                status=401,
                data={"message": "Invalid app credentials"},
                headers={},
            )

            with pytest.raises(AuthenticationError) as exc_info:
                get_github_client_from_app(
                    app_id=12345,
                    private_key_path=str(key_file),
                    installation_id=67890,
                )

            assert "Invalid app credentials" in str(exc_info.value)
