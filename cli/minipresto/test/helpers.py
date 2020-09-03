#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import time
import sys
import subprocess
import click

from click.testing import CliRunner
from pathlib import Path
from minipresto.cli import cli

# Path references
# -----------------------------------------------------------------------------------
USER_HOME_DIR = os.path.expanduser("~")
MINIPRESTO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minipresto"))
CONFIG_FILE = os.path.abspath(os.path.join(MINIPRESTO_USER_DIR, "minipresto.cfg"))
MINIPRESTO_LIB_DIR = Path(os.path.abspath(__file__)).resolve().parents[3]
SNAPSHOT_DIR = os.path.join(MINIPRESTO_LIB_DIR, "lib", "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "test.tar.gz")
MINIPRESTO_USER_SNAPSHOTS_DIR = os.path.join(MINIPRESTO_USER_DIR, "snapshots")
SNAPSHOT_CONFIG_FILE = os.path.join(
    MINIPRESTO_USER_SNAPSHOTS_DIR, "test", "minipresto.cfg"
)
# -----------------------------------------------------------------------------------


def execute_command(command=[], print_output=True, command_input=""):
    """Executes a command through the Click CliRunner."""

    runner = CliRunner()
    if command_input == "":
        result = runner.invoke(cli, command)
    else:
        result = runner.invoke(cli, command, input=command_input)
    if print_output:
        print(
            f"Output of command [minipresto {' '.join(command)}]:\n{result.output}"
        )
    return result


def log_success(msg):
    """Logs test status message to stdout."""

    click.echo(click.style("[SUCCESS] ", fg="green", bold=True) + msg + "\n")


def log_status(msg):
    """Logs test status message to stdout."""

    click.echo(click.style("[RUNNING] ", fg="yellow", bold=True) + msg + "\n")


def start_docker_daemon():
    """Starts the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        return_code = subprocess.call("open --background -a Docker", shell=True)
    elif "linux" in sys.platform.lower():
        return_code = subprocess.call("sudo service docker start", shell=True)
    else:
        raise Exception(f"Incompatible testing platform: {sys.platform}")
    if return_code != 0:
        raise Exception("Failed to start Docker daemon.")

    docker_client = docker.from_env()
    counter = 0
    while counter < 61:
        if counter == 61:
            raise Exception("Docker daemon failed to start after one minute.")
        try:
            docker_client.ping()
            break
        except:
            counter += 1
            time.sleep(1)


def stop_docker_daemon():
    """Stops the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        return_code = subprocess.call("osascript -e 'quit app \"Docker\"'", shell=True)
    elif "linux" in sys.platform.lower():
        return_code = subprocess.call("sudo service docker stop", shell=True)
    else:
        raise Exception(f"Incompatible testing platform: {sys.platform}")
    if return_code != 0:
        raise Exception("Failed to stop Docker daemon.")

    # Hard wait for daemon to stop
    time.sleep(3)


def make_sample_config():
    """Creates a sample config file."""

    config_file = os.path.join(MINIPRESTO_USER_DIR, "minipresto.cfg")
    subprocess.call(
        f'bash -c "cat << EOF > {config_file}\n'
        f"[CLI]\n"
        f"LIB_PATH=\n"
        f"\n"
        f"[DOCKER]\n"
        f"S3_ACCESS_KEY=example\n"
        f'S3_SECRET_KEY=example\n"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
