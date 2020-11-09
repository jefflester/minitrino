#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import minipresto.test.test_misc as test_misc
import minipresto.test.test_cmd_config as test_config
import minipresto.test.test_cmd_down as test_down
import minipresto.test.test_cmd_provision as test_provision
import minipresto.test.test_cmd_remove as test_remove
import minipresto.test.test_cmd_snapshot as test_snapshot
import minipresto.test.test_cmd_version as test_version
import minipresto.test.test_cmd_modules as test_modules
import minipresto.test.test_cmd_lib_install as test_cmd_lib_install


def main():
    """Minipresto unit test runner."""

    test_misc.main()
    # test_config.main()
    test_down.main()
    test_provision.main()
    test_remove.main()
    test_snapshot.main()
    test_version.main()
    test_modules.main()
    test_cmd_lib_install.main()


if __name__ == "__main__":
    main()
