#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import jsonschema

import src.common as common
from src.lib.specs import SPECS
from src.lib.helpers import cleanup
from src.lib.helpers import get_container
from src.lib.helpers import execute_command


class ModuleTest:
    def __init__(self, json_data={}, module=""):
        """Module Tests.

        Attributes
        ----------
        - `json_data`: JSON containing module test data.
        - `module`: Module name.
        - `specs`: JSON schema specifications for different test types."""

        self.json_data = json_data
        self.module = module
        self.specs = SPECS

        common.log_status(f"Module tests for module: '{module}'")

        tests = json_data.get("tests", [])
        for t in tests:
            self.validate(t)

        execute_command(f"minitrino -v provision -m {self.module} --no-rollback")

        for t in tests:
            common.log_status(
                f"Module test type '{t.get('type')}' for module: '{module}'"
            )
            if t.get("type") == "query":
                self.test_query(t)
            if t.get("type") == "shell":
                self.test_shell(t)
            if t.get("type") == "logs":
                self.test_logs(t)
            common.log_success(
                f"Module test type '{t.get('type')}' for module: '{module}'"
            )

        common.log_success(f"Module tests for module: '{module}'")

    def test_query(self, json_data):
        "Runs a query inside the Trino container using the trino-cli."

        # Check inputs
        contains = json_data.get("successCriteria", {}).get("contains", [])
        row_count = json_data.get("successCriteria", {}).get("rowCount", None)

        if not contains and row_count is None:
            raise Exception(
                "'contains' and/or 'rowCount' must be supplied in query success criteria."
            )

        # Wait for server to become available
        i = 0
        cmd = "curl -X GET -H 'Accept: application/json' -H 'X-Trino-User: admin' 'localhost:8080/v1/info/'"
        while i <= 30:
            output = execute_command(cmd, "trino")
            if '"starting":false' in output.get("output", ""):
                time.sleep(5)  # hard stop to ensure coordinator is ready
                break
            else:
                time.sleep(1)
                i += 1

        # Build command
        sql = json_data.get("sql", "")
        cmd = f"trino-cli --debug --output-format CSV_HEADER --execute '{sql}'"
        args = json_data.get("trinoCliArgs", [])

        if args:
            for i in args:
                cmd += f" {i}"

        # Execute query
        output = execute_command(cmd, "trino", json_data.get("env", {}))

        # Run assertions
        for c in contains:
            assert c in output.get("output"), f"Output '{c}' not in query result"
        if row_count:
            row_count += 1  # Account for column header row
            query_row_count = output.get("output").count("\n")
            assert (
                row_count == query_row_count
            ), f"Expected row count: {row_count}, actual row count: {query_row_count}"

    def test_shell(self, json_data):
        """Runs a command in a container or on the host shell."""

        # Check inputs
        contains = json_data.get("successCriteria", {}).get("contains", [])
        exit_code = json_data.get("successCriteria", {}).get("exitCode", None)

        if not contains and exit_code is None:
            raise Exception(
                "'contains' and/or 'exitCode' must be supplied in shell success criteria."
            )

        # Wait for service
        healthcheck = json_data.get("healthcheck", {})
        if healthcheck:
            retry = healthcheck.get("retries", 0)
            cmd = healthcheck.get("command", "")
            hc_contains = healthcheck.get("contains", [])
            container = healthcheck.get("container", None)
            i = 0
            for c in hc_contains:
                while True:
                    output = execute_command(cmd, container)
                    try:
                        assert c in output.get(
                            "output", ""
                        ), f"'{c}' not in healthcheck output"
                        break
                    except:
                        if i <= retry:
                            print("Health check did not succeed. Retrying...")
                            time.sleep(1)
                            pass
                        else:
                            assert c in output.get(
                                "output", ""
                            ), f"'{c}' not in healthcheck output"

        # Run command
        cmd = json_data.get("command", "")
        container = json_data.get("container", None)
        output = execute_command(cmd, container)

        # Run assertions
        if exit_code is not None:
            assert exit_code == output.get(
                "return_code"
            ), f"Unexpected return code: {output.get('return_code')} expected: {exit_code}"

        for c in contains:
            assert c in output.get("output"), f"'{c}' not in command output"

    def test_logs(self, json_data):
        """Checks for matching strings in container logs."""

        # Determine how long to check for matches before failing
        timeout = get_container(json_data.get("timeout", None))
        if not timeout:
            timeout = 30

        container = get_container(json_data.get("container"))

        i = 0
        for c in json_data.get("successCriteria", {}).get("contains", []):
            while True:
                logs = container.logs().decode()
                try:
                    assert c in logs, f"'{c}' not found in container log output"
                    break
                except:
                    if i <= timeout:
                        print("Log text match not found. Retrying...")
                        time.sleep(1)
                        i += 1
                    else:
                        assert c in logs, f"'{c}' not found in container log output"

    def validate(self, json_data={}):
        """Validates JSON input."""

        test_type = json_data.get("type", "")
        spec = self.specs.get(test_type)
        jsonschema.validate(json_data, spec)


def main():
    """Minitrino library test runner. To run a specific module test, invoke this
    file with a module name as an arg, i.e. `python runner.py ldap`."""

    if len(sys.argv) == 2:
        run_only = sys.argv[1]
    else:
        run_only = None

    common.start_docker_daemon()
    cleanup()

    tests = os.path.join(os.path.dirname(__file__), "json")
    for t in os.listdir(tests):
        module = os.path.basename(t).split(".")[0]
        if run_only and module != run_only:
            continue
        with open(os.path.join(tests, t)) as f:
            json_data = json.load(f)
        ModuleTest(json_data, module)
        cleanup()


if __name__ == "__main__":
    main()
