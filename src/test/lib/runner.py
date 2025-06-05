"""Test runner for Minitrino module tests."""

import argparse
import json
import os
import re
import time

import jsonschema

from minitrino.settings import MIN_CLUSTER_VER
from test import common
from test.lib.specs import SPECS
from test.lib.utils import cleanup, dump_container_logs, log_status, log_success


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
    specs : dict
        JSON schema specifications for different test types.
    """

    def __init__(self, json_data={}, module="", image=""):
        self.json_data = json_data
        self.module = module
        self.image = image
        self.specs = SPECS

        log_status(f"Module tests for module: '{module}'")
        if self.skip_enterprise():
            return

        tests = json_data.get("tests", [])
        for t in tests:
            self._validate(t)

        self.run_tests(tests)
        cleanup()
        self.run_tests(tests, True)

    def skip_enterprise(self) -> bool:
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
            f"minitrino modules -m {self.module} -j | "
            f"jq --arg module {self.module} '.[$module].enterprise'"
        )
        if self.image == "trino" and cmd_result.output == "true":
            log_status(f"Module '{self.module}' is an enterprise module, skipping test")
            return True
        return False

    def run_tests(self, tests=[], workers=False) -> None:
        """
        Run all tests for the module.

        Parameters
        ----------
        tests : list
            List of tests to run.
        workers : bool
            Whether to run tests with workers.
        """
        if self.image == "starburst":
            cluster_ver = str(MIN_CLUSTER_VER) + "-e"
        else:
            cluster_ver = str(MIN_CLUSTER_VER)

        if not workers:
            cmd_result = common.execute_cmd(
                f"minitrino -v -e CLUSTER_VER={cluster_ver} "
                f"provision -i {self.image} -m {self.module}"
            )
        else:
            cmd_result = common.execute_cmd(
                f"minitrino -v -e CLUSTER_VER={cluster_ver} "
                f"provision -i {self.image} -m {self.module} --workers 1"
            )

        if cmd_result.exit_code != 0:
            raise RuntimeError(
                f"Provisioning of module '{self.module}' failed. Exiting test."
            )

        for t in tests:
            log_status(
                f"Running test type '{t.get('type')}' "
                f"for module '{self.module}': '{t.get('name')}'"
            )
            if t.get("type") == "query":
                self.test_query(t)
            if t.get("type") == "shell":
                self.test_shell(t)
            if t.get("type") == "logs":
                self.test_logs(t)
            log_success(
                f"Module test type '{t.get('type')}' for module: '{self.module}'"
            )

    def test_query(self, json_data={}) -> None:
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

        if not contains and row_count is None:
            raise KeyError(
                "JSON schema error: 'contains' and/or 'rowCount' "
                "must be defined in query tests"
            )

        # Wait for server to become available
        i = 0
        cmd = (
            "curl -X GET -H 'Accept: application/json' "
            "-H 'X-Trino-User: admin' 'localhost:8080/v1/info/'"
        )
        while i <= 60:
            cmd_result = common.execute_cmd(cmd, "minitrino")
            if '"starting":false' in cmd_result.output:
                time.sleep(5)  # hard stop to ensure coordinator is ready
                break
            elif i < 60:
                time.sleep(1)
                i += 1
            else:
                raise TimeoutError(
                    "Timed out waiting for coordinator to become available"
                )

        # Build command
        sql = json_data.get("sql", "")
        cmd = f'trino-cli --debug --output-format CSV_HEADER --execute "{sql}"'
        args = json_data.get("trinoCliArgs", [])

        if args:
            for i in args:
                cmd += f" {i}"

        # Execute query
        cmd_result = common.execute_cmd(cmd, "minitrino", json_data.get("env", {}))

        # Run assertions
        for c in contains:
            assert c in cmd_result.output, f"Output '{c}' not in query result"
        if row_count:
            row_count += 1  # Account for column header row
            query_row_count = cmd_result.output.count("\n")
            assert (
                row_count == query_row_count
            ), f"Expected row count: {row_count}, actual row count: {query_row_count}"

    def test_shell(self, json_data={}) -> None:
        """
        Test shell command execution.

        Parameters
        ----------
        json_data : dict
            JSON containing shell test data.
        """
        # Check inputs
        contains = json_data.get("contains", [])
        exit_code = json_data.get("exitCode", None)

        if not contains and exit_code is None:
            raise KeyError(
                "'contains' and/or 'exitCode' must be supplied in shell test criteria."
            )

        # Wait for service
        healthcheck = json_data.get("healthcheck", {})
        if healthcheck:
            self._execute_subcommand(healthcheck, healthcheck=True)

        # Run command
        cmd = json_data.get("command", "")
        container = json_data.get("container", None)
        cmd_result = common.execute_cmd(cmd, container, json_data.get("env", {}))

        # Run assertions
        if exit_code is not None:
            assert (
                exit_code == cmd_result.exit_code
            ), f"Unexpected exit code: {cmd_result.exit_code} expected: {exit_code}"

        for c in contains:
            assert c in cmd_result.output, f"'{c}' not in command output"

        # Run subcommands
        subcommands = json_data.get("subCommands", [])
        if subcommands:
            for s in subcommands:
                self._execute_subcommand(s, prev_output=cmd_result.output)

    def test_logs(self, json_data) -> None:
        """
        Test log output.

        Parameters
        ----------
        json_data : dict
            JSON containing log test data.
        """
        timeout = json_data.get("timeout", 30)
        container = common.get_containers(json_data.get("container"))[0]

        i = 0
        while True:
            logs = container.logs().decode()
            try:
                for c in json_data.get("contains", []):
                    assert c in logs, f"'{c}' not found in container log output"
                break
            except Exception:
                if i <= timeout:
                    print("Log text match not found. Retrying...")
                    time.sleep(1)
                    i += 1
                else:
                    raise TimeoutError(f"'{c}' not found in container log output")

    def _execute_subcommand(
        self, json_data={}, healthcheck=False, prev_output=""
    ) -> None:
        """
        Execute a subcommand.

        Parameters
        ----------
        json_data : dict
            JSON containing subcommand data.
        healthcheck : bool
            Whether this is a healthcheck.
        prev_output : str
            Previous output.
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
            cmd_result = common.execute_cmd(cmd, container, json_data.get("env", {}))
            try:
                for c in contains:
                    assert c in cmd_result.output, f"'{c}' not in {cmd_type} output"
                if isinstance(exit_code, int):
                    assert exit_code == cmd_result.exit_code, (
                        f"Unexpected exit code: {cmd_result.exit_code} "
                        f"expected: {exit_code}"
                    )
            except AssertionError as e:
                if i < retry:
                    print(f"{cmd_type.title()} did not succeed. Retrying...")
                    i += 1
                    time.sleep(1)
                else:
                    raise TimeoutError(
                        f"'{c}' not in {cmd_type} output after {retry} retries. "
                        f"Last error: {e}"
                    )

    def _validate(self, json_data={}) -> None:
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


def main() -> None:
    """Run the test runner main entry point."""
    parser = argparse.ArgumentParser(
        description="Run module tests with optional flags."
    )
    parser.add_argument(
        "modules", nargs="*", help="Modules to test (e.g., ldap, iceberg)"
    )
    parser.add_argument(
        "--image",
        choices=["trino", "starburst"],
        default="trino",
        help="Image to use for cluster container",
    )
    parser.add_argument(
        "--remove-images",
        action="store_true",
        default=False,
        help="Remove images after run",
    )
    args = parser.parse_args()

    common.start_docker_daemon()
    cleanup()

    tests = os.path.join(os.path.dirname(__file__), "json")
    for t in os.listdir(tests):
        module = os.path.basename(t).split(".")[0]
        if args.modules and module not in args.modules:
            continue
        with open(os.path.join(tests, t)) as f:
            json_data = json.load(f)
        try:
            ModuleTest(json_data, module, args.image)
            cleanup(args.remove_images)
        except Exception as e:
            log_status(f"Module {module} test failed: {e}")
            dump_container_logs()
            cleanup(args.remove_images)
            raise e


if __name__ == "__main__":
    main()
