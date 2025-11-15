"""Minitrino logger."""

import inspect
import logging
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from types import FrameType, TracebackType

from click import prompt, style

from minitrino.core import logging as lg
from minitrino.core.errors import MinitrinoError


class MinitrinoLogger(logging.Logger):
    """Minitrino logger."""

    _instance = None

    def __new__(cls, name, level=logging.NOTSET):
        """Create a new logger or return the existing instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self._log_level = lg.levels.LogLevel.INFO
        self._user_log_level = lg.levels.LogLevel.INFO
        self._log_sink: lg.sink.SinkCollector = lg.sink.SinkCollector()
        self._formatter: lg.formatter.MinitrinoLogFormatter | None = None
        self._spinner: lg.spinner.Spinner | None = None

    def log(
        self,
        level: int,
        msg: object,
        *args: object,
        exc_info: (
            bool
            | BaseException
            | tuple[type[BaseException], BaseException, TracebackType | None]
            | tuple[None, None, None]
            | None
        ) = None,
        stack_info: bool = False,
        stacklevel: int = 3,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        """Log a message."""
        self._log_with_stacklevel(
            super().log,
            level,
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    def info(self, msg: object, *args: object, **kwargs) -> None:
        """Log an info message."""
        lvl = logging.INFO
        self._log_with_stacklevel(super().info, msg, *args, level=lvl, **kwargs)

    def warn(self, msg: object, *args: object, **kwargs) -> None:
        """Log a warning message."""
        lvl = logging.WARN
        self._log_with_stacklevel(super().warning, msg, *args, level=lvl, **kwargs)

    def warning(self, msg: object, *args: object, **kwargs) -> None:
        """Log a warning message."""
        self.warn(msg, *args, **kwargs)

    def error(self, msg: object, *args: object, **kwargs) -> None:
        """Log an error message."""
        lvl = logging.ERROR
        self._log_with_stacklevel(super().error, msg, *args, level=lvl, **kwargs)

    def debug(self, msg: object, *args: object, **kwargs) -> None:
        """Log a debug message."""
        lvl = logging.DEBUG
        self._log_with_stacklevel(super().debug, msg, *args, level=lvl, **kwargs)

    def set_log_sink(self, sink: Callable[[str, str, bool], None] | None) -> None:
        """Set the log sink."""
        self._log_sink = sink or lg.sink.SinkCollector()

    def enable_log_buffer(self) -> None:
        """Enable internal buffering of all logs."""
        self._log_sink = lg.sink.SinkCollector()
        self.set_log_sink(self._log_sink)

        # Update the SinkOnlyHandler on the root logger to use the new sink
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, lg.sink.SinkOnlyHandler):
                handler.sink = self._log_sink

    @property
    def log_buffer(self) -> list[tuple[str, str]]:
        """Return the log buffer."""
        return [
            (msg, stream)
            for msg, stream, is_spinner in self._log_sink.buffer
            if not is_spinner
        ]

    def clear_log_buffer(self) -> None:
        """Clear the log buffer."""
        self._log_sink.buffer.clear()

    def set_level(self, level: lg.levels.LogLevel) -> None:
        """Set the log level for the logger and all handlers."""
        self._log_level = level
        py_level = lg.levels.PY_LEVEL[level]
        self.setLevel(py_level)
        # Update handlers on this logger
        for handler in self.handlers:
            handler.setLevel(py_level)
        # Also update MinitrinoLoggerHandler on root logger if propagating
        if self.propagate:
            root = logging.getLogger()
            for handler in root.handlers:
                if handler.__class__.__name__ == "MinitrinoLoggerHandler":
                    handler.setLevel(py_level)

        always_verbose = level == lg.levels.LogLevel.DEBUG
        if self._formatter:
            self._formatter.always_verbose = always_verbose
        if self._spinner:
            self._spinner.always_verbose = always_verbose

    def prompt_msg(self, msg: str = "") -> str:
        """Prompt for a message."""
        styled_prefix = style(
            lg.levels.LogLevel.INFO.prefix, fg=lg.levels.LogLevel.INFO.color, bold=True
        )
        return prompt(f"{styled_prefix}{msg}", type=str)

    def styled_prefix(self, level: lg.levels.LogLevel = lg.levels.LogLevel.INFO) -> str:
        """Return a styled prefix."""
        return style(level.prefix, fg=level.color, bold=True)

    def _log_with_stacklevel(self, super_method, *args: object, **kwargs) -> None:
        """Log a message with stack level."""
        level = kwargs.pop("level", self.level)
        if not args:
            return super_method(*args, **kwargs)

        msg, *log_args = args
        msg_str = str(msg).strip()
        if not msg_str:
            return

        kwargs.setdefault("stacklevel", 3)

        # Only attach fq_caller for debug/info logs at debug level
        if self.isEnabledFor(logging.DEBUG) and level in (logging.DEBUG, logging.INFO):
            fq_name = lg.utils.get_caller_fq_name(stacklevel=kwargs["stacklevel"])
            kwargs.setdefault("extra", {})
            kwargs["extra"]["fq_caller"] = fq_name

        # Do NOT pass 'level' to super_method
        super_method(msg_str, *log_args, **kwargs)

        # The sink handler attached to the root logger will capture all
        # logs. Do NOT call the sink directly here; this prevents double
        # emission and log leaks.

    @contextmanager
    def spinner(self, message: str):
        """Display a spinner while a task is in progress."""
        if not isinstance(self._spinner, lg.spinner.Spinner):
            raise MinitrinoError(
                f"Spinner is not of type Spinner, got: {type(self._spinner)}."
            )
        with self._spinner.spinner(message):
            yield

    def _get_caller_logger(self) -> logging.Logger:
        """Get the caller logger."""
        frame: FrameType | None = inspect.currentframe()
        for _ in range(3):
            frame = frame.f_back if frame and frame.f_back else frame
        module = inspect.getmodule(frame)
        return logging.getLogger(module.__name__ if module else "minitrino")
