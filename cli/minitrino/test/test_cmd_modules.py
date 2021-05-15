#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import subprocess
import minitrino.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    helpers.log_status(__file__)
    test_invalid_module()
    test_valid_module()
    test_all_modules()
    test_json()
    test_running()


def test_invalid_module():
    """Ensures Minitrino exists with a user error if an invalid module name is
    provided."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "modules", "--module", "not-a-real-module"])

    assert result.exit_code == 2
    assert "Invalid module" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_module():
    """Ensures the `module` command works when providing a valid module name."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "modules", "--module", "test"])

    assert result.exit_code == 0
    assert all(("Module: test" in result.output, "Test module" in result.output))

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_all_modules():
    """Ensures that all module metadata is printed to the console if a module
    name is not passed to the command."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "modules"])

    assert result.exit_code == 0
    assert all(
        (
            "Module: test" in result.output,
            "Description:" in result.output,
            "Incompatiblemodules:" in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_json():
    """Ensures the `module` command can output module metadata in JSON
    format."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "modules", "--module", "test", "--json"])

    assert result.exit_code == 0
    assert all(('"type": "catalog"' in result.output, '"test":' in result.output))

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_running():
    """Ensures the `module` command can output metadata for running modules."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision", "--module", "test"])
    result = helpers.execute_command(["-v", "modules", "--json", "--running"])

    assert result.exit_code == 0
    assert all(
        (
            '"type": "catalog"' in result.output,
            '"type": "catalog"' in result.output,
            '"containers":' in result.output,
        )
    )

    helpers.execute_command(["-v", "down", "--sig-kill"])
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
