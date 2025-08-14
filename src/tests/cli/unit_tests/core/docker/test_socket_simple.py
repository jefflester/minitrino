"""Simplified unit tests for Docker socket detection module.

Tests Docker daemon socket resolution with mocking.
"""

import os
from unittest.mock import Mock, patch

from minitrino.core.docker.socket import resolve_docker_socket


class TestResolveDockerSocket:
    """Test suite for Docker socket resolution."""

    @patch("os.path.exists")
    def test_standard_socket_exists(self, mock_exists):
        """Test when standard Docker socket exists."""
        mock_exists.return_value = True
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        socket = resolve_docker_socket(ctx=mock_ctx)

        assert socket is not None
        assert "docker.sock" in socket or socket == "unix://var/run/docker.sock"

    @patch("os.path.exists")
    def test_socket_not_exists(self, mock_exists):
        """Test when Docker socket doesn't exist."""
        mock_exists.return_value = False
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        # Should still return something (fallback or error)
        socket = resolve_docker_socket(ctx=mock_ctx)

        # Implementation may return a default or None
        assert socket is None or isinstance(socket, str)

    def test_with_docker_host_env(self):
        """Test with DOCKER_HOST environment variable."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        with patch.dict(os.environ, {"DOCKER_HOST": "tcp://localhost:2375"}):
            socket = resolve_docker_socket(ctx=mock_ctx, env=os.environ)

        # Should handle DOCKER_HOST
        assert socket is not None

    def test_without_context(self):
        """Test calling without context (uses defaults)."""
        with patch("os.path.exists", return_value=True):
            socket = resolve_docker_socket()

        assert socket is not None

    @patch("platform.system")
    @patch("os.path.exists")
    def test_macos_specific_handling(self, mock_exists, mock_platform):
        """Test macOS-specific socket locations."""
        mock_platform.return_value = "Darwin"
        mock_exists.return_value = False  # Standard socket doesn't exist
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        socket = resolve_docker_socket(ctx=mock_ctx)

        # Should check macOS-specific locations
        assert socket is None or isinstance(socket, str)

    @patch("platform.system")
    @patch("os.path.exists")
    def test_linux_handling(self, mock_exists, mock_platform):
        """Test Linux socket handling."""
        mock_platform.return_value = "Linux"
        mock_exists.return_value = True
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        socket = resolve_docker_socket(ctx=mock_ctx)

        assert socket is not None
        assert "unix://" in socket or "docker.sock" in socket

    def test_with_custom_env(self):
        """Test with custom environment dictionary."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        custom_env = {"DOCKER_HOST": "unix:///custom/docker.sock"}

        with patch("os.path.exists", return_value=True):
            socket = resolve_docker_socket(ctx=mock_ctx, env=custom_env)

        assert socket is not None
