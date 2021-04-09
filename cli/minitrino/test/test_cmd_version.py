#!usr/bin/env/python3
# -*- coding: utf-8 -*-


import minitrino.test.helpers as helpers
import pkg_resources

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    helpers.log_status(__file__)
    test_version()


def test_version():
    """Tests for correct version output."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["version"])
    assert pkg_resources.require("Minitrino")[0].version in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
