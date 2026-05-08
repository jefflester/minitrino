"""Pytest configuration and fixtures for Minitrino library (module) tests."""

import logging
import os
from collections.abc import Generator
from typing import Any

import pytest

from tests import common
from tests.lib import utils
from tests.lib.module_test import ModuleTest

HERE = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.join(HERE, "json")


# ---------------------------------------------------------------------------
# Custom CLI options
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register lib-test-specific CLI options."""
    group = parser.getgroup("minitrino-lib", "Minitrino library test options")
    group.addoption(
        "--image",
        choices=["trino", "starburst"],
        default="trino",
        help="Image to use for cluster containers (default: trino).",
    )
    group.addoption(
        "--remove-images",
        action="store_true",
        default=False,
        help="Remove images after each module test.",
    )
    group.addoption(
        "--modules",
        type=str,
        default="",
        help="Space-separated module names to test (default: all).",
    )


# ---------------------------------------------------------------------------
# Parametrize: one test case per module JSON file
# ---------------------------------------------------------------------------


def _discover_modules() -> list[str]:
    """Return sorted module names from the JSON test directory."""
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(JSON_DIR) if f.endswith(".json")
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize any test requesting ``module_name``."""
    if "module_name" not in metafunc.fixturenames:
        return

    all_modules = _discover_modules()
    modules_opt = metafunc.config.getoption("--modules", "").split()
    if modules_opt:
        selected = [m for m in modules_opt if m in all_modules]
    else:
        selected = all_modules

    metafunc.parametrize("module_name", selected)


# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def image(request: pytest.FixtureRequest) -> str:
    """Return the ``--image`` option value."""
    return request.config.getoption("--image")


@pytest.fixture(scope="session")
def remove_images(request: pytest.FixtureRequest) -> bool:
    """Return the ``--remove-images`` option value."""
    return request.config.getoption("--remove-images")


@pytest.fixture(scope="session", autouse=True)
def _setup_environment(request: pytest.FixtureRequest) -> None:
    """Start Docker and run an initial cleanup before any tests."""
    debug = request.config.getoption("verbose", 0) > 0
    log_level = logging.DEBUG if debug else logging.INFO
    common.logger = common.get_logger(log_level)

    common.start_docker_daemon()
    ModuleTest.cleanup(debug=debug)


# ---------------------------------------------------------------------------
# Per-test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _module_cleanup(
    request: pytest.FixtureRequest, remove_images: bool
) -> Generator[None]:
    """Clean up containers, networks, and volumes after each module test."""
    yield
    debug = request.config.getoption("verbose", 0) > 0
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        utils.dump_container_logs(debug=debug, force=True)
    ModuleTest.cleanup(remove_images, debug)


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo,  # type: ignore[type-arg]
) -> Generator[None]:
    """Stash call report on the test item so fixtures can inspect it."""
    outcome: Any = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
