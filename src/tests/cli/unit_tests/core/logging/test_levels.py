"""Unit tests for logging levels."""

import logging

from minitrino.core.logging.levels import PY_LEVEL, LogLevel


class TestLogLevel:
    """Test suite for LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.INFO.prefix == "[i]  "
        assert LogLevel.INFO.color == "cyan"
        assert LogLevel.INFO.debug is False

        assert LogLevel.WARN.prefix == "[w]  "
        assert LogLevel.WARN.color == "yellow"
        assert LogLevel.WARN.debug is False

        assert LogLevel.ERROR.prefix == "[e]  "
        assert LogLevel.ERROR.color == "red"
        assert LogLevel.ERROR.debug is False

        assert LogLevel.DEBUG.prefix == "[v]  "
        assert LogLevel.DEBUG.color == "magenta"
        assert LogLevel.DEBUG.debug is True

    def test_log_level_attributes(self):
        """Test LogLevel attributes are properly set."""
        for level in LogLevel:
            assert hasattr(level, "prefix")
            assert hasattr(level, "color")
            assert hasattr(level, "debug")
            assert isinstance(level.prefix, str)
            assert isinstance(level.color, str)
            assert isinstance(level.debug, bool)

    def test_py_level_mapping(self):
        """Test Python log level mapping."""
        assert PY_LEVEL[LogLevel.DEBUG] == logging.DEBUG
        assert PY_LEVEL[LogLevel.INFO] == logging.INFO
        assert PY_LEVEL[LogLevel.WARN] == logging.WARNING
        assert PY_LEVEL[LogLevel.ERROR] == logging.ERROR

    def test_py_level_keys(self):
        """Test all LogLevel enums are in PY_LEVEL mapping."""
        for level in LogLevel:
            assert level in PY_LEVEL

    def test_log_level_enum_uniqueness(self):
        """Test LogLevel enum values are unique."""
        values = [level.value for level in LogLevel]
        assert len(values) == len(set(values))

    def test_log_level_iteration(self):
        """Test LogLevel enum can be iterated."""
        levels = list(LogLevel)
        assert len(levels) == 4
        assert LogLevel.INFO in levels
        assert LogLevel.WARN in levels
        assert LogLevel.ERROR in levels
        assert LogLevel.DEBUG in levels
