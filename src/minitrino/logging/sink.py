"""Logging sink for Minitrino logger."""

import logging

from minitrino.ansi import strip_ansi


class SinkCollector:
    """Collect log messages and metadata from the log sink."""

    MAX_BUFFER_BYTES = 100 * 1024 * 1024  # 100 MB

    def __init__(self) -> None:
        self.buffer: list[tuple[str, str, bool]] = []
        self._buffer_size_bytes = 0

    def __call__(self, msg: str, stream: str, is_spinner: bool):
        """Collect a log message and add it to the buffer."""
        msg_size = len(msg.encode("utf-8")) + len(stream.encode("utf-8")) + 1
        self._buffer_size_bytes += msg_size
        self.buffer.append((msg, stream, is_spinner))

        if self._buffer_size_bytes > self.MAX_BUFFER_BYTES:
            self._trim_buffer()

    def _trim_buffer(self):
        """Trim the buffer by discarding the oldest 50% of entries."""
        half = len(self.buffer) // 2
        self.buffer = self.buffer[half:]

        self._buffer_size_bytes = sum(
            len(msg.encode("utf-8")) + len(stream.encode("utf-8")) + 1
            for msg, stream, _ in self.buffer
        )

    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
        self._buffer_size_bytes = 0

    @property
    def size(self) -> int:
        """Return the size of the buffer in bytes."""
        return self._buffer_size_bytes


class SinkOnlyHandler(logging.Handler):
    """Handler that sends all logs to the sink, regardless of level."""

    def __init__(self, sink: SinkCollector, formatter: logging.Formatter) -> None:
        super().__init__(level=logging.NOTSET)
        self.sink = sink
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        try:
            msg = self.format(record)
            msg = strip_ansi(msg)
            stream = "stderr" if record.levelno >= logging.ERROR else "stdout"
            self.sink(msg, stream, False)
        except Exception:
            self.handleError(record)
