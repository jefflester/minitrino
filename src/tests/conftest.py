"""Root conftest for all Minitrino test suites.

Registers the watchdog plugin so its pytest hooks (collection, fixture
setup/teardown, test reports) ping the silence timer. Configure via
``--watchdog-timeout`` or ``WATCHDOG_TIMEOUT`` (default 900s, 0 to disable).
"""

pytest_plugins = ["tests.watchdog"]
