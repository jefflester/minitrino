#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import subprocess

import src.common as common
import src.cli.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast

CMD = ["-v", "-e", "TEXT_EDITOR=cat", "config"]


def main():
    common.log_status(__file__)
    test_no_directory()
    test_no_config_file()
    test_reset()
    test_edit_invalid_config()
    test_edit_valid_config()


def test_no_directory():
    """Verifies that a configuration directory and config file are created when
    executing config command (if not already present)."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"rm -rf {common.MINITRINO_USER_DIR}", shell=True)
    result = helpers.execute_command(CMD)

    assert result.exit_code == 0
    assert os.path.isdir(common.MINITRINO_USER_DIR)
    assert os.path.isfile(common.CONFIG_FILE)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_no_config_file():
    """Verifies that a missing config file is created when executing config
    command."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"rm {common.CONFIG_FILE}", shell=True)
    result = helpers.execute_command(CMD)

    assert result.exit_code == 0
    assert os.path.isfile(common.CONFIG_FILE)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_reset():
    """Ensures that the --reset option works as expected, even if the config
    file is invalid."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"echo 'hello world' > {common.CONFIG_FILE}", shell=True)

    # Run the command and feed 'y' as input
    result = helpers.execute_command(CMD + ["--reset"], command_input="y\n")

    assert result.exit_code == 0
    assert os.path.isfile(common.CONFIG_FILE)

    config_contents = subprocess.Popen(
        f"cat {common.CONFIG_FILE}",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    config_contents, _ = config_contents.communicate()
    assert "hello world" not in config_contents

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_invalid_config():
    """Verifies that an error is not thrown if the config is 'invalid' (such as
    a missing section). This is because there is default behavior built in, and
    all major functions should still work without a valid configuration file."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"echo 'hello world' > {common.CONFIG_FILE}", shell=True)
    result = helpers.execute_command(CMD)

    assert result.exit_code == 0
    assert "Failed to parse config file" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_valid_config():
    """Verifies that the user can edit an existing configuration file."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.make_sample_config()
    result = helpers.execute_command(CMD)
    assert result.exit_code == 0

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
