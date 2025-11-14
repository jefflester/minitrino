"""Pytest configuration and fixtures for unit tests.

This file makes fixtures from fixtures.py available to all unit tests without needing
explicit imports.
"""

# Import all fixtures to make them available to tests
from tests.cli.unit_tests.fixtures import *  # noqa: F401, F403
