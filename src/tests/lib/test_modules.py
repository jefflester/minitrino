"""Pytest-driven module tests for Minitrino.

Each module JSON file in ``json/`` becomes a parametrized test case.
The heavy lifting is delegated to :class:`ModuleTest`.
"""

import json
import os

import pytest

from tests.lib.module_test import ModuleTest

HERE = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.join(HERE, "json")


def test_module(
    module_name: str,
    image: str,
    request: pytest.FixtureRequest,
) -> None:
    """Provision, test, and restart a single module."""
    debug = request.config.getoption("verbose", 0) > 0
    exit_first = request.config.getoption("exitfirst", False)

    json_path = os.path.join(JSON_DIR, f"{module_name}.json")
    with open(json_path) as f:
        json_data = json.load(f)

    test = ModuleTest(json_data, module_name, image, debug=debug, x=exit_first)
    if not test.run():
        pytest.skip(f"Module '{module_name}' skipped")
