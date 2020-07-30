#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import subprocess
import minipresto.test.helpers as helpers

# Using the Click CliRunner does not appear to play well with commands that
# require user input. That is being researched.


def main():
    helpers.log_status("Running test_config")
    test_reset_no_directory()
    test_reset_with_directory()
    test_edit_invalid_config()
    test_edit_valid_config()


def test_reset_no_directory():
    """
    Verifies that a configuration directory and config file are created with
    config --reset.
    """

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    return_code = subprocess.call("minipresto config --reset", shell=True)

    assert return_code == 0
    assert os.path.isdir(helpers.minipresto_user_dir)
    assert os.path.isfile(helpers.config_file)

    helpers.log_status(f"Passed test_reset_no_directory")


def test_reset_with_directory():
    """
    Verifies that the configuration directory is only removed and restored with
    the user's approval. This is a valid test case for both 'yes' and 'no'
    responses.
    """

    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    return_code = subprocess.call(f"minipresto config --reset", shell=True)

    assert return_code == 0
    assert os.path.isdir(helpers.minipresto_user_dir)

    helpers.log_status(f"Passed test_reset_with_directory")


def test_edit_invalid_config():
    """
    Verifies that an error is not thrown if the config is 'invalid' (such as a
    missing section or value required to perform an action). This is because
    there is default behavior built in, and all major functions should still
    work without a valid configuration file. 
    """

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"touch {helpers.config_file}", shell=True)
    return_code = subprocess.call(f"minipresto config", shell=True)
    assert return_code == 0
    helpers.log_status(f"Passed test_edit_invalid_config")


def test_edit_valid_config():
    """
    Verifies that the user can edit an existing configuration file.
    """

    subprocess.call(f"rm -rf {helpers.minipresto_user_dir}", shell=True)
    subprocess.call(f"mkdir {helpers.minipresto_user_dir}", shell=True)
    helpers.make_sample_config()
    return_code = subprocess.call(f"minipresto config", shell=True)
    assert return_code == 0
    helpers.log_status(f"Passed test_edit_valid_config")


if __name__ == "__main__":
    main()
