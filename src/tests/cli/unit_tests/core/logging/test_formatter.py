"""Unit tests for logging formatter."""

import logging
from unittest.mock import patch

from minitrino.core.logging.formatter import MinitrinoLogFormatter


class TestMinitrinoLogFormatter:
    """Test suite for MinitrinoLogFormatter class."""

    def test_init_tty(self):
        """Test formatter initialization with TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            formatter = MinitrinoLogFormatter()

        assert formatter.always_verbose is False
        assert formatter.enable_color is True

    def test_init_non_tty(self):
        """Test formatter initialization without TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            formatter = MinitrinoLogFormatter()

        assert formatter.always_verbose is False
        assert formatter.enable_color is False

    def test_init_always_verbose(self):
        """Test formatter initialization with always_verbose."""
        formatter = MinitrinoLogFormatter(always_verbose=True)
        assert formatter.always_verbose is True

    def test_format_empty_message(self):
        """Test formatting empty message returns empty string."""
        formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == ""

    def test_format_whitespace_only_message(self):
        """Test formatting whitespace-only message returns empty string."""
        formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="   \n\t  ",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == ""

    @patch("sys.stdout.isatty", return_value=False)
    def test_format_simple_message_non_tty(self, mock_isatty):
        """Test formatting simple message for non-TTY."""
        formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == "[i]  Test message"

    @patch("sys.stdout.isatty", return_value=True)
    @patch("minitrino.core.logging.formatter.get_terminal_width", return_value=80)
    def test_format_simple_message_tty(self, mock_width, mock_isatty):
        """Test formatting simple message for TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "Test message" in result
        assert "[i]  " in result

    def test_get_prefix_info(self):
        """Test getting prefix for INFO level."""
        formatter = MinitrinoLogFormatter()
        formatter.enable_color = False

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        prefix = formatter._get_prefix(record)
        assert prefix == "[i]  "

    def test_get_prefix_error(self):
        """Test getting prefix for ERROR level."""
        formatter = MinitrinoLogFormatter()
        formatter.enable_color = False

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        prefix = formatter._get_prefix(record)
        assert prefix == "[e]  "

    def test_get_prefix_with_color(self):
        """Test getting colored prefix."""
        formatter = MinitrinoLogFormatter()
        formatter.enable_color = True

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        with patch("minitrino.core.logging.formatter.style") as mock_style:
            mock_style.return_value = "styled_prefix"
            prefix = formatter._get_prefix(record)

        assert prefix == "styled_prefix"
        mock_style.assert_called_once_with("[i]  ", fg="cyan", bold=True)

    def test_get_left_prefix_normal(self):
        """Test getting left prefix for normal log."""
        formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        result = formatter._get_left_prefix(record, "[i]  ")
        assert result == "[i]  "

    def test_get_left_prefix_debug_with_fq_caller(self):
        """Test getting left prefix for debug with fq_caller."""
        formatter = MinitrinoLogFormatter()
        formatter.always_verbose = True

        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.fq_caller = "module.function"

        result = formatter._get_left_prefix(record, "[v]  ")
        assert result == "[v]  module.function "

    def test_get_left_prefix_debug_with_pathname(self):
        """Test getting left prefix for debug with pathname."""
        formatter = MinitrinoLogFormatter()
        formatter.always_verbose = True

        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="/path/to/test.py",
            lineno=42,
            msg="test",
            args=(),
            exc_info=None,
        )

        result = formatter._get_left_prefix(record, "[v]  ")
        assert result == "[v]  test.py:42 "

    @patch("sys.stdout.isatty", return_value=False)
    def test_format_multiline_message_non_tty(self, mock_isatty):
        """Test formatting multiline message for non-TTY."""
        formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\nLine 2\nLine 3",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        lines = result.split("\n")

        assert len(lines) == 3
        assert lines[0] == "[i]  Line 1"
        assert lines[1] == "     Line 2"
        assert lines[2] == "     Line 3"

    @patch("sys.stdout.isatty", return_value=True)
    @patch("minitrino.core.logging.formatter.get_terminal_width", return_value=80)
    def test_format_multiline_message_tty(self, mock_width, mock_isatty):
        """Test formatting multiline message for TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\nLine 2",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "Line 1" in result
        assert "Line 2" in result

    @patch("sys.stdout.isatty", return_value=True)
    @patch("minitrino.core.logging.formatter.get_terminal_width", return_value=20)
    def test_wrap_long_lines_tty(self, mock_width, mock_isatty):
        """Test wrapping long lines for TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            formatter = MinitrinoLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="This is a very long message that should be wrapped",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        lines = result.split("\n")

        # Should be wrapped to multiple lines
        assert len(lines) > 1

    def test_colors_mapping(self):
        """Test COLORS mapping has all required levels."""
        assert "DEBUG" in MinitrinoLogFormatter.COLORS
        assert "INFO" in MinitrinoLogFormatter.COLORS
        assert "WARNING" in MinitrinoLogFormatter.COLORS
        assert "ERROR" in MinitrinoLogFormatter.COLORS
        assert "CRITICAL" in MinitrinoLogFormatter.COLORS

    def test_prefixes_mapping(self):
        """Test PREFIXES mapping has all required levels."""
        assert "DEBUG" in MinitrinoLogFormatter.PREFIXES
        assert "INFO" in MinitrinoLogFormatter.PREFIXES
        assert "WARNING" in MinitrinoLogFormatter.PREFIXES
        assert "ERROR" in MinitrinoLogFormatter.PREFIXES
        assert "CRITICAL" in MinitrinoLogFormatter.PREFIXES
