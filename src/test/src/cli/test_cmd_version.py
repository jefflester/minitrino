#!/usr/bin/env python3


import pkg_resources

import src.common as common
import src.cli.utils as utils

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    test_version()


def test_version():
    """Tests for correct version output."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["version"])
    assert pkg_resources.require("Minitrino")[0].version in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
