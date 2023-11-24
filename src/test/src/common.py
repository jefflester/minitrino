#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import sys
import subprocess
import click

from time import sleep, gmtime, strftime
from pathlib import Path

# Path references
# -----------------------------------------------------------------------------------
USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = Path(os.path.abspath(__file__)).resolve().parents[3]
SNAPSHOT_DIR = os.path.join(MINITRINO_LIB_DIR, "src", "lib", "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "test.tar.gz")
MINITRINO_USER_SNAPSHOTS_DIR = os.path.join(MINITRINO_USER_DIR, "snapshots")
# -----------------------------------------------------------------------------------


def log_success(msg):
    """Logs test status message to stdout."""

    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [SUCCESS] ",
            fg="green",
            bold=True,
        )
        + msg
        + "\n"
    )


def log_status(msg):
    """Logs test status message to stdout."""

    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [RUNNING] ",
            fg="yellow",
            bold=True,
        )
        + msg
        + "\n"
    )


def start_docker_daemon():
    """Starts the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        return_code = subprocess.call("open --background -a Docker", shell=True)
    elif "linux" in sys.platform.lower():
        return_code = subprocess.call("sudo service docker start", shell=True)
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")
    if return_code != 0:
        raise RuntimeError("Failed to start Docker daemon.")

    counter = 0
    while counter < 61:
        if counter == 61:
            raise TimeoutError("Docker daemon failed to start after one minute.")
        try:
            docker_client = docker.from_env()
            docker_client.ping()
            break
        except:
            counter += 1
            sleep(1)


def stop_docker_daemon():
    """Stops the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        return_code = subprocess.call("osascript -e 'quit app \"Docker\"'", shell=True)
    elif "linux" in sys.platform.lower():
        return_code = subprocess.call(
            "sudo service docker stop; sudo systemctl stop docker.socket", shell=True
        )
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")
    if return_code != 0:
        raise RuntimeError("Failed to stop Docker daemon.")

    # Hard wait for daemon to stop
    sleep(3)
