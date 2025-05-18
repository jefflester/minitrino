import pkg_resources
from logging import Logger
from test.cli import utils


@pytest.mark.usefixtures("log_test")
@pytest.mark.parametrize("log_msg", ["Testing version"], id="version")
def test_version(logger: Logger) -> None:
    """Test for correct version output."""
    result = utils.cli_cmd(utils.build_cmd("version"), logger)
    version = pkg_resources.require("Minitrino")[0].version
    utils.assert_exit_code(result)
    utils.assert_in_output(version, result=result)
