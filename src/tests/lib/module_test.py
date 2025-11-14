"""Test class for Minitrino modules."""

import os
import re
import sys
from time import monotonic, sleep

import click
import jsonschema

from minitrino.settings import DEFAULT_CLUSTER_VER

here = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.abspath(os.path.join(here, "../.."))
repo_root = os.path.abspath(os.path.join(src_dir, ".."))

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


from tests import common  # noqa: E402
from tests.lib import utils  # noqa: E402

CONTAINER_NAME = "minitrino-lib-test"
COLOR_OUTPUT = sys.stdout.isatty()

logger = common.logger


class ModuleTest:
    """
    Test class for Minitrino modules.

    Parameters
    ----------
    json_data : dict
        JSON containing module test data.
    module : str
        Module name.
    image : str
        Image to use for cluster containers.
    debug : bool
        Whether to enable debug logging.
    x : bool
        Whether to exit on failure; do not rollback resources of failed
        module.
    specs : dict
        JSON schema specifications for different test types.

    Methods
    -------
    run()
        Run all tests for the module.
    log_success()
        Log a success message.
    log_failure()
        Log a failure message.
    cleanup()
        Remove containers, networks, and volumes.
    """

    def __init__(self, json_data: dict, module: str, image: str, debug: bool, x: bool):
        self.json_data = json_data
        self.module = module
        self.image = image
        self.debug = debug
        self.x = x
        self.specs = utils.SPECS
        self.module_overrides = json_data.get("moduleOverrides", {})

    def run(self) -> bool:
        """
        Run all tests for the module.

        Returns
        -------
        bool
            `True` if tests were run, `False` if they were skipped.
        """
        utils.log_status(f"Running tests for module: '{self.module}'")
        if self._skip_enterprise():
            utils.log_status(
                f"Module '{self.module}' is an enterprise module, skipping test"
            )
            return False

        if self._skip_ci():
            utils.log_status(
                f"Module '{self.module}' is configured to skip in CI, skipping test"
            )
            return False

        tests = self.json_data.get("tests", [])
        for t in tests:
            self._validate(t)

        self._runner(tests)
        self.cleanup(debug=self.debug)

        # Skip worker test if configured (useful for memory-intensive modules)
        if not self.json_data.get("skipWorkers", False):
            self._runner(tests, workers=True)
        else:
            utils.log_status(f"Module '{self.module}' configured to skip worker test")
        return True

    @staticmethod
    def cleanup(remove_images=False, debug=False) -> None:
        """
        Remove containers, networks, and volumes.

        Parameters
        ----------
        remove_images : bool
            Whether to remove images.
        debug : bool
            Whether to enable debug logging.
        """
        executor = common.MinitrinoExecutor("all", debug)
        cmd_down = executor.build_cmd("down", append=["--sig-kill"])
        executor.exec(cmd_down)
        cmd_remove = executor.build_cmd("remove", append=["--volumes"])
        executor.exec(cmd_remove)
        if remove_images:
            logger.debug("Removing images...")
            common.execute_cmd(
                'docker images -q | grep -v "$(docker images minitrino/cluster -q)" | '
                "xargs -r docker rmi",
            )
        logger.debug("Disk space usage:")
        common.execute_cmd("df -h")

    @staticmethod
    def log_success(msg: str, timestamp: str | None = None) -> None:
        """
        Log a success message.

        Parameters
        ----------
        msg : str
            The message to log.
        timestamp : str, optional
            Timestamp string to use as prefix (format: '%d/%m/%Y
            %H:%M:%S'). If not provided, current time is used.
        """
        prefix = timestamp if timestamp is not None else utils._timestamp()
        click.echo(
            click.style(
                f"[{prefix} GMT] [SUCCESS] ",
                fg="green",
                bold=True,
            )
            + msg,
            color=COLOR_OUTPUT,
        )

    @staticmethod
    def log_failure(
        msg: str, error: BaseException | None = None, timestamp: str | None = None
    ) -> None:
        """
        Log a failure message.

        Parameters
        ----------
        msg : str
            The message to log.
        error : BaseException | None
            The exception that occurred. It is appended to the failure
            message.
        timestamp : str, optional
            Timestamp string to use as prefix (format: '%d/%m/%Y
            %H:%M:%S'). If not provided, current time is used.
        """
        prefix = timestamp if timestamp is not None else utils._timestamp()
        click.echo(
            click.style(
                f"[{prefix} GMT] [FAILURE] ",
                fg="red",
                bold=True,
            )
            + f"{msg}{': ' + str(error) if error else ''}",
            err=True,
            color=COLOR_OUTPUT,
        )

    def _skip_enterprise(self) -> bool:
        """
        Skip enterprise tests under certain conditions.

        Returns
        -------
        bool
            `True` if the tests should be skipped, `False` otherwise.

        Notes
        -----
        Skips tests if the module is enterprise and the image is
        'trino'.
        """
        cmd_result = common.execute_cmd(
            f"minitrino modules -m {self.module} --json | "
            f'python3 -c "import sys, json; '
            f"data = json.load(sys.stdin); "
            f"print(data.get('{self.module}', {{}}).get('enterprise', False))\"",
        )
        if self.image == "trino" and cmd_result.output.strip() == "True":
            utils.log_status(
                f"Module '{self.module}' is an enterprise module, skipping test"
            )
            return True
        return False

    def _skip_ci(self) -> bool:
        """
        Skip tests in CI if configured via test JSON.

        Returns
        -------
        bool
            `True` if the tests should be skipped, `False` otherwise.

        Notes
        -----
        Checks for 'skipCi' field in test JSON. If true and IS_GITHUB
        environment variable is set to 'true', the test will be skipped.
        This allows marking resource-intensive tests that exceed CI runner
        constraints.
        """
        is_github = os.environ.get("IS_GITHUB", "").lower() == "true"
        skip_ci = self.json_data.get("skipCi", False)
        return is_github and skip_ci

    def _runner(self, tests: list[dict], workers: bool = False) -> None:
        """
        Run all tests for the module.

        Parameters
        ----------
        tests : list[dict]
            List of tests to run.
        workers : bool
            Whether to run tests with workers.
        """
        if self.image == "starburst":
            cluster_ver = ["-e", f"CLUSTER_VER={DEFAULT_CLUSTER_VER}-e"]
        else:
            cluster_ver = ["-e", f"CLUSTER_VER={DEFAULT_CLUSTER_VER}"]

        prepend_args = cluster_ver

        # Apply module overrides if specified in test JSON
        if self.module_overrides.get("dependentClusters"):
            import json

            override_json = json.dumps(self.module_overrides["dependentClusters"])
            prepend_args += ["-e", f"MINITRINO_TEST_DEP_OVERRIDE={override_json}"]
            logger.debug(f"Using dependent cluster override: {override_json}")

        # Apply main cluster environment variable overrides
        if self.module_overrides.get("env"):
            for key, value in self.module_overrides["env"].items():
                prepend_args += ["-e", f"{key}={value}"]
                logger.debug(f"Using main cluster env override: {key}={value}")

        no_rollback = "--no-rollback" if self.x else ""
        append_args = [
            "--image",
            self.image,
            "--module",
            self.module,
            no_rollback,
        ]
        if workers:
            append_args += ["--workers", "1"]
        executor = common.MinitrinoExecutor("lib-test", debug=self.debug)
        cmd = executor.build_cmd(
            base="provision",
            prepend=prepend_args,
            append=append_args,
        )
        cmd_result = executor.exec(cmd)
        if cmd_result.exit_code != 0:
            common.logger.info(cmd_result.output)
            raise RuntimeError(
                f"Provisioning of module '{self.module}' failed. Exiting test."
            )

        for t in tests:
            utils.log_status(
                f"Running test type '{t.get('type')}' "
                f"for module '{self.module}': '{t.get('name')}'"
            )
            if t.get("type") == "query":
                self._test_query(t)
            if t.get("type") == "shell":
                self._test_shell(t)
            if t.get("type") == "logs":
                self._test_logs(t)
            self.log_success(
                f"Module test type '{t.get('type')}' for module: '{self.module}'"
            )

        utils.log_status(f"Running test type 'restart' for module '{self.module}'")
        self._test_restart()
        self.log_success(f"Module test type 'restart' for module: '{self.module}'")

    def _test_query(self, json_data: dict) -> None:
        """
        Test query execution.

        Parameters
        ----------
        json_data : dict
            JSON containing query test data.
        """
        # Check inputs
        contains = json_data.get("contains", [])
        row_count = json_data.get("rowCount", None)
        retries = json_data.get("retries", 1)

        if not contains and row_count is None:
            raise KeyError(
                "JSON schema error: 'contains' and/or 'rowCount' "
                "must be defined in query tests"
            )

        # Wait for server to become available
        cmd = (
            "curl -X GET -H 'Accept: application/json' "
            "-H 'X-Trino-User: admin' 'localhost:8080/v1/info/'"
        )
        start = monotonic()
        while True:
            elapsed = monotonic() - start
            if elapsed > 60:
                raise TimeoutError(
                    "Timed out waiting for coordinator to become available"
                )
            cmd_result = common.execute_cmd(cmd, CONTAINER_NAME)
            if '"starting":false' in cmd_result.output:
                sleep(5)  # hard stop to ensure coordinator is ready
                break
            elif elapsed < 60:
                sleep(1)

        def _try_query(contains, row_count):
            sql = json_data.get("sql", "")
            cmd = f'trino-cli --debug --output-format CSV_HEADER --execute "{sql}"'
            args = json_data.get("trinoCliArgs", [])

            if args:
                for i in args:
                    cmd += f" {i}"

            cmd_result = common.execute_cmd(
                cmd, CONTAINER_NAME, json_data.get("env", {})
            )

            for c in contains:
                assert c in cmd_result.output, f"Output '{c}' not in query result"
            if row_count:
                row_count += 1  # Account for column header row
                query_row_count = cmd_result.output.count("\n")
                assert row_count == query_row_count, (
                    f"Expected row count: {row_count}, "
                    f"actual row count: {query_row_count}"
                )

        for i in range(retries):
            try:
                _try_query(contains, row_count)
                break
            except Exception as e:
                if i < retries - 1:
                    sleep(1.5)
                    continue
                else:
                    common.logger.error(f"Query failed after {retries} retries: {e}")
                    raise e

    def _test_shell(self, json_data: dict) -> None:
        """
        Test shell command execution.

        Parameters
        ----------
        json_data : dict
            JSON containing shell test data.
        """
        contains = json_data.get("contains", [])
        exit_code = json_data.get("exitCode", None)

        if not contains and exit_code is None:
            raise KeyError(
                "'contains' and/or 'exitCode' must be supplied in shell test criteria."
            )

        healthcheck = json_data.get("healthcheck", {})
        if healthcheck:
            self._execute_subcommand(healthcheck, healthcheck=True)
        cmd = json_data.get("command", "")
        container = json_data.get("container", None)
        cmd_result = common.execute_cmd(cmd, container, json_data.get("env", {}))

        if exit_code is not None:
            assert (
                exit_code == cmd_result.exit_code
            ), f"Unexpected exit code: {cmd_result.exit_code} expected: {exit_code}"

        for c in contains:
            assert c in cmd_result.output, f"'{c}' not in command output"

        subcommands = json_data.get("subCommands", [])
        if subcommands:
            prev_output = cmd_result.output
            for s in subcommands:
                prev_output = self._execute_subcommand(s, prev_output=prev_output)

    def _test_logs(self, json_data: dict) -> None:
        """
        Test log output.

        Parameters
        ----------
        json_data : dict
            JSON containing log test data.
        """
        container_name = json_data.get("container", "")
        timeout = json_data.get("timeout", 30)
        start = monotonic()
        while True:
            elapsed = monotonic() - start
            if elapsed > timeout:
                raise TimeoutError(
                    f"Failed to verify container logs after {timeout} seconds"
                )
            try:
                container = common.get_containers(container_name)[0]
                logs = container.logs().decode()
                for c in json_data.get("contains", []):
                    try:
                        assert c in logs, f"'{c}' not found in container log output"
                    except Exception:
                        logger.debug(
                            f"Log text match for '{c}' not found in container "
                            f"{container_name}. Retrying..."
                        )
                break
            except Exception:
                logger.debug(f"Failed to get container {container_name}. Retrying...")
            sleep(1)

    def _test_restart(self) -> None:
        """Test cluster restart."""
        executor = common.MinitrinoExecutor("lib-test", debug=self.debug)
        cmd = executor.build_cmd("restart")
        executor.exec(cmd)

        json_data = {
            "type": "logs",
            "name": "Ensure cluster is running after restart",
            "container": "minitrino-lib-test",
            "contains": ["CLUSTER IS READY"],
            "timeout": 60,
        }
        try:
            self._test_logs(json_data)
        except Exception as e:
            logger.error(f"Cluster failed to start after restart: {e}")
            raise e

    def _execute_subcommand(
        self, json_data: dict, healthcheck: bool = False, prev_output: str = ""
    ) -> str:
        """
        Execute a subcommand and return the output.

        Parameters
        ----------
        json_data : dict
            JSON containing subcommand data.
        healthcheck : bool
            Whether this is a healthcheck.
        prev_output : str
            Previous output.

        Returns
        -------
        str
            The output of the subcommand.
        """
        if healthcheck:
            cmd_type = "healthcheck"
            retry = json_data.get("retries", 30)
        else:
            cmd_type = "subcommand"
            retry = json_data.get("retries", 1)

        cmd = re.sub(
            r"\$\{PREV_OUTPUT\}", prev_output.strip(), json_data.get("command", "")
        )
        container = json_data.get("container", None)
        contains = json_data.get("contains", [])
        exit_code = json_data.get("exitCode", None)

        if not contains and exit_code is None:
            raise KeyError(
                f"'contains' and/or 'exitCode' must be supplied in shell {cmd_type}."
            )

        i = 0
        while True:
            try:
                cmd_result = common.execute_cmd(
                    cmd, container, json_data.get("env", {})
                )
                for c in contains:
                    assert c in cmd_result.output, f"'{c}' not in {cmd_type} output"
                if isinstance(exit_code, int):
                    assert exit_code == cmd_result.exit_code, (
                        f"Unexpected exit code: {cmd_result.exit_code} "
                        f"expected: {exit_code}"
                    )
                return cmd_result.output
            except Exception as e:
                if i < retry:
                    logger.debug(f"{cmd_type.title()} did not succeed. Retrying...")
                    i += 1
                    sleep(1)
                else:
                    raise TimeoutError(
                        f"'{c}' not in {cmd_type} output after {retry} retries. "
                        f"Last error: {e}"
                    )

    def _validate(self, json_data: dict) -> None:
        """
        Validate JSON input.

        Parameters
        ----------
        json_data : dict
            JSON containing test data.
        """
        test_type = json_data.get("type", "")
        spec = self.specs.get(test_type)
        assert isinstance(spec, dict), f"Invalid test type: {test_type}"
        jsonschema.validate(json_data, spec)
