#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import time
import sys
import subprocess
import click

from pathlib import Path

# Path references
user_home_dir = os.path.expanduser("~")
minipresto_user_dir = os.path.abspath(os.path.join(user_home_dir, ".minipresto"))
config_file = os.path.abspath(os.path.join(minipresto_user_dir, "minipresto.cfg"))
minipresto_lib_dir = Path(os.path.abspath(__file__)).resolve().parents[3]
snapshot_dir = os.path.join(minipresto_lib_dir, "lib", "snapshots")
snapshot_file = os.path.join(snapshot_dir, "test.tar.gz")
minipresto_user_snapshots_dir = os.path.join(minipresto_user_dir, "snapshots")
snapshot_config_file = os.path.join(
    minipresto_user_snapshots_dir, "test", "minipresto.cfg"
)


def log_status(msg):
    """Logs test status message to the console."""

    click.echo(click.style(">> ", fg="green", bold=True) + msg)


def start_docker_daemon():
    """Starts the Docker daemon (works on MacOS)."""

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
    """Stops the Docker daemon (works on MacOS)."""

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

    config_file = os.path.join(minipresto_user_dir, "minipresto.cfg")
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