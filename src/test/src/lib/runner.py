#!/usr/bin/env python3

import os
import re
import json
import time
import argparse
import jsonschema

import src.common as common
from src.lib.specs import SPECS
from src.lib.utils import cleanup
from src.lib.utils import dump_container_logs

from minitrino.settings import MIN_CLUSTER_VER


class ModuleTest:
    def __init__(self, json_data={}, module="", image=""):
        """Module Tests.

        Attributes
        ----------
        - `json_data`: JSON containing module test data.
        - `module`: Module name.
        - `image`: Image to use for cluster containers.
        - `specs`: JSON schema specifications for different test types."""

        self.json_data = json_data
        self.module = module
        self.image = image
        self.specs = SPECS

        common.log_status(f"Module tests for module: '{module}'")
        if self.skip_enterprise():
            return

        tests = json_data.get("tests", [])
        for t in tests:
            self._validate(t)

        self.run_tests(tests)
        cleanup()
        self.run_tests(tests, True)

    def skip_enterprise(self):
        """Skips the test if the module is enterprise and the image is
        'trino'."""

        output = common.execute_command(
            f"minitrino modules -m {self.module} -j | jq --arg module {self.module} '.[$module].enterprise'"
        )
        if self.image == "trino" and output.get("output") == "true":
            common.log_status(
                f"Module '{self.module}' is an enterprise module, skipping test"
            )
            return True

    def run_tests(self, tests=[], workers=False):
        """Runs module tests."""

        if self.image == "starburst":
            cluster_ver = str(MIN_CLUSTER_VER) + "-e"
        else:
            cluster_ver = MIN_CLUSTER_VER

        if not workers:
            output = common.execute_command(
                f"minitrino -v -e CLUSTER_VER={cluster_ver} "
                f"provision -i {self.image} -m {self.module}"
            )
        else:
            output = common.execute_command(
                f"minitrino -v -e CLUSTER_VER={cluster_ver} "
                f"provision -i {self.image} -m {self.module} --workers 1"
            )

        if output.get("exit_code") != 0:
            raise RuntimeError(
                f"Provisioning of module '{self.module}' failed. Exiting test."
            )

        for t in tests:
            common.log_status(
                f"Running test type '{t.get('type')}' for module '{self.module}': '{t.get('name')}'"
            )
            if t.get("type") == "query":
                self.test_query(t)
            if t.get("type") == "shell":
                self.test_shell(t)
            if t.get("type") == "logs":
                self.test_logs(t)
            common.log_success(
                f"Module test type '{t.get('type')}' for module: '{self.module}'"
            )

    def test_query(self, json_data={}):
        "Runs a query inside the cluster container using the trino-cli."

        # Check inputs
        contains = json_data.get("contains", [])
        row_count = json_data.get("rowCount", None)

        if not contains and row_count is None:
            raise KeyError(
                "JSON schema error: 'contains' and/or 'rowCount' must be defined in query tests"
            )

        # Wait for server to become available
        i = 0
        cmd = "curl -X GET -H 'Accept: application/json' -H 'X-Trino-User: admin' 'localhost:8080/v1/info/'"
        while i <= 60:
            output = common.execute_command(cmd, "minitrino")
            if '"starting":false' in output.get("output", ""):
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
        output = common.execute_command(cmd, "minitrino", json_data.get("env", {}))

        # Run assertions
        for c in contains:
            assert c in output.get("output"), f"Output '{c}' not in query result"
        if row_count:
            row_count += 1  # Account for column header row
            query_row_count = output.get("output").count("\n")
            assert (
                row_count == query_row_count
            ), f"Expected row count: {row_count}, actual row count: {query_row_count}"

    def test_shell(self, json_data={}):
        """Runs a command in a container or on the host shell."""

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
        output = common.execute_command(cmd, container, json_data.get("env", {}))

        # Run assertions
        if exit_code is not None:
            cmd_exit_code = output.get("exit_code")
            assert (
                exit_code == cmd_exit_code
            ), f"Unexpected exit code: {cmd_exit_code} expected: {exit_code}"

        for c in contains:
            assert c in output.get("output"), f"'{c}' not in command output"

        # Run subcommands
        subcommands = json_data.get("subCommands", [])
        if subcommands:
            for s in subcommands:
                output = self._execute_subcommand(
                    s, prev_output=output.get("output", "")
                )

    def test_logs(self, json_data):
        """Checks for matching strings in container logs."""

        timeout = json_data.get("timeout", 30)
        container = common.get_container(json_data.get("container"))

        i = 0
        while True:
            logs = container.logs().decode()
            try:
                for c in json_data.get("contains", []):
                    assert c in logs, f"'{c}' not found in container log output"
                break
            except:
                if i <= timeout:
                    print("Log text match not found. Retrying...")
                    time.sleep(1)
                    i += 1
                else:
                    raise TimeoutError(f"'{c}' not found in container log output")

    def _execute_subcommand(self, json_data={}, healthcheck=False, prev_output=""):
        """Executes healthchecks and subcommands."""

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
            output = common.execute_command(cmd, container, json_data.get("env", {}))
            try:
                for c in contains:
                    assert c in output.get(
                        "output", ""
                    ), f"'{c}' not in {cmd_type} output"
                cmd_exit_code = output.get("exit_code")
                if isinstance(exit_code, int):
                    assert (
                        exit_code == cmd_exit_code
                    ), f"Unexpected exit code: {cmd_exit_code} expected: {exit_code}"
                return output
            except AssertionError as e:
                if i < retry:
                    print(f"{cmd_type.title()} did not succeed. Retrying...")
                    i += 1
                    time.sleep(1)
                else:
                    raise TimeoutError(
                        f"'{c}' not in {cmd_type} output after {retry} retries. Last error: {e}"
                    )

    def _validate(self, json_data={}):
        """Validates JSON input."""

        test_type = json_data.get("type", "")
        spec = self.specs.get(test_type)
        jsonschema.validate(json_data, spec)


def main():
    """Minitrino library test runner.

    To run a specific module test, invoke this file with a module name as an
    arg, i.e. `python runner.py ldap`.

    If `--remove-images` is supplied as an argument, then all images (except the
    `minitrino/cluster` image) will be removed after each test. This is used to
    ensure the tests don't consume all the disk space on the GitHub Actions
    runner."""

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
            common.log_status(f"Module {module} test failed: {e}")
            dump_container_logs()
            cleanup(args.remove_images)
            raise e


if __name__ == "__main__":
    main()
