#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import re
import subprocess

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


def execute_command(command=[], print_output=True, command_input="", env={}):
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

    subprocess.call(
        f'bash -c "cat << EOF > {CONFIG_FILE}\n'
        f"[config]\n"
        f"LIB_PATH=\n"
        f"STARBURST_VER=\n"
        f'TEXT_EDITOR=\n"'
        f'LIC_PATH=\n"',
        f'SECRET_KEY=abc123\n"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
