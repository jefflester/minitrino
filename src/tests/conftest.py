"""Root conftest for all Minitrino test suites.

Provides the output-silence watchdog for pytest-based tests.  Configure
via ``--watchdog-timeout`` CLI option or ``WATCHDOG_TIMEOUT`` env var
(default 600 seconds, set to 0 to disable).
"""

import os
from collections.abc import Generator

import pytest

from tests.watchdog import Watchdog


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the watchdog timeout option."""
    group = parser.getgroup("minitrino", "Minitrino shared options")
    group.addoption(
        "--watchdog-timeout",
        type=int,
        default=None,
        help="Seconds of output silence before force-exit "
        "(default: 600, env: WATCHDOG_TIMEOUT, 0 to disable).",
    )


@pytest.fixture(scope="session", autouse=True)
def _watchdog(request: pytest.FixtureRequest) -> Generator[None]:
    """Start the output-silence watchdog for the entire test session."""
    opt = request.config.getoption("--watchdog-timeout")
    timeout = opt if opt is not None else int(os.environ.get("WATCHDOG_TIMEOUT", "600"))

    if timeout <= 0:
        yield
        return

    wd = Watchdog(timeout=timeout)
    wd.start()
    yield
    wd.stop()
