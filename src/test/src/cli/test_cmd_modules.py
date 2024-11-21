#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import src.common as common
import src.cli.utils as utils

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    test_invalid_module()
    test_valid_module()
    test_all_modules()
    test_json()
    test_running()


def test_invalid_module():
    """Ensures Minitrino exists with a user error if an invalid module name is
    provided."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "not-a-real-module"])

    assert result.exit_code == 2
    assert "Invalid module" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_module():
    """Ensures the `module` command works when providing a valid module name."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "test"])

    assert result.exit_code == 0
    assert all(("Module: test" in result.output, "Test module" in result.output))

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_all_modules():
    """Ensures that all module metadata is printed to the console if a module
    name is not passed to the command."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules"])

    assert result.exit_code == 0
    assert all(
        (
            "Module: test" in result.output,
            "Description:" in result.output,
            "IncompatibleModules:" in result.output,
            "DependentModules:" in result.output,
            "Versions:" in result.output,
            "Enterprise:" in result.output,
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_json():
    """Ensures the `module` command can output module metadata in JSON
    format."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "test", "--json"])

    assert result.exit_code == 0
    assert all(('"type": "catalog"' in result.output, '"test":' in result.output))

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_running():
    """Ensures the `module` command can output metadata for running modules."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    result = utils.execute_cli_cmd(["-v", "modules", "--json", "--running"])

    assert result.exit_code == 0
    assert all(
        (
            '"type": "catalog"' in result.output,
            '"type": "security"' in result.output,
            "file-access-control" in result.output,
        )
    )

    utils.execute_cli_cmd(["-v", "down", "--sig-kill"])
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
