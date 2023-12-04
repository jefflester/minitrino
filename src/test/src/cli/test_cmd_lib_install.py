#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import subprocess

import src.common as common
import src.cli.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    test_install()
    test_install_overwrite()
    test_invalid_ver()


def test_install():
    """Verifies that the Minitrino library can be installed."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()

    # Install 0.0.0 since it's always around as a test release
    result = helpers.execute_command(["-v", "lib-install", "--version", "0.0.0"])

    assert result.exit_code == 0
    assert os.path.isdir(os.path.join(common.MINITRINO_USER_DIR, "lib"))

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_install_overwrite():
    """Verifies that the Minitrino library can be installed over an existing
    library."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "lib-install", "--version", "0.0.0"], command_input="y\n"
    )

    assert result.exit_code == 0
    assert os.path.isdir(os.path.join(common.MINITRINO_USER_DIR, "lib"))
    assert "Removing existing library directory" in result.output

    cleanup()

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_ver():
    """Verifies that an error is raised if an incorrect version is passed to the
    command."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "lib-install", "--version", "YEE-TRINO"])

    assert result.exit_code == 1
    assert not os.path.isdir(os.path.join(common.MINITRINO_USER_DIR, "lib"))

    cleanup()

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def cleanup():
    subprocess.call("rm -rf ~/.minitrino/", shell=True)


if __name__ == "__main__":
    main()
