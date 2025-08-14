"""Unit tests for logging sink."""

import logging
from unittest.mock import MagicMock, patch

from minitrino.core.logging.sink import SinkCollector, SinkOnlyHandler


class TestSinkCollector:
    """Test suite for SinkCollector class."""

    def test_init(self):
        """Test SinkCollector initialization."""
        sink = SinkCollector()
        assert sink.buffer == []
        assert sink._buffer_size_bytes == 0
        assert sink.MAX_BUFFER_BYTES == 100 * 1024 * 1024

    def test_call_adds_to_buffer(self):
        """Test calling sink adds message to buffer."""
        sink = SinkCollector()

        sink("test message", "stdout", False)

        assert len(sink.buffer) == 1
        assert sink.buffer[0] == ("test message", "stdout", False)
        assert sink._buffer_size_bytes > 0

    def test_call_with_spinner(self):
        """Test calling sink with spinner flag."""
        sink = SinkCollector()

        sink("spinner message", "stderr", True)

        assert len(sink.buffer) == 1
        assert sink.buffer[0] == ("spinner message", "stderr", True)

    def test_buffer_size_tracking(self):
        """Test buffer size is tracked correctly."""
        sink = SinkCollector()

        msg1 = "test message 1"
        msg2 = "test message 2"

        sink(msg1, "stdout", False)
        size1 = sink._buffer_size_bytes

        sink(msg2, "stderr", False)
        size2 = sink._buffer_size_bytes

        assert size2 > size1
        assert sink.size == size2

    def test_trim_buffer_when_exceeds_max(self):
        """Test buffer is trimmed when it exceeds max size."""
        sink = SinkCollector()
        sink.MAX_BUFFER_BYTES = 100  # Set small limit for testing

        # Add messages until we exceed the limit
        for i in range(10):
            sink(f"message {i}" * 10, "stdout", False)

        # Should have trimmed buffer
        assert len(sink.buffer) < 10
        assert sink._buffer_size_bytes <= sink.MAX_BUFFER_BYTES

    def test_trim_buffer_keeps_recent_messages(self):
        """Test trimming keeps the most recent messages."""
        sink = SinkCollector()
        sink.MAX_BUFFER_BYTES = 200  # Small limit

        # Add numbered messages
        messages = []
        for i in range(20):
            msg = f"message_{i}"
            messages.append(msg)
            sink(msg, "stdout", False)

        # Check that earlier messages were removed
        buffer_messages = [msg for msg, _, _ in sink.buffer]
        assert messages[0] not in buffer_messages
        assert messages[-1] in buffer_messages

    def test_clear(self):
        """Test clearing the buffer."""
        sink = SinkCollector()

        sink("message 1", "stdout", False)
        sink("message 2", "stderr", True)

        assert len(sink.buffer) == 2
        assert sink._buffer_size_bytes > 0

        sink.clear()

        assert len(sink.buffer) == 0
        assert sink._buffer_size_bytes == 0

    def test_size_property(self):
        """Test size property returns buffer size."""
        sink = SinkCollector()

        assert sink.size == 0

        sink("test", "stdout", False)

        assert sink.size > 0
        assert sink.size == sink._buffer_size_bytes

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        sink = SinkCollector()

        unicode_msg = "Test with emoji 🎉 and special chars €£¥"
        sink(unicode_msg, "stdout", False)

        assert len(sink.buffer) == 1
        assert sink.buffer[0][0] == unicode_msg


class TestSinkOnlyHandler:
    """Test suite for SinkOnlyHandler class."""

    def test_init(self):
        """Test SinkOnlyHandler initialization."""
        sink = MagicMock()
        formatter = MagicMock()

        handler = SinkOnlyHandler(sink, formatter)

        assert handler.sink == sink
        assert handler.formatter == formatter
        assert handler.level == logging.NOTSET

    @patch("minitrino.core.logging.sink.strip_ansi")
    def test_emit_stdout(self, mock_strip_ansi):
        """Test emitting log record to stdout."""
        sink = MagicMock()
        formatter = MagicMock()
        formatter.format.return_value = "formatted message"
        mock_strip_ansi.return_value = "stripped message"

        handler = SinkOnlyHandler(sink, formatter)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        formatter.format.assert_called_once_with(record)
        mock_strip_ansi.assert_called_once_with("formatted message")
        sink.assert_called_once_with("stripped message", "stdout", False)

    @patch("minitrino.core.logging.sink.strip_ansi")
    def test_emit_stderr(self, mock_strip_ansi):
        """Test emitting error log record to stderr."""
        sink = MagicMock()
        formatter = MagicMock()
        formatter.format.return_value = "error message"
        mock_strip_ansi.return_value = "stripped error"

        handler = SinkOnlyHandler(sink, formatter)

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        sink.assert_called_once_with("stripped error", "stderr", False)

    @patch("minitrino.core.logging.sink.strip_ansi")
    def test_emit_handles_exception(self, mock_strip_ansi):
        """Test emit handles exceptions gracefully."""
        sink = MagicMock()
        formatter = MagicMock()
        formatter.format.side_effect = Exception("Format error")

        handler = SinkOnlyHandler(sink, formatter)
        handler.handleError = MagicMock()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        handler.handleError.assert_called_once_with(record)
        sink.assert_not_called()

    @patch("minitrino.core.logging.sink.strip_ansi")
    def test_emit_critical_level(self, mock_strip_ansi):
        """Test emitting critical log record to stderr."""
        sink = MagicMock()
        formatter = MagicMock()
        formatter.format.return_value = "critical"
        mock_strip_ansi.return_value = "critical"

        handler = SinkOnlyHandler(sink, formatter)

        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="critical",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # CRITICAL is >= ERROR, should go to stderr
        sink.assert_called_once_with("critical", "stderr", False)
