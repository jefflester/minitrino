#!/usr/bin/env python3

import os
import re
import json

import src.common as common
from minitrino.cli import cli
from src.common import CONFIG_FILE

from click.testing import CliRunner


class MinitrinoResult:
    def __init__(self, click_result, output, exit_code):
        """Result class containing information about the result of a Minitrino
        command.

        Attributes
        ----------
        - `click_result`: The unaltered Click Result object.
        - `output`: Formatted output with newlines removed.
        - `exit_code`: The exit code of the command."""

        self.click_result = click_result
        self.output = output
        self.exit_code = exit_code


def execute_cli_cmd(command=[], print_output=True, command_input="", env={}):
    """Executes a command through the Click CliRunner."""

    runner = CliRunner()
    if not command_input:
        result = runner.invoke(cli, command, env=env)
    else:
        result = runner.invoke(cli, command, input=command_input, env=env)
    if print_output:
        print(f"Output of command [minitrino {' '.join(command)}]:\n{result.output}")

    # Remove newlines and extra spaces for string assertion consistency
    output = result.output.replace("\n", "")
    output = re.sub(" +", " ", output)
    return MinitrinoResult(result, output, result.exit_code)


def make_sample_config():
    """Creates a sample config file."""

    cmd = (
        f'bash -c "cat << EOF > {CONFIG_FILE}\n'
        f"[config]\n"
        f"LIB_PATH=\n"
        f"CLUSTER_VER=\n"
        f"TEXT_EDITOR=\n"
        f"LIC_PATH=\n"
        f'SECRET_KEY=abc123\n"'
    )

    common.execute_command(cmd)


def update_metadata_json(module="", updates=[]):
    """Updates a given module's metadata.json file with the provided
    list of dicts."""

    path = get_metadata_json_path(module)

    with open(path, "r") as f:
        data = json.load(f)

    for update in updates:
        for k, v in update.items():
            data[k] = v

    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def reset_test_metadata_json():
    """Resets the test module's metadata.json file to default values."""

    default = {
        "description": "Test module.",
        "incompatibleModules": ["ldap"],
        "dependentModules": ["file-access-control"],
        "versions": [],
        "enterprise": False,
    }
    path = get_metadata_json_path("test")

    with open(path, "w") as f:
        json.dump(default, f, indent=2)
        f.write("\n")


def get_metadata_json_path(module=""):
    """Fetches the metadata.json file path for a given module."""

    metadata = get_module_metadata(module)
    return os.path.abspath(
        os.path.join(metadata[module]["module_dir"], "metadata.json")
    )


def get_module_metadata(module=""):
    """Fetches (all) module metadata for a given module."""

    metadata = execute_cli_cmd(["modules", "-m", module, "--json"])
    return json.loads(metadata.output)


def get_module_yaml_path(module=""):
    """Fetches the module.yaml file path for a given module."""

    metadata = get_module_metadata(module)
    return os.path.abspath(metadata[module]["yaml_file"])
