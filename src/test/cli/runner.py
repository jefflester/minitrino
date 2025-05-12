#!/usr/bin/env python3

from test.cli import (
    test_misc,
    test_cmd_config,
    test_cmd_down,
    test_cmd_provision,
    test_cmd_restart,
    test_cmd_remove,
    test_cmd_snapshot,
    test_cmd_version,
    test_cmd_modules,
    test_cmd_lib_install,
)


def main():
    """Minitrino CLI test runner."""

    test_misc.main()
    test_cmd_config.main()
    test_cmd_down.main()
    test_cmd_provision.main()
    test_cmd_restart.main()
    test_cmd_remove.main()
    test_cmd_snapshot.main()
    test_cmd_version.main()
    test_cmd_modules.main()
    test_cmd_lib_install.main()


if __name__ == "__main__":
    main()
