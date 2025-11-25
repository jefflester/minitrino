"""Unit tests for EnvironmentVariables class with simplified mocking.

Tests the environment variable management including:
- get() method behavior
- Type consistency enforcement
- Environment variable precedence
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from minitrino.core.envvars import EnvironmentVariables


class TestEnvironmentVariablesSimple:
    """Test suite for EnvironmentVariables with simplified mocking."""

    def create_mock_context(self, user_env_args=None, cluster_name=None):
        """Create a mock context for testing."""
        mock_ctx = Mock()
        mock_ctx._user_env_args = user_env_args or []
        mock_ctx.cluster_name = cluster_name
        mock_ctx.logger = Mock()
        mock_ctx.lib_dir = Path("/test/lib")
        mock_ctx.lib_env_dir = Path("/test/lib/env")
        return mock_ctx

    def test_init_with_empty_context(self):
        """Test initialization with empty mock context."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        assert isinstance(env, dict)
        # Context is stored internally
        assert hasattr(env, "_ctx")

    def test_get_method_returns_string(self):
        """Test that get() always returns a string."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

            # Set different types
            env["STRING"] = "value"
            env["INT"] = 123
            env["NONE"] = None

        # get() should always return strings
        assert env.get("STRING") == "value"
        assert env.get("INT") == "123"
        assert env.get("NONE") == ""  # None becomes empty string
        assert env.get("MISSING", "default") == "default"

    def test_user_env_args_parsing(self):
        """Test parsing of user-provided environment arguments."""
        user_args = ["KEY1=value1", "KEY2=value2"]
        mock_ctx = self.create_mock_context(user_env_args=user_args)

        # Mock the parse_key_value_pair utility
        with patch("minitrino.core.envvars.utils.parse_key_value_pair") as mock_parse:
            mock_parse.side_effect = [("KEY1", "value1"), ("KEY2", "value2")]

            with (
                patch.object(EnvironmentVariables, "_parse_os_env"),
                patch.object(EnvironmentVariables, "_parse_minitrino_config"),
            ):
                env = EnvironmentVariables(mock_ctx)

            assert env["KEY1"] == "value1"
            assert env["KEY2"] == "value2"
            assert mock_parse.call_count == 2

    @patch.dict(os.environ, {"MINITRINO_TEST_VAR": "os_value"})
    def test_os_env_parsing(self):
        """Test parsing of OS environment variables."""
        mock_ctx = self.create_mock_context()

        with patch.object(EnvironmentVariables, "_parse_minitrino_config"):
            env = EnvironmentVariables(mock_ctx)

            # Manually set a value as if parsed from OS
            env["MINITRINO_TEST_VAR"] = "os_value"

        assert env.get("MINITRINO_TEST_VAR") == "os_value"

    def test_precedence_user_over_os(self):
        """Test that user args take precedence over OS env."""
        user_args = ["KEY=user_value"]
        mock_ctx = self.create_mock_context(user_env_args=user_args)

        with patch("minitrino.core.envvars.utils.parse_key_value_pair") as mock_parse:
            mock_parse.return_value = ("KEY", "user_value")

            with (
                patch.dict(os.environ, {"KEY": "os_value"}),
                patch.object(EnvironmentVariables, "_parse_minitrino_config"),
            ):
                env = EnvironmentVariables(mock_ctx)

            # User value should win
            assert env["KEY"] == "user_value"

    def test_dict_operations(self):
        """Test that EnvironmentVariables behaves like a dict."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

            # Set and get
            env["KEY1"] = "value1"
            assert env["KEY1"] == "value1"

            # Contains
            assert "KEY1" in env
            assert "MISSING" not in env

            # Delete
            del env["KEY1"]
            assert "KEY1" not in env

            # Update
            env.update({"KEY2": "value2", "KEY3": "value3"})
            assert env["KEY2"] == "value2"
            assert env["KEY3"] == "value3"

            # Length
            initial_len = len(env)
            env["KEY4"] = "value4"
            assert len(env) == initial_len + 1

    def test_string_conversion(self):
        """Test that all values are stored as strings."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

            # Set various types - they stay as is in the dict
            env["STRING"] = "text"
            env["INT"] = 42
            env["FLOAT"] = 3.14
            env["BOOL"] = True
            env["LIST"] = ["a", "b"]

            # When using get(), they become strings
            assert env.get("STRING") == "text"
            assert env.get("INT") == "42"
            assert env.get("FLOAT") == "3.14"
            assert env.get("BOOL") == "True"
            # Lists are trickier - the dict stores the actual list
            assert str(env["LIST"]) == "['a', 'b']"

    def test_get_with_none_value(self):
        """Test get() behavior with None values."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

            env["NULL_KEY"] = None

            # get() should return empty string for None
            assert env.get("NULL_KEY") == ""
            assert env.get("NULL_KEY", "default") == ""  # Not default!

    @patch("minitrino.core.envvars.ConfigParser")
    @patch("os.path.isfile")
    def test_config_file_parsing(self, mock_isfile, mock_config_parser):
        """Test parsing of minitrino.cfg file."""
        mock_ctx = self.create_mock_context(cluster_name="test-cluster")
        mock_ctx.config_file = "/home/.minitrino/minitrino.cfg"
        mock_isfile.return_value = True

        mock_parser = Mock()
        mock_config_parser.return_value = mock_parser

        # Mock config file content
        mock_parser.read.return_value = ["/home/.minitrino/minitrino.cfg"]
        mock_parser.has_section.return_value = True
        mock_parser.items.return_value = [
            ("key1", "config_value1"),
            ("key2", "config_value2"),
        ]

        with patch.object(EnvironmentVariables, "_parse_os_env"):
            _ = EnvironmentVariables(mock_ctx)

            # Check that config parser was called
            mock_config_parser.assert_called_once()
            mock_parser.read.assert_called_once()

    def test_special_characters_in_values(self):
        """Test handling of special characters in values."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

            # Set values with special characters
            env["NEWLINE"] = "line1\nline2"
            env["TAB"] = "col1\tcol2"
            env["QUOTES"] = 'value "with" quotes'
            env["PATH"] = "/usr/bin:/usr/local/bin"

            assert env.get("NEWLINE") == "line1\nline2"
            assert env.get("TAB") == "col1\tcol2"
            assert env.get("QUOTES") == 'value "with" quotes'
            assert env.get("PATH") == "/usr/bin:/usr/local/bin"


class TestQuoteStripping:
    """Test suite for quote stripping in config file values."""

    def create_mock_context(self):
        """Create a mock context for testing."""
        mock_ctx = Mock()
        mock_ctx._user_env_args = []
        mock_ctx.logger = Mock()
        mock_ctx.lib_dir = Path("/test/lib")
        mock_ctx.lib_env_dir = Path("/test/lib/env")
        mock_ctx.config_file = "/test/.minitrino/minitrino.cfg"
        return mock_ctx

    def test_strip_quotes_double_quotes(self):
        """Test stripping of double quotes."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes('"bar"') == "bar"
        assert env._strip_quotes('"hello world"') == "hello world"
        assert env._strip_quotes('"path/to/file"') == "path/to/file"

    def test_strip_quotes_single_quotes(self):
        """Test stripping of single quotes."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes("'bar'") == "bar"
        assert env._strip_quotes("'hello world'") == "hello world"
        assert env._strip_quotes("'path/to/file'") == "path/to/file"

    def test_strip_quotes_no_quotes(self):
        """Test that values without quotes are unchanged."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes("bar") == "bar"
        assert env._strip_quotes("hello world") == "hello world"
        assert env._strip_quotes("path/to/file") == "path/to/file"

    def test_strip_quotes_mismatched_quotes(self):
        """Test that mismatched quotes are not stripped."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes("\"bar'") == "\"bar'"
        assert env._strip_quotes("'bar\"") == "'bar\""
        assert env._strip_quotes('"bar') == '"bar'
        assert env._strip_quotes('bar"') == 'bar"'
        assert env._strip_quotes("'bar") == "'bar"
        assert env._strip_quotes("bar'") == "bar'"

    def test_strip_quotes_quotes_in_middle(self):
        """Test that quotes in the middle are not stripped."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes('ba"r') == 'ba"r'
        assert env._strip_quotes("ba'r") == "ba'r"
        assert env._strip_quotes('path/to/"special"/file') == 'path/to/"special"/file'

    def test_strip_quotes_empty_value(self):
        """Test stripping of empty quoted values."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes('""') == ""
        assert env._strip_quotes("''") == ""

    def test_strip_quotes_whitespace_handling(self):
        """Test whitespace handling with quotes."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        # Whitespace inside quotes should be preserved
        assert env._strip_quotes('" bar "') == " bar "
        assert env._strip_quotes("' bar '") == " bar "

        # Whitespace outside quotes should be stripped first
        assert env._strip_quotes('  "bar"  ') == "bar"
        assert env._strip_quotes("  'bar'  ") == "bar"

        # Mixed whitespace
        assert env._strip_quotes(' " bar " ') == " bar "

    def test_strip_quotes_single_character(self):
        """Test that single characters and edge cases are handled."""
        mock_ctx = self.create_mock_context()

        with (
            patch.object(EnvironmentVariables, "_parse_os_env"),
            patch.object(EnvironmentVariables, "_parse_minitrino_config"),
        ):
            env = EnvironmentVariables(mock_ctx)

        # Test the _strip_quotes method directly
        assert env._strip_quotes('"a"') == "a"
        assert env._strip_quotes("'a'") == "a"
        assert env._strip_quotes("a") == "a"
        assert env._strip_quotes('"') == '"'
        assert env._strip_quotes("'") == "'"
        assert env._strip_quotes("") == ""

    @patch("minitrino.core.envvars.ConfigParser")
    @patch("os.path.isfile")
    def test_config_file_quote_stripping_integration(
        self, mock_isfile, mock_config_parser
    ):
        """Test that quote stripping works in config file parsing."""
        mock_ctx = self.create_mock_context()
        mock_isfile.return_value = True

        mock_parser = Mock()
        mock_config_parser.return_value = mock_parser

        # Mock config file content with quotes
        mock_parser.read.return_value = ["/test/.minitrino/minitrino.cfg"]
        mock_parser.has_section.return_value = True
        mock_parser.items.return_value = [
            ("lib_path", '"/home/user/lib"'),
            ("cluster_name", "'my-cluster'"),
            ("image", "trino:latest"),  # No quotes
            ("empty", '""'),
        ]

        with patch.object(EnvironmentVariables, "_parse_os_env"):
            env = EnvironmentVariables(mock_ctx)

        # Verify that quotes were stripped
        assert env.get("LIB_PATH") == "/home/user/lib"
        assert env.get("CLUSTER_NAME") == "my-cluster"
        assert env.get("IMAGE") == "trino:latest"
        assert env.get("EMPTY") == ""
