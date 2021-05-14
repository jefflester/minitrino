#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import pkg_resources

from minitrino import errors as err
from minitrino.settings import DEFAULT_INDENT

from click import echo, style, prompt
from textwrap import fill
from shutil import get_terminal_size
from functools import wraps


class Logger:
    """Minitrino logging class. The logger does not log to a file; it uses
    `click.echo()` to print text to the user's terminal.

    The log level will affect the prefix color (i.e. the '[i]' in info messages
    is blue) and the message prefix (the prefix for the warning logs is '[w]').

    ### Parameters
    - `log_verbose`: If `True`, log messages flagged as verbose will be logged.
      If `False`, verbose messages will not be logged. This is dynamically
      determined by user input when the logger is instantiated from the
      Environment class.

    ### Public Attributes
    - `info`: Info log level.
    - `warn`: Warn log level.
    - `error`: Error log level.
    - `verbose`: Verbose log level.

    ### Public Methods
    - `log()`: Logs a message to the user's terminal.
    - `prompt_msg()`: Logs a prompt message and returns the user's input."""

    def __init__(self, log_verbose=False):

        self.info = {"prefix": "[i]  ", "prefix_color": "cyan"}
        self.warn = {"prefix": "[w]  ", "prefix_color": "yellow"}
        self.error = {"prefix": "[e]  ", "prefix_color": "red"}
        self.verbose = {"prefix": "[i]  ", "prefix_color": "cyan", "verbose": True}

        self._log_verbose = log_verbose

    def log(self, *args, level=None, stream=False):
        """Logs messages to the user's console. Defaults to 'info' log level.

        ### Parameters
        - `*args`: Messages to log.
        - `level`: The level of the log message (info, warn, error, and
          verbose).
        - `stream`: If `True`, the logger will not apply a prefix to each line
          streamed to the console."""

        if not level:
            level = self.info

        # Skip verbose messages unless verbose mode is enabled
        if not self._log_verbose and level == self.verbose:
            return

        for msg in args:
            # Ensure the message can be a string
            try:
                msg = str(msg)
            except:
                raise err.MinitrinoError(
                    f"A string is required for {self.log.__name__}."
                )
            msgs = msg.replace("\r", "\n").split("\n")
            # Log each message
            for i, msg in enumerate(msgs):
                msg = self._format(msg)
                if not msg:
                    continue
                if stream or i > 0:
                    msg_prefix = DEFAULT_INDENT
                else:
                    msg_prefix = style(
                        level.get("prefix", ""),
                        fg=level.get("prefix_color", ""),
                        bold=True,
                    )
                echo(f"{msg_prefix}{msg}")

    def prompt_msg(self, msg="", input_type=str):
        """Logs a prompt message and returns the user's input.

        ### Parameters
        - `msg`: The prompt message
        - `input_type`: The object type to check the input for"""

        if not msg:
            raise handle_missing_param(["msg"])

        try:
            msg = str(msg)
        except:
            raise err.MinitrinoError(f"A string is required for {self.log.__name__}.")

        msg = self._format(msg)
        styled_prefix = style(
            self.info.get("prefix", ""), fg=self.info.get("prefix_color", ""), bold=True
        )

        return prompt(
            f"{styled_prefix}{msg}",
            type=input_type,
        )

    def _format(self, msg):
        """Formats strings prior to displaying to the user."""

        msg = msg.rstrip()
        if not msg:
            return ""

        terminal_width, _ = get_terminal_size()
        msg = msg.replace("\n", f"\n{DEFAULT_INDENT}")
        msg = fill(
            msg,
            terminal_width - 4,
            subsequent_indent=DEFAULT_INDENT,
            replace_whitespace=False,
            break_on_hyphens=False,
            break_long_words=True,
        )

        return msg


def handle_exception(error=Exception, additional_msg="", skip_traceback=False):
    """Handles a single exception. Wrapped by `@exception_handler` decorator.

    ### Parameters
    - `error`: The exception object.
    - `additional_msg`: An additional message to log, if any. Can be useful if
      handling a generic exception and you need to append a user-friendly
      message to the log.
    - `skip_traceback`: If `True`, the traceback will not be printed to the
      user's terminal. Defaults to `True` for user errors, but it is `False`
      otherwise."""

    if not isinstance(error, Exception):
        raise handle_missing_param(["error"])

    if isinstance(error, err.UserError):
        error_msg = error.msg
        exit_code = error.exit_code
        skip_traceback = True
    elif isinstance(error, err.MinitrinoError):
        error_msg = error.msg
        exit_code = error.exit_code
    elif isinstance(error, Exception):
        error_msg = str(error)
        exit_code = 1
    else:
        raise err.MinitrinoError(
            f"Invalid type given to 'e' parameter of {handle_exception.__name__}. "
            f"Expected an Exception type, but got type {type(error).__name__}"
        )

    logger = Logger()
    logger.log(additional_msg, error_msg, level=logger.error)
    if not skip_traceback:
        echo()  # Force a newline
        echo(f"{traceback.format_exc()}", err=True)

    sys.exit(exit_code)


