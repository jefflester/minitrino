#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import src.cli.test_misc

# import src.cli.test_cmd_config
import src.cli.test_cmd_down
import src.cli.test_cmd_provision
import src.cli.test_cmd_remove
import src.cli.test_cmd_snapshot
import src.cli.test_cmd_version
import src.cli.test_cmd_modules
import src.cli.test_cmd_lib_install


def main():
    """Minitrino CLI test runner."""

    src.cli.test_misc.main()
    # src.cli.test_cmd_config.main()
    src.cli.test_cmd_down.main()
    src.cli.test_cmd_provision.main()
    src.cli.test_cmd_remove.main()
    src.cli.test_cmd_snapshot.main()
    src.cli.test_cmd_version.main()
    src.cli.test_cmd_modules.main()
    src.cli.test_cmd_lib_install.main()


if __name__ == "__main__":
    main()
