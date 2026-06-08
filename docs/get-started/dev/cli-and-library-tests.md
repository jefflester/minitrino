# CLI and Library Tests

Tests are broken into CLI and library tests. PRs targeting the `master` branch
and new commits to said PRs trigger the CI workflow (`.github/workflows/ci.yaml`),
which automates all test types including CLI tests, library tests for both Trino
and Starburst distributions, and test release creation.

To learn more about the workflows, visit the
[GitHub workflows overview](github-workflows).

## Install Test Packages

The testing package can be installed by running the `install` script in the
repository's root directory or by installing the package directly via:

```sh
pip install --editable src/tests/
```

## CLI Tests

CLI tests are built using [pytest](https://docs.pytest.org/) and
[Click's CLI runner](https://click.palletsprojects.com/en/8.1.x/testing/), and
thoroughly test the CLI's commands and options. The tests and related logic are
stored in `src/tests/cli/`.

### Test Organization

CLI tests are organized into two categories:

- **Integration Tests** (`src/tests/cli/integration_tests/`): End-to-end tests
  that provision actual Docker clusters and test complete workflows. These tests
  are slower but provide comprehensive validation.
- **Unit Tests** (`src/tests/cli/unit_tests/`): Fast, isolated tests for
  individual components and functions. These tests use mocks and don't require
  Docker containers.

### Running CLI Tests

**Run all CLI tests** (integration + unit):

```sh
pytest src/tests/cli/
```

**Run only integration tests** (requires Docker):

```sh
pytest src/tests/cli/integration_tests/
```

**Run only unit tests** (fast, no Docker required):

```sh
pytest src/tests/cli/unit_tests/
```

**Run a specific test file**:

```sh
pytest src/tests/cli/integration_tests/test_cmd_provision.py -v
```

**Run a specific test function**:

```sh
pytest src/tests/cli/integration_tests/test_cmd_provision.py::test_provision_with_modules -v
```

**Run tests with verbose output and logging**:

```sh
pytest src/tests/cli/ -vv -s --log-cli-level=DEBUG
```

### Using Make Targets

The project includes convenient Make targets for running tests:

```sh
# Run all unit tests with coverage report
make unit-tests

# Run all integration tests
make integration-tests

# Run failed tests first, then continue (useful for debugging)
make integration-tests FF=1

# Run all tests (unit + integration)
make all-tests

# Generate HTML coverage report
make coverage
```

### Test Execution Tips

**Quick feedback loop** - Run unit tests first for fast validation:

```sh
make unit-tests  # Takes ~30 seconds
```

**Pre-commit validation** - Run both test types before committing:

```sh
make all-tests  # Takes 5-10 minutes
```

**Debugging failures** - Use verbose mode with stdout capture disabled:

```sh
pytest src/tests/cli/integration_tests/test_cmd_provision.py -vv -s
```

**Filter by test name pattern**:

```sh
pytest src/tests/cli/ -k "provision" -v  # Runs all tests with "provision" in name
```

### Understanding Test Output

**PASSED** ✓ - Test executed successfully **FAILED** ✗ - Test assertion failed,
check the traceback **SKIPPED** - Test was skipped (usually platform-specific)
**ERROR** - Test encountered an error before assertions

Example output:

```
src/tests/cli/integration_tests/test_cmd_provision.py::test_provision_basic PASSED  [10%]
src/tests/cli/integration_tests/test_cmd_provision.py::test_provision_with_hive PASSED [20%]
```

### Coverage Requirements

The project aims for **90% test coverage** as a quality goal. Coverage is
collected for all test runs, though CI workflows do not enforce hard thresholds
for integration tests. To check coverage locally:

```sh
make coverage
```

Then open `htmlcov/index.html` in your browser to see the detailed coverage
report.

## Library Tests

Library tests validate module deployments using JSON-driven test scenarios.
These tests provision actual clusters with modules and validate functionality
through queries, log checks, and container commands. The tests and related logic
are stored in `src/tests/lib/`.

Library tests are built on [pytest](https://docs.pytest.org/) with a CLI
wrapper (`runner.py`) for convenience. Each JSON test file becomes a
parametrized pytest test case, giving you retry support (`--reruns`), failure
filtering (`--lf`), and standard pytest output.

### Test Organization

- **JSON Test Definitions** (`src/tests/lib/json/`): Test scenarios defined in
  JSON
- **Test Runner** (`src/tests/lib/runner.py`): CLI wrapper that translates
  runner flags to pytest arguments
- **Pytest Entry Point** (`src/tests/lib/test_modules.py`): Parametrized test
  function, one case per JSON file
- **Pytest Config** (`src/tests/lib/conftest.py`): Fixtures for setup, cleanup,
  and custom options (`--image`, `--modules`, `--remove-images`)
- **ModuleTest Class** (`src/tests/lib/module_test.py`): Core test execution
  logic

**Note:** Tests are executed in the order they are defined in the JSON files.

### Running Library Tests

**Run all library tests** (tests all modules):

```sh
python src/tests/lib/runner.py
```

**Run tests for a specific module**:

```sh
python src/tests/lib/runner.py hive
python src/tests/lib/runner.py iceberg
python src/tests/lib/runner.py ldap
```

**Run tests for a specific Trino/Starburst version**:

```sh
# Test with Trino
python src/tests/lib/runner.py --image trino

# Test with Starburst Enterprise
python src/tests/lib/runner.py --image starburst
```

**Use Make targets**:

```sh
# Run all library tests (defaults to Starburst, see Makefile)
make lib-tests

# Run library tests with license file
LIC_PATH=/path/to/license make lib-tests

# Run library tests for specific modules
make lib-tests ARGS="hive iceberg"
```

**Run via pytest directly** (advanced):

```sh
pytest src/tests/lib/test_modules.py -s --image starburst --modules "hive iceberg"
```

### Starburst Version Resolution

When running Starburst tests, the test runner automatically resolves the latest
LTS patch release. For example, if the base version is `479`, the runner queries
the Starburst release bucket and resolves it to the latest patch (e.g.,
`479-e.8`) rather than using the initial `479-e` release.

This also applies to the `provision` CLI command. When a user provides a bare
version like `479-e`, Minitrino resolves it to the latest patch and logs the
resolved version. To pin the initial release explicitly, use `479-e.0`.

### Understanding Library Test Structure

Each JSON test file can contain multiple test types:

1. **Query Tests**: Execute SQL queries and validate results
1. **Log Tests**: Check container logs for expected messages
1. **Command Tests**: Run commands in containers and validate output

Example test scenario structure:

```json
{
  "module": "hive",
  "tests": [
    {
      "type": "query",
      "query": "SHOW CATALOGS",
      "expected": "hive"
    },
    {
      "type": "log",
      "container": "hive",
      "expected": "Hive Metastore started"
    }
  ]
}
```

### Test Execution Tips

**Test a specific module after changes**:

```sh
python src/tests/lib/runner.py my-module
```

**Run with debug output**:

```sh
python src/tests/lib/runner.py --debug hive
```

**Rerun only the last failed tests**:

```sh
python src/tests/lib/runner.py --lf
```

**Debug library test failures**:

1. Check the test output for the specific failure
1. Inspect running containers: `docker ps`
1. Check container logs: `docker logs <container-name>`
1. Connect to Trino CLI for manual testing: `minitrino exec -i 'trino-cli'`

### CI/CD Integration

The GitHub CI workflow (`.github/workflows/ci.yaml`) automatically runs library
tests for both Trino and Starburst Enterprise distributions, testing multiple
versions to ensure compatibility.

### Test Duration

- **CLI Unit Tests**: ~30 seconds
- **CLI Integration Tests**: ~25-30 minutes in CI (parallelized across provision
  and other tests)
- **Library Tests (single module)**: ~2-3 minutes
- **Library Tests (all modules)**: ~30-60 minutes (varies by modules)

### When to Run Which Tests

| Scenario                 | Tests to Run                 | Command                                 |
| ------------------------ | ---------------------------- | --------------------------------------- |
| Quick validation         | CLI unit tests               | `make unit-tests`                       |
| Before committing        | All CLI tests                | `make all-tests`                        |
| After module changes     | Specific module library test | `python src/tests/lib/runner.py MODULE` |
| Before PR                | Full test suite              | `make all-tests && make lib-tests`      |
| After changing core code | Everything                   | CI will run all tests automatically     |
