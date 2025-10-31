# Installation and Upgrades

## Overview

- [Installation and Upgrades](#installation-and-upgrades)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Normal Installation](#normal-installation)
  - [Upgrades](#upgrades)
  - [Using Non-Default Docker Contexts](#using-non-default-docker-contexts)
  - [MacOS Users](#macos-users)
  - [A Note on Module Compatibility](#a-note-on-module-compatibility)
  - [Developer Installation](#developer-installation)
    - [Pre-Commit Hooks](#pre-commit-hooks)

## Requirements

- Docker
- Python & Pip
- Linux / MacOS

## Normal Installation

Minitrino is available on PyPI and the library is available for public download
on GitHub. To install it, run:

```sh
pip install minitrino
minitrino -v lib-install
```

Using this installation method, the `LIB_PATH` variable will point to
`~/.minitrino/lib/`, the directory where the `lib-install` command placed all
library files.

## Upgrades

To upgrade the Minitrino CLI, run:

```sh
pip install minitrino --upgrade
```

Each release has its own library. To upgrade the currently-installed library,
run:

```sh
minitrino -v lib-install
```

**Warning**: Installing the new library will overwrite all modules and snapshots
in the current library. If you have customized modules or snapshot files in
`lib/snapshots/`, make sure to take a backup of the `~/.minitrino/lib` directory
prior to running this command in order to persist your local changes.

## Using Non-Default Docker Contexts

Users operating on a non-default Docker Desktop context, e.g. Colima or
OrbStack, can set the desired context via:

```sh
docker context use <context>
```

To see available contexts:

```sh
docker context ls
```

Alternatively, the `DOCKER_HOST` environment variable can be used to point to
the desired context's `.sock` file as well, e.g.:

```sh
# Permanently set at OS (shell) level
echo 'export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"' >> ~/.bash_profile
source ~/.bash_profile

# Set for current shell session
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
minitrino -v provision ...

# Pass into the command
minitrino -v -e DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock" provision ...
```

Setting this environment variable overrides any context that's set using
`docker context use`.

## MacOS Users

The latest MacOS releases allow users to use
[built-in virtualization frameworks](https://docs.docker.com/desktop/settings/mac/)
that ship with Docker Desktop. To get the most out of the available modules, it
is recommended to run Minitrino on the latest MacOS with a virtualization
framework enabled.

Without a virtualization framework, some images will fail to run on ARM64 Macs,
such as the SQL Server and Db2 images.

## A Note on Module Compatibility

For any given Minitrino release, all modules are tested and verified to work
with the default Trino/Starburst version. This version is specified in the
`src/lib/minitrino.env`
[file](https://github.com/jefflester/minitrino/blob/master/src/lib/minitrino.env)
via the `CLUSTER_VER` variable. Consequently, modules are not guaranteed to work
on older or newer versions due to configuration incompatibilities or outdated,
dependent services (like a minimum server version for a data source, e.g.
MySQL). If you run into issues with a module on an older or newer Trino or
Starburst version, you may edit the module source to work with the version
you're attempting to deploy. See the [module building guide](build-a-module) for
instructions on creating/editing modules.

## Developer Installation

In the project's root directory, run `make install` to install the Minitrino CLI
and test packages. If you encounter errors during installation, try running
`make install-debug` for verbose output.

Alternatively, you can call the install script directly:

```sh
./install/src/install.sh
./install/src/install.sh -v  # For verbose output
```

Using this installation method, the `LIB_PATH` variable will point to
`${REPO_DIRECTORY}/src/lib/`. To test local changes, edit the code and then
recompile the packages by running `make install` again.

**Note**: If you encounter dependency version conflicts, consider using a
virtual environment to isolate the installation. To set up a virtual
environment, run:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Then, re-run `install.sh`.

### Pre-Commit Hooks

Before committing, install the `pre-commit` package and install the hooks from
the repository root:

```sh
pip install pre-commit
pre-commit install
pre-commit autoupdate
```

The hooks lint Python, YAML, and JSON files.

To lint all files in the repository, run:

```sh
pre-commit run --all-files --verbose
```
