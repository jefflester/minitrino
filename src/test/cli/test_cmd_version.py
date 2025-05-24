from importlib.metadata import version

import pytest

from test.cli import utils


@pytest.mark.usefixtures("log_test")
@pytest.mark.parametrize("log_msg", ["Testing version"])
def test_version() -> None:
    """Test for correct version output."""
    result = utils.cli_cmd(utils.build_cmd(append=["--version"]))
    cli_version = version("Minitrino")
    utils.assert_exit_code(result)
    utils.assert_in_output(cli_version, result=result)
