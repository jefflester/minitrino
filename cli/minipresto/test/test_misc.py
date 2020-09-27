#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import pathlib
import subprocess
import pkg_resources
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_version()


def test_version():
    """
    Tests for correct version output.
    """

    result = helpers.execute_command(["version"])
    assert pkg_resources.require("Minipresto")[0].version in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_presto_config():
    """
    Validates user-defined config is propagated to Presto at a global level.
    """


def test_docker_host():
    """
    Validates you can connect to another Docker host.
    """


def test_scrub_keys():
    """
    Tests scrub key effectiveness.
    """


def test_symlink_paths():
    """
    Ensures Minipresto can find paths from symlinks.
    """


if __name__ == "__main__":
    main()