def exception_handler(func):
    """A decorator that handles unhandled exceptions. Why? A few reasons.

    1. Inner functions still have the liberty to do try/catch and perform
       inner-function exception handling how they wish.
    2. Functions that catch exceptions which need specialized handling can
       manually invoke the handle_exception() utility.
    3. For all other generic exceptions and unhandled exceptions, they will be
       siphoned to the handle_exception() utility.

    This is especially useful when decorating main/runner functions and class
    constructors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_exception(e)

    return wrapper


def handle_missing_param(params=[]):
    """Handles missing parameters required for function calls. This should be
    used to signal a programmatic error, not a user error.

    ### Parameters
    - `params`: List of parameter names that are required.

    ### Usage
    ```python
    # All params are required
    if not param:
        raise handle_missing_param(list(locals().keys()))
    # Two params are required
    if not param:
        raise handle_missing_param(["module", "path"])
    ```"""

    if not params:
        raise handle_missing_param(list(locals().keys()))

    return err.MinitrinoError(f"Parameters {params} required to execute function.")


def check_daemon(docker_client):
    """Checks if the Docker daemon is running. If an exception is thrown, it is
    handled."""

    try:
        docker_client.ping()
    except Exception as e:
        raise err.UserError(
            f"Error when pinging the Docker server. Is the Docker daemon running?\n"
            f"Error from Docker: {str(e)}",
            "You may need to initialize your Docker daemon.",
        )


def check_lib(ctx):
    """Checks if a Minitrino library exists."""

    ctx.minitrino_lib_dir


def generate_identifier(identifiers=None):
    """Returns an 'object identifier' string used for creating log messages,
    e.g. '[ID: 12345] [Name: trino]'.

    ### Parameters
    - `identifiers`: Dictionary of "identifier_value": "identifier_key" pairs.

    ### Usage
    ```python
    identifier = generate_identifier(
        {"ID": container.short_id, "Name": container.name}
    ) # Will Spit out -> "[ID: 12345] [Name: trino]"
    ```"""

    if not identifiers:
        raise handle_missing_param(list(locals().keys()))

    identifier = []
    for key, value in identifiers.items():
        identifier.append(f"[{key}: {value}]")
    return " ".join(identifier)


def parse_key_value_pair(key_value_pair, err_type=err.MinitrinoError):
    """Parses a key-value pair in string form and returns the resulting pair as
    both a 2-element list. If the string cannot be split by "=", a
    MinitrinoError is raised.

    ### Parameters
    - `key_value_pair`: A string formatted as a key-value pair, i.e.
      `"TRINO=354-e"`.
    - `err_type`: The exception to raise if an "=" delimiter is not in the
      key-value pair. Defaults to `MinitrinoError`.

    ### Return Values
    - A list `[k, v]`, but will return `None` if the stripped input is an empty
      string."""

    # Return None of empty string or special char (i.e. '\n')
    key_value_pair = key_value_pair.strip()
    if not key_value_pair:
        return None

    key_value_pair = key_value_pair.split("=", 1)
    err_msg = (
        f"Invalid key-value pair: '{'='.join(key_value_pair)}'. "
        f"Key-value pairs should be formatted as 'KEY=VALUE'"
    )

    # Raise an error if the key has no value
    if not key_value_pair[0]:
        raise err_type(err_msg)

    if isinstance(key_value_pair, list):
        for i in range(len(key_value_pair)):
            key_value_pair[i] = key_value_pair[i].strip()
        if not key_value_pair[0]:
            raise err_type(err_msg)
    if not len(key_value_pair) == 2:
        raise err_type(err_msg)

    return key_value_pair


def get_cli_ver():
    """Returns the version of the Minitrino CLI."""

    return pkg_resources.require("Minitrino")[0].version


def get_lib_ver(library_path=""):
    """Returns the version of the Minitrino library.

    ### Parameters
    - `library_path`: The Minitrino library directory."""

    version_file = os.path.join(library_path, "version")
    try:
        with open(version_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    return line
            return "NOT INSTALLED"
    except:
        return "NOT INSTALLED"


def validate_yes(response=""):
    """Validates 'yes' user input. Returns `True` if a 'yes' input is
    detected."""

    response = response.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
