#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import src.common as common
import src.cli.utils as utils
from minitrino.settings import MODULE_ADMIN
from minitrino.settings import MODULE_CATALOG
from minitrino.settings import MODULE_SECURITY

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    test_invalid_module()
    test_valid_module()
    test_all_modules()
    test_json()
    test_type()
    test_running()


def test_invalid_module():
    """Ensures Minitrino exists with a user error if an invalid module name is
    provided."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "not-a-real-module"])
    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert "No modules match the specified criteria" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_module():
    """Ensures the `module` command works when providing a valid module name."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "test"])

    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert all(("Module: test" in result.output, "Test module" in result.output))

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_all_modules():
    """Ensures that all module metadata is printed to the console if a module
    name is not passed to the command."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules"])

    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    # Check if "Module:" appears more than 5 times (arbitrary threshold)
    module_count = result.output.count("Module:")
    assert (
        module_count > 5
    ), f"Expected more modules in the output, found {module_count}."

    # Ensure key fields are present at least once
    expected_fields = [
        "Description:",
        "IncompatibleModules:",
        "DependentModules:",
        "Versions:",
        "Enterprise:",
    ]
    for field in expected_fields:
        assert field in result.output, f"Expected field '{field}' not found in output."

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_json():
    """Ensures the `module` command can output module metadata in JSON
    format."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--module", "test", "--json"])

    assert result.exit_code == 0
    assert all(
        (f'"type": "{MODULE_CATALOG}"' in result.output, '"test":' in result.output)
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_type():
    """Ensures type filter works as expected."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "modules", "--type", MODULE_ADMIN, "--json"])
    assert result.exit_code == 0
    assert f"/src/lib/modules/{MODULE_ADMIN}" in result.output
    assert all(
        (
            f"/src/lib/modules/{MODULE_CATALOG}" not in result.output,
            f"/src/lib/modules/{MODULE_SECURITY}" not in result.output,
        )
    )

    result = utils.execute_cli_cmd(
        ["-v", "modules", "--type", MODULE_CATALOG, "--json"]
    )
    assert result.exit_code == 0
    assert f"/src/lib/modules/{MODULE_CATALOG}" in result.output
    assert all(
        (
            f"/src/lib/modules/{MODULE_ADMIN}" not in result.output,
            f"/src/lib/modules/{MODULE_SECURITY}" not in result.output,
        )
    )

    result = utils.execute_cli_cmd(
        ["-v", "modules", "--type", MODULE_SECURITY, "--json"]
    )
    assert result.exit_code == 0
    assert f"/src/lib/modules/{MODULE_SECURITY}" in result.output
    assert all(
        (
            f"/src/lib/modules/{MODULE_ADMIN}" not in result.output,
            f"/src/lib/modules/{MODULE_CATALOG}" not in result.output,
        )
    )

    result = utils.execute_cli_cmd(
        ["-v", "modules", "--module", "postgres", "--type", MODULE_SECURITY]
    )
    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert "No modules match the specified criteria" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_running():
    """Ensures the `module` command can output metadata for running modules."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    result = utils.execute_cli_cmd(["-v", "modules", "--json", "--running"])

    assert result.exit_code == 0
    assert all(
        (
            f'"type": "{MODULE_CATALOG}"' in result.output,
            f'"type": "{MODULE_SECURITY}"' in result.output,
            "file-access-control" in result.output,
        )
    )

    utils.execute_cli_cmd(["-v", "down", "--sig-kill"])
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
