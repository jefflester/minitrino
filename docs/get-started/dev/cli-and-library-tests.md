# CLI and Library Tests

Tests are broken into CLI and library tests. PRs targeting the `master` branch
and new commits to said PRs trigger the following workflows, which automate each
test type:

- `.github/workflows/cli-tests.yaml`
- `.github/workflows/lib-tests.yaml`
- `.github/workflows/test-release.yaml`

To learn more about the workflows, visit the
[GitHub workflows overview](https://github.com/jefflester/minitrino/wiki/GitHub-Workflows).

## Install Test Packages

The testing package can be installed by running the `install.sh` script in the
repository's root directory or by installing the package directly via:

```sh
pip install --editable src/test/
```

## CLI Tests

CLI tests are built using
[Click's CLI runner](https://click.palletsprojects.com/en/8.1.x/testing/) and
thoroughly test the CLI's commands and options. The tests and related logic are
stored in `src/test/src/cli/`.

To execute the CLI test runner manually, run:

```sh
python src/test/src/cli/runner.py
```

## Library Tests

Library tests are built using JSON files containing various tests for each
module. The tests and related logic are stored in `src/test/src/lib/`. The JSON
specification for each test type are stored in `src/test/src/lib/specs.py`, and
new module tests are added in `src/test/src/lib/json/`. **Tests are executed in
the order they are defined in the JSON files.**

To execute the library tests runner, run:

```sh
python src/test/src/lib/runner.py
```

To execute a specific module test, run:

```sh
python src/test/src/lib/runner.py ${MODULE}
```
