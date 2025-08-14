"""Unit tests for Minitrino logger."""

import logging
from unittest.mock import MagicMock, patch

from minitrino.core.logging import levels, sink
from minitrino.core.logging.logger import MinitrinoLogger


class TestMinitrinoLogger:
    """Test suite for MinitrinoLogger class."""

    def test_singleton_pattern(self):
        """Test logger follows singleton pattern."""
        logger1 = MinitrinoLogger("test1")
        logger2 = MinitrinoLogger("test2")

        assert logger1 is logger2

    def test_init(self):
        """Test logger initialization."""
        # Reset singleton
        MinitrinoLogger._instance = None

        logger = MinitrinoLogger("test")

        assert logger.name == "test"
        assert logger._log_level == levels.LogLevel.INFO
        assert logger._user_log_level == levels.LogLevel.INFO
        assert isinstance(logger._log_sink, sink.SinkCollector)
        assert logger._formatter is None
        assert logger._spinner is None

    def test_info(self):
        """Test info level logging."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "_log_with_stacklevel") as mock_log:
            logger.info("test message")

        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == "test message"

    def test_warn(self):
        """Test warn level logging."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "_log_with_stacklevel") as mock_log:
            logger.warn("warning message")

        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == "warning message"

    def test_warning_calls_warn(self):
        """Test warning method calls warn."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "warn") as mock_warn:
            logger.warning("warning message")

        mock_warn.assert_called_once_with("warning message")

    def test_error(self):
        """Test error level logging."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "_log_with_stacklevel") as mock_log:
            logger.error("error message")

        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == "error message"

    def test_debug(self):
        """Test debug level logging."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "_log_with_stacklevel") as mock_log:
            logger.debug("debug message")

        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == "debug message"

    def test_set_log_sink(self):
        """Test setting log sink."""
        logger = MinitrinoLogger("test")
        new_sink = MagicMock()

        logger.set_log_sink(new_sink)

        assert logger._log_sink == new_sink

    def test_set_log_sink_none(self):
        """Test setting log sink to None creates new SinkCollector."""
        logger = MinitrinoLogger("test")

        logger.set_log_sink(None)

        assert isinstance(logger._log_sink, sink.SinkCollector)

    def test_enable_log_buffer(self):
        """Test enabling log buffer."""
        logger = MinitrinoLogger("test")

        logger.enable_log_buffer()

        assert isinstance(logger._log_sink, sink.SinkCollector)

    def test_log_buffer_property(self):
        """Test log buffer property."""
        logger = MinitrinoLogger("test")
        logger._log_sink = sink.SinkCollector()

        # Add some messages
        logger._log_sink.buffer = [
            ("msg1", "stdout", False),
            ("spinner", "stdout", True),
            ("msg2", "stderr", False),
        ]

        buffer = logger.log_buffer

        # Should exclude spinner messages
        assert len(buffer) == 2
        assert buffer[0] == ("msg1", "stdout")
        assert buffer[1] == ("msg2", "stderr")

    def test_clear_log_buffer(self):
        """Test clearing log buffer."""
        logger = MinitrinoLogger("test")
        logger._log_sink = sink.SinkCollector()
        logger._log_sink.buffer = [("msg", "stdout", False)]

        logger.clear_log_buffer()

        assert logger._log_sink.buffer == []

    def test_set_level(self):
        """Test setting log level."""
        logger = MinitrinoLogger("test")
        handler1 = MagicMock()
        handler2 = MagicMock()
        logger.handlers = [handler1, handler2]
        logger._formatter = MagicMock()
        logger._spinner = MagicMock()

        logger.set_level(levels.LogLevel.DEBUG)

        assert logger._log_level == levels.LogLevel.DEBUG
        assert logger.level == logging.DEBUG
        handler1.setLevel.assert_called_once_with(logging.DEBUG)
        handler2.setLevel.assert_called_once_with(logging.DEBUG)
        assert logger._formatter.always_verbose is True
        assert logger._spinner.always_verbose is True

    def test_set_level_info(self):
        """Test setting log level to INFO."""
        logger = MinitrinoLogger("test")
        logger._formatter = MagicMock()
        logger._spinner = MagicMock()

        logger.set_level(levels.LogLevel.INFO)

        assert logger._log_level == levels.LogLevel.INFO
        assert logger.level == logging.INFO
        assert logger._formatter.always_verbose is False
        assert logger._spinner.always_verbose is False

    @patch("minitrino.core.logging.logger.prompt")
    @patch("minitrino.core.logging.logger.style")
    def test_prompt_msg(self, mock_style, mock_prompt):
        """Test prompting for message."""
        logger = MinitrinoLogger("test")
        mock_style.return_value = "styled_prefix"
        mock_prompt.return_value = "user input"

        result = logger.prompt_msg("Enter value: ")

        assert result == "user input"
        mock_style.assert_called_once_with("[i]  ", fg="cyan", bold=True)
        mock_prompt.assert_called_once_with("styled_prefixEnter value: ", type=str)

    @patch("minitrino.core.logging.logger.style")
    def test_styled_prefix(self, mock_style):
        """Test getting styled prefix."""
        logger = MinitrinoLogger("test")
        mock_style.return_value = "styled"

        result = logger.styled_prefix(levels.LogLevel.ERROR)

        assert result == "styled"
        mock_style.assert_called_once_with("[e]  ", fg="red", bold=True)

    def test_log_with_stacklevel_empty_message(self):
        """Test logging with empty message."""
        logger = MinitrinoLogger("test")
        super_method = MagicMock()

        logger._log_with_stacklevel(super_method)

        super_method.assert_called_once_with()

    def test_log_with_stacklevel_whitespace_message(self):
        """Test logging with whitespace-only message."""
        logger = MinitrinoLogger("test")
        super_method = MagicMock()

        logger._log_with_stacklevel(super_method, "   ")

        super_method.assert_not_called()

    @patch("minitrino.core.logging.utils.get_caller_fq_name")
    def test_log_with_stacklevel_debug_mode(self, mock_get_caller):
        """Test logging with stack level in debug mode."""
        logger = MinitrinoLogger("test")
        logger.setLevel(logging.DEBUG)
        super_method = MagicMock()
        mock_get_caller.return_value = "module.function"

        logger._log_with_stacklevel(super_method, "test message", level=logging.DEBUG)

        mock_get_caller.assert_called_once_with(stacklevel=3)
        super_method.assert_called_once()
        kwargs = super_method.call_args[1]
        assert kwargs["extra"]["fq_caller"] == "module.function"

    def test_log_with_stacklevel_normal(self):
        """Test logging with stack level in normal mode."""
        logger = MinitrinoLogger("test")
        logger.setLevel(logging.INFO)
        super_method = MagicMock()

        logger._log_with_stacklevel(super_method, "test message")

        super_method.assert_called_once()
        args, kwargs = super_method.call_args
        assert args[0] == "test message"
        assert kwargs["stacklevel"] == 3

    def test_log_method(self):
        """Test log method."""
        logger = MinitrinoLogger("test")

        with patch.object(logger, "_log_with_stacklevel") as mock_log:
            logger.log(logging.INFO, "test message", extra={"key": "value"})

        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == logging.INFO
        assert args[2] == "test message"

    def test_singleton_reset(self):
        """Test resetting singleton for testing."""
        MinitrinoLogger._instance = None
        logger1 = MinitrinoLogger("test1")

        MinitrinoLogger._instance = None
        logger2 = MinitrinoLogger("test2")

        assert logger1 is not logger2
