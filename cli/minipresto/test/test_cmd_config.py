#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# 1. Test with no Minipresto directory
# 2. Test with no Minipresto config file (ensure template is created)
# 3. Test reset w/ existing config dir and file (ensure template is created)
# 4. Test editing an invalid config file

import os
import subprocess
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast

# Using the Click CliRunner does not appear to play well with commands that
# require user input. That is being researched.


def main():
    helpers.log_status(__file__)
    test_reset_no_directory()
    test_reset_with_directory()
    test_edit_invalid_config()
    test_edit_valid_config()


def test_reset_no_directory():
    """Verifies that a configuration directory and config file are created with
    config --reset."""

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    return_code = subprocess.call("minipresto config --reset", shell=True)

    assert return_code == 0
    assert os.path.isdir(helpers.minipresto_user_dir)
    assert os.path.isfile(helpers.config_file)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_reset_with_directory():
    """Verifies that the configuration directory is only removed and restored
    with the user's approval. This is a valid test case for both 'yes' and 'no'
    responses."""

    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    return_code = subprocess.call(f"minipresto config --reset", shell=True)

    assert return_code == 0
    assert os.path.isdir(helpers.minipresto_user_dir)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_invalid_config():
    """Verifies that an error is not thrown if the config is 'invalid' (such as
    a missing section or value required to perform an action). This is because
    there is default behavior built in, and all major functions should still
    work without a valid configuration file."""

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"touch {helpers.config_file}", shell=True)
    return_code = subprocess.call(f"minipresto config", shell=True)
    assert return_code == 0
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_edit_valid_config():
    """Verifies that the user can edit an existing configuration file."""

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    helpers.make_sample_config()
    return_code = subprocess.call(f"minipresto config", shell=True)
    assert return_code == 0
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
