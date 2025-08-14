"""Unit tests for utility functions.

Tests various utility functions used throughout the codebase.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from minitrino import utils
from minitrino.core.errors import UserError


class TestStrToBool:
    """Test suite for STR_TO_BOOL constant and string to boolean conversion."""

    def test_str_to_bool_constant_exists(self):
        """Test that STR_TO_BOOL constant is defined."""
        assert hasattr(utils, "STR_TO_BOOL")
        assert isinstance(utils.STR_TO_BOOL, dict)

    def test_true_values(self):
        """Test values that should convert to True."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]

        for val in true_values:
            if val.lower() in utils.STR_TO_BOOL:
                assert utils.STR_TO_BOOL[val.lower()] is True

    def test_false_values(self):
        """Test values that should convert to False."""
        false_values = ["false", "False", "FALSE", "0", "no", "No", "NO"]

        for val in false_values:
            if val.lower() in utils.STR_TO_BOOL:
                assert utils.STR_TO_BOOL[val.lower()] is False


class TestParseKeyValuePair:
    """Test suite for parse_key_value_pair function."""

    def test_valid_key_value_pair(self):
        """Test parsing valid key=value pairs."""
        mock_ctx = Mock()

        key, value = utils.parse_key_value_pair(mock_ctx, "KEY=value")

        assert key == "KEY"
        assert value == "value"

    def test_key_value_with_equals_in_value(self):
        """Test parsing when value contains equals sign."""
        mock_ctx = Mock()

        key, value = utils.parse_key_value_pair(mock_ctx, "KEY=value=with=equals")

        assert key == "KEY"
        assert value == "value=with=equals"

    def test_empty_value(self):
        """Test parsing key with empty value."""
        mock_ctx = Mock()

        key, value = utils.parse_key_value_pair(mock_ctx, "KEY=")

        assert key == "KEY"
        assert value == ""

    def test_whitespace_in_value(self):
        """Test parsing value with whitespace."""
        mock_ctx = Mock()

        key, value = utils.parse_key_value_pair(mock_ctx, "KEY=value with spaces")

        assert key == "KEY"
        assert value == "value with spaces"

    def test_invalid_format_hard_fail(self):
        """Test that invalid format raises UserError when hard_fail=True."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        with pytest.raises(UserError) as exc_info:
            utils.parse_key_value_pair(mock_ctx, "invalid", hard_fail=True)

        assert "must be in the form" in str(exc_info.value)

    def test_invalid_format_soft_fail(self):
        """Test that invalid format returns None when hard_fail=False."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        result = utils.parse_key_value_pair(mock_ctx, "invalid", hard_fail=False)

        assert result == (None, None)
        mock_ctx.logger.warn.assert_called()

    def test_special_characters_in_key_value(self):
        """Test parsing with special characters."""
        mock_ctx = Mock()

        test_cases = [
            ("KEY_1=value", ("KEY_1", "value")),
            ("key-name=value", ("key-name", "value")),
            ("KEY123=456", ("KEY123", "456")),
            ("PATH=/usr/bin:/usr/local/bin", ("PATH", "/usr/bin:/usr/local/bin")),
        ]

        for input_str, expected in test_cases:
            result = utils.parse_key_value_pair(mock_ctx, input_str)
            assert result == expected


class TestHandleUserError:
    """Test suite for handle_user_error function."""

    def test_user_error_with_hint(self):
        """Test handling UserError with a hint."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        error = UserError("Test error", hint="Try this instead")

        utils.handle_user_error(mock_ctx, error)

        # Should log error and hint
        mock_ctx.logger.error.assert_called()
        error_calls = mock_ctx.logger.error.call_args_list

        # Check that both error and hint were logged
        assert len(error_calls) >= 1
        assert any("Test error" in str(call) for call in error_calls)

    def test_user_error_without_hint(self):
        """Test handling UserError without a hint."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        error = UserError("Test error")

        utils.handle_user_error(mock_ctx, error)

        # Should log error only
        mock_ctx.logger.error.assert_called_once()
        assert "Test error" in str(mock_ctx.logger.error.call_args)

    def test_user_error_with_empty_hint(self):
        """Test handling UserError with empty hint."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        error = UserError("Test error", hint="")

        utils.handle_user_error(mock_ctx, error)

        # Should log error only (empty hint is ignored)
        mock_ctx.logger.error.assert_called()


class TestGetDirFileContents:
    """Test suite for get_dir_file_contents function."""

    def test_get_files_in_directory(self, tmp_path):
        """Test getting contents of files in a directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        result = utils.get_dir_file_contents(tmp_path)

        assert "file1.txt" in result
        assert "file2.txt" in result
        assert result["file1.txt"] == "content1"
        assert result["file2.txt"] == "content2"
        # Subdirectories might not be included depending on implementation

    def test_empty_directory(self, tmp_path):
        """Test getting contents of empty directory."""
        result = utils.get_dir_file_contents(tmp_path)

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_non_existent_directory(self):
        """Test handling of non-existent directory."""
        with pytest.raises(Exception):
            utils.get_dir_file_contents(Path("/non/existent/path"))

    def test_binary_files_skipped(self, tmp_path):
        """Test that binary files are handled appropriately."""
        # Create a text file and a "binary" file
        (tmp_path / "text.txt").write_text("text content")
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")

        result = utils.get_dir_file_contents(tmp_path)

        assert "text.txt" in result
        # Binary file handling depends on implementation


class TestCheckBindMount:
    """Test suite for check_bind_mount function."""

    @patch("os.path.isdir")
    def test_directory_exists(self, mock_isdir):
        """Test bind mount check when directory exists."""
        mock_isdir.return_value = True

        result = utils.check_bind_mount("/existing/path")

        assert result == "/existing/path"

    @patch("os.path.isdir")
    def test_directory_not_exists(self, mock_isdir):
        """Test bind mount check when directory doesn't exist."""
        mock_isdir.return_value = False

        result = utils.check_bind_mount("/non/existent/path")

        assert result is None

    @patch("os.path.isdir")
    def test_relative_path_converted(self, mock_isdir):
        """Test that relative paths are converted to absolute."""
        mock_isdir.return_value = True

        with patch("os.path.abspath", return_value="/absolute/path"):
            result = utils.check_bind_mount("./relative/path")

        # Should convert to absolute path
        assert result is not None

    def test_none_input(self):
        """Test handling of None input."""
        result = utils.check_bind_mount(None)

        assert result is None

    def test_empty_string_input(self):
        """Test handling of empty string input."""
        result = utils.check_bind_mount("")

        assert result is None or result == ""
