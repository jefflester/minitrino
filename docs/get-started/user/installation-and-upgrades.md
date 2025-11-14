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

### Docker

- **Docker Desktop** (recommended): Version 4.0+ for macOS and Windows
- **Docker Engine**: Version 20.10+ for Linux
- **Alternative runtimes**: Colima, OrbStack, or Podman (with Docker socket
  compatibility)
- **Resources**: Minimum 4GB RAM allocated to Docker, 8GB+ recommended for
  multiple modules
- **Disk space**: 10-20GB free space depending on modules used

### Python

- **Python 3.10 or higher** required
- **Pip**: Version 20.0+ recommended
- **Virtual environment**: Optional but recommended for isolation

### Operating System

- **Linux**: Any modern distribution (Ubuntu 20.04+, Fedora 35+, etc.)
- **macOS**: macOS 11 (Big Sure) or higher
- **Windows**: Windows 10/11 with WSL2 (Windows Subsystem for Linux)
  - Minitrino must be run from within WSL2, not from Windows directly
  - Docker Desktop for Windows should be configured to use WSL2 backend

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

### Before You Upgrade

**Important considerations:**

1. **Check the release notes** for your target version at
   [github.com/jefflester/minitrino/releases](https://github.com/jefflester/minitrino/releases)
1. **Review breaking changes** - Major version upgrades (e.g., 2.x → 3.x) may
   have breaking changes
1. **Backup custom modules** - Library installation overwrites existing modules
1. **Note your configurations** - Document any custom environment variables or
   settings

### Upgrade Procedure

#### Step 1: Stop Running Clusters (Recommended)

While not strictly required, stopping clusters prevents potential conflicts:

```sh
# Stop all running clusters
minitrino down

# Optional: Remove containers to free up resources
minitrino remove
```

**Note:** Stopping containers is especially important if:

- Upgrading between major versions (e.g., 2.x → 3.x)
- The release notes mention Docker label changes
- You're experiencing unusual errors

#### Step 2: Backup Custom Work

If you've customized modules or created snapshots:

```sh
# Backup the entire library
cp -r ~/.minitrino/lib/ ~/.minitrino/lib-backup-$(date +%Y%m%d)

# Or backup specific items
cp -r ~/.minitrino/lib/modules/catalog/my-custom-module ~/backups/
cp -r ~/.minitrino/lib/snapshots/ ~/backups/
```

#### Step 3: Upgrade the CLI

```sh
# Upgrade to latest version
pip install minitrino --upgrade

# Or upgrade to specific version
pip install minitrino==3.0.0 --upgrade

# Verify new version
minitrino version
```

#### Step 4: Upgrade the Library

Each Minitrino release has its own library version. After upgrading the CLI,
install the matching library:

```sh
minitrino -v lib-install
```

**Warning:** This command will **overwrite all modules** in
`~/.minitrino/lib/modules/` and **delete all snapshots** in
`~/.minitrino/lib/snapshots/`. Ensure you've backed up any custom work.

#### Step 5: Update Configuration (if needed)

Check the release notes for configuration changes. For example, upgrading to
3.0.0 requires:

```sh
# Open config file
minitrino config

# Update variables (example for 3.0.0)
# Old:
# STARBURST_VER=443-e
#
# New:
CLUSTER_VER=476
IMAGE=trino  # or 'starburst'
```

#### Step 6: Test the Upgrade

Provision a test cluster to verify everything works:

```sh
# Provision a simple test cluster
minitrino -v -c test provision

# Check status
minitrino resources

# Clean up test cluster
minitrino -c test down
minitrino -c test remove
```

#### Step 7: Restore Custom Modules (if needed)

If you backed up custom modules, restore them:

```sh
# Copy custom module back
cp -r ~/backups/my-custom-module ~/.minitrino/lib/modules/catalog/

# Verify module is recognized
minitrino modules -m my-custom-module
```

### Version Compatibility

#### CLI and Library Versions

The CLI and library versions must match. Minitrino automatically detects
mismatches:

```sh
minitrino version
# CLI Version: 3.0.0
# Library Version: 2.2.4  ← Mismatch detected!
```

If there's a mismatch, run `minitrino lib-install` to sync versions.

#### Trino/Starburst Compatibility

Each Minitrino release is tested with specific Trino/Starburst versions:

| Minitrino Version | Trino Versions | Starburst Versions | Python Required |
| ----------------- | -------------- | ------------------ | --------------- |
| 3.0.0             | 443+           | 443-e+             | 3.10+           |
| 2.2.x             | 400+           | 400-e+             | 3.8+            |
| 2.0.x             | 351+           | 351-e+             | 3.7+            |

Check `lib/minitrino.env` for the default version:

```sh
cat ~/.minitrino/lib/minitrino.env | grep CLUSTER_VER
```

**Note:** Modules are tested with the default version. Using older or newer
Trino/Starburst versions may cause compatibility issues.

#### Module Version Requirements

Some modules have minimum version requirements. Check before provisioning:

```sh
# View module requirements
minitrino modules -m spooling-protocol --json | jq '.["spooling-protocol"].versions'
# Output: ["466", "9999"]  ← Requires Trino 466+
```

If you see version errors, either:

1. Upgrade your Trino/Starburst version:
   ```sh
   minitrino -v -e CLUSTER_VER=476 provision -m spooling-protocol
   ```
1. Use a module without version constraints

### Handling Breaking Changes

Major version upgrades may include breaking changes. Always review release
notes!

#### Example: Upgrading to 3.0.0

**Breaking Changes:**

1. **Python 3.10+ required** - Upgrade Python if needed
1. **Environment variables changed:**
   - `STARBURST_VER` → `CLUSTER_VER`
   - New `IMAGE` variable: `trino` or `starburst`
1. **Bootstrap scripts rewritten** - Custom bootstraps need updates
1. **Docker labels changed** - Scripts filtering by labels need updates

**Migration Steps:**

1. Upgrade Python: `python --version` (ensure 3.10+)

1. Update config file (see Step 5 above)

1. Update custom bootstrap scripts to use `before_start()` and `after_start()`
   functions

1. Update any scripts using Docker labels:

   ```sh
   # Old:
   docker ps --filter label=com.starburst.tests=minitrino

   # New:
   docker ps --filter label=org.minitrino.root=true
   ```

### Migrating Custom Modules

If you've built custom modules:

#### Option 1: Manual Migration

1. Backup custom module directory
1. Upgrade Minitrino
1. Copy custom module to new library
1. Test module with new version
1. Update if necessary (check metadata.json schema, bootstrap API, etc.)

#### Option 2: Use Module Snapshots

Before upgrading, snapshot custom modules:

```sh
# Create snapshot
minitrino snapshot --name my-custom-module-backup -m my-custom-module

# Snapshot is saved to lib/snapshots/
ls ~/.minitrino/lib/snapshots/
```

After upgrading:

```sh
# Extract and restore snapshot
cd ~/.minitrino/lib/
tar -xzf snapshots/my-custom-module-backup.tar.gz -C modules/catalog/
```

### Downgrading

If you need to downgrade after an upgrade:

```sh
# Downgrade CLI
pip install minitrino==2.2.4

# Install matching library
minitrino -v lib-install

# Update config if needed
minitrino config
```

**Note:** Downgrading may have its own compatibility issues. It's recommended to
test in a non-production environment first.

### Common Upgrade Issues

#### Issue: "Library version mismatch"

**Solution:** Run `minitrino lib-install`

#### Issue: "Module not found after upgrade"

**Solution:** Check if module was renamed or removed in release notes. Restore
from backup if it was a custom module.

#### Issue: "Configuration errors after upgrade"

**Solution:** Review release notes for configuration changes. Update
`~/.minitrino/minitrino.cfg` accordingly.

#### Issue: "Bootstrap scripts fail after upgrade"

**Solution:** Bootstrap API may have changed. Review new bootstrap documentation
and update scripts.

#### Issue: "Container fails to start after upgrade"

**Solution:** Remove old containers and images:

```sh
minitrino down
minitrino remove --images
minitrino -v provision  # Will rebuild images
```

### Getting Help

If you encounter issues during upgrade:

1. **Check release notes:**
   [github.com/jefflester/minitrino/releases](https://github.com/jefflester/minitrino/releases)
1. **Review troubleshooting guide:** [Troubleshooting](troubleshooting)
1. **Search GitHub issues:**
   [github.com/jefflester/minitrino/issues](https://github.com/jefflester/minitrino/issues)
1. **File a bug report:** [Reporting Bugs](reporting-bugs-and-contributing)

Include in your report:

- Previous Minitrino version
- New Minitrino version
- Full error message
- Output of `minitrino version`

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
you're attempting to deploy. See the
[module building guide](../dev/build-a-module) for instructions on
creating/editing modules.

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
