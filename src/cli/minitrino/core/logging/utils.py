"""Logging utilities for Minitrino."""

import inspect
import logging
import os
import shutil

from minitrino.core import logging as lg

DEFAULT_INDENT = " " * 5


def configure_logging(
    log_level: lg.levels.LogLevel = lg.levels.LogLevel.INFO,
) -> lg.logger.MinitrinoLogger:
    """
    Create a singleton Minitrino logger or return the existing one.

    Parameters
    ----------
    log_level : LogLevel
        Minimum log level to emit.

    Returns
    -------
    MinitrinoLogger
        The configured minitrino logger.
    """
    logging.setLoggerClass(lg.logger.MinitrinoLogger)
    logger: lg.logger.MinitrinoLogger = logging.getLogger("minitrino")
    root_logger = logging.getLogger()

    def _logger_is_configured(logger: logging.Logger) -> bool:
        # Check if logger is MinitrinoLogger and root has MinitrinoLoggerHandler
        if not isinstance(logger, lg.logger.MinitrinoLogger):
            return False
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if handler.__class__.__name__ == "MinitrinoLoggerHandler":
                return True
        return False

    def _setup_handlers_and_formatters(
        logger: lg.logger.MinitrinoLogger,
        root_logger: logging.Logger,
        log_level: lg.levels.LogLevel,
    ):
        logger.handlers.clear()
        root_logger.handlers.clear()
        always_verbose = log_level == lg.levels.LogLevel.DEBUG

        # Spinner, formatter, and minitrino handler
        logger._spinner = lg.spinner.Spinner(
            logger, logger.set_log_sink, always_verbose=always_verbose
        )
        from minitrino.core.logging.handler import MinitrinoLoggerHandler

        minitrino_handler = MinitrinoLoggerHandler(logger._spinner)
        logger._formatter = lg.formatter.MinitrinoLogFormatter(
            always_verbose=always_verbose
        )
        minitrino_handler.setFormatter(logger._formatter)
        minitrino_handler.setLevel(lg.levels.PY_LEVEL[log_level])

        # Sink handler for capturing all logs
        sink_handler = lg.sink.SinkOnlyHandler(logger._log_sink, logger._formatter)
        sink_handler.setLevel(logging.NOTSET)
        root_logger.addHandler(sink_handler)
        root_logger.addHandler(minitrino_handler)
        root_logger.setLevel(logging.NOTSET)
        logger.propagate = True

    if _logger_is_configured(logger):
        # Found existing logger, returning to caller.
        # Update logger level to requested level when returning existing logger.
        logger.set_level(log_level)
        return logger

    logger.debug("No logger found, creating new singleton.")
    _setup_handlers_and_formatters(logger, root_logger, log_level)

    # Turn off urllib3 logging
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


def get_terminal_width() -> int:
    """Get the terminal width."""
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def get_caller_fq_name(stacklevel: int = 4) -> str:
    """Get the fully qualified name of the caller."""
    frame = inspect.currentframe()
    for _ in range(stacklevel):
        if frame is not None:
            frame = frame.f_back
    if frame is None:
        return "<unknown>"
    module = inspect.getmodule(frame)
    module_name = module.__name__ if module else "<unknown>"
    filename = os.path.basename(frame.f_code.co_filename)
    lineno = frame.f_lineno
    return f"{module_name}:{filename}:{lineno}"
