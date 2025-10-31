# CLI and Library Tests

Tests are broken into CLI and library tests. PRs targeting the `master` branch
and new commits to said PRs trigger the following workflows, which automate each
test type:

- `.github/workflows/cli-tests.yaml`
- `.github/workflows/lib-tests-trino.yaml`
- `.github/workflows/lib-tests-sep.yaml`
- `.github/workflows/test-release.yaml`

To learn more about the workflows, visit the
[GitHub workflows overview](https://github.com/jefflester/minitrino/wiki/GitHub-Workflows).

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

CLI tests are organized into two categories:

- **Integration Tests** (`src/tests/cli/integration_tests/`): End-to-end tests
  that provision actual clusters and test complete workflows
- **Unit Tests** (`src/tests/cli/unit_tests/`): Fast, isolated tests for
  individual components and functions

To execute all CLI tests, run:

```sh
pytest src/tests/cli/
```

To execute only integration tests:

```sh
pytest src/tests/cli/integration_tests/
```

To execute only unit tests:

```sh
pytest src/tests/cli/unit_tests/
```

## Library Tests

Library tests are built using JSON files containing various tests for each
module. The tests and related logic are stored in `src/tests/lib/`. New module
tests are added in `src/tests/lib/json/`. **Tests are executed in the order they
are defined in the JSON files.**

To execute the library tests runner, run:

```sh
python src/tests/lib/runner.py
```

To execute a specific module test, run:

```sh
python src/tests/lib/runner.py ${MODULE}
```
