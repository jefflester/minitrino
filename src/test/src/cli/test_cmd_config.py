#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# 1. Test with no Minitrino directory
# 2. Test with no Minitrino config file (ensure template is created)
# 3. Test reset w/ existing config dir and file (ensure template is created)
# 4. Test editing an invalid config file

import os
import subprocess

import src.common as common
import src.cli.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast

# Using the Click CliRunner does not appear to play well with commands that
# require user input. That is being researched.


def main():
    common.log_status(__file__)
    # test_no_directory()
    test_reset_with_directory()
    # test_edit_invalid_config()
    # test_edit_valid_config()


def test_no_directory():
    """Verifies that a configuration directory and config file are created with
    config --reset."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"rm -rf {common.MINITRINO_USER_DIR}", shell=True)
    return_code = subprocess.call("minitrino config", shell=True)

    assert return_code == 0
    assert os.path.isdir(common.MINITRINO_USER_DIR)
    assert os.path.isfile(common.CONFIG_FILE)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_reset_with_directory():
    """Verifies that the configuration directory is only removed and restored
    with the user's approval. This is a valid test case for both 'yes' and 'no'
    responses."""

    import time

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(
        f"mkdir {common.MINITRINO_USER_DIR}", shell=True, stdout=subprocess.DEVNULL
    )

    start_time = time.time()
    end_time = 2.0
    output = ""
    while time.time() - start_time <= end_time:
        process = subprocess.Popen(
            "minitrino -v config --reset",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        while True:
            output_line = process.stdout.readline()
            if output_line == "":
                break
        output, _ = process.communicate()  # Get full output (stdout + stderr)
        if time.time() >= end_time:
            process.terminate()
            break

    process = subprocess.Popen(
        "minitrino -v config --reset",
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        universal_newlines=True,
    )
    output = process.communicate(input="y\n", timeout=1)[0]
    process.terminate()

    assert process.returncode == 0
    assert all(
        (
            "Configuration directory exists" in output,
            "Created Minitrino configuration directory" in output,
            "Opening existing config file at path" in output,
        )
    )
    assert os.path.isdir(common.MINITRINO_USER_DIR)
    assert os.path.isfile(common.CONFIG_FILE)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_invalid_config():
    """Verifies that an error is not thrown if the config is 'invalid' (such as
    a missing section or value required to perform an action). This is because
    there is default behavior built in, and all major functions should still
    work without a valid configuration file."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"rm -rf {common.MINITRINO_USER_DIR}", shell=True)
    subprocess.call(f"mkdir {common.MINITRINO_USER_DIR}", shell=True)
    subprocess.call(f"touch {common.CONFIG_FILE}", shell=True)
    return_code = subprocess.call(f"minitrino config", shell=True)
    assert return_code == 0
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_valid_config():
    """Verifies that the user can edit an existing configuration file."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    subprocess.call(f"rm -rf {common.MINITRINO_USER_DIR}", shell=True)
    subprocess.call(f"mkdir {common.MINITRINO_USER_DIR}", shell=True)
    helpers.make_sample_config()
    return_code = subprocess.call(f"minitrino config", shell=True)
    assert return_code == 0
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
