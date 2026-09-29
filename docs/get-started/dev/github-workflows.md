# GitHub Workflows

All workflows are stored in `.github/workflows/`.

## Creation of a Release Branch

A release branch is any branch whose name matches the following regex:

```text
[0-9]\.[0-9]\.[0-9]
```

The workflow `update-version-files.yaml` runs on release branches, updating the
following files to stay in sync with the current release:

- `readme.md`
- `src/lib/version`
- `pyproject.toml`

The version sync happens as soon as a release branch is created, so developers
should ensure they pull the remote changes or rebase before merging their
feature branches to a release branch.

## PR from Release Branch

When a PR is created from a release branch and targets `master`, the `ci.yaml`
workflow is triggered, which includes the following automated jobs:

- **Change detection** - Determines if image-related files changed
- **Test release creation** - Creates a prerelease tag (`0.0.0`) targeting the
  release branch, allowing the testing suite to access an updated Minitrino
  library reflective of the current state of the release branch
- **Image builds** - Builds Trino and Starburst test images in parallel via a
  matrix job (only runs if image files changed)
- **CLI tests** - Unit tests plus integration tests split into parallel matrix
  segments (Provision, Snapshot, Remove, Other)
- **Library tests** - Tests modules with both Trino and Starburst distributions
  via dynamically generated test matrices

All tests are described in detail in the [testing overview](cli-and-library-tests).

## Merging a PR into `master`

Upon completion of the code tests and the merging of a release branch PR into
`master`, the `release.yaml` workflow is triggered. This workflow runs in four
stages:

### Stage 1: PyPI Publish

- Builds the CLI package
- Publishes it to PyPI (idempotent - skips if version exists)
- Waits for PyPI availability before proceeding

### Stage 2: GitHub Release

- Creates a GitHub release whose name matches the merged PR branch (e.g.,
  `3.0.0`), using `release-notes/<version>.md` as the description
- The release is **not** marked as `latest` yet

### Stage 3: Smoke Test (Release Gate)

The workflow calls the reusable `smoke-test.yaml` workflow, which runs on both
**Ubuntu 22.04** and **macOS 15 (Intel)** to verify the PyPI package works
correctly in an isolated environment. On macOS, Docker is provided by Colima
with the Docker Compose v2 plugin.

The smoke test intentionally does **not** checkout the repository. This
simulates an end-user installation experience and catches bugs like library
path resolution that might incorrectly fall back to repository paths during
development.

**Tests performed:**

1. **Install from PyPI** - Installs the newly released version
1. **CLI accessibility** - Verifies `minitrino --version` and `--help` work
1. **Config command** - Tests `minitrino config --reset` without a library
   installed
1. **Library installation** - Tests `minitrino lib-install` without a library
   installed
1. **Modules command** - Verifies `minitrino modules` works with the installed
   library
1. **Docker check** - Verifies the Docker daemon and `docker compose` are
   available
1. **Provision smoke test** - Runs `minitrino provision` for 30 seconds; passes
   if provisioning is still running at the timeout or completes, and fails on
   any error

`smoke-test.yaml` can also be run outside of a release:

- **Manually** via `workflow_dispatch`, against any published version (defaults
  to the latest version on PyPI)
- **On pull requests** that modify `smoke-test.yaml`, against the latest
  published version, so changes to the smoke test are validated before they
  gate a release

### Stage 4: Mark Release as Latest

Only after the smoke test passes on all platforms is the GitHub release marked
as `latest`.

### Handling Failures

If the smoke test fails, the package is on PyPI and the GitHub release exists,
but it is not marked as `latest`. This means:

- Users who install by specific version can still access it
- `latest` continues to point to the previous release

To fix:

1. Create a new release branch with the fix
1. Bump the version (e.g., `3.0.3` → `3.0.4`)
1. Create a new release PR

If the failure was caused by the smoke test or CI environment rather than the
package, re-run the release workflow via `workflow_dispatch` with the same
version instead. The PyPI upload step is idempotent—it checks if the version
already exists before uploading—and the GitHub release is recreated.

## Automated Dependency Updates

Dependabot is configured to automatically monitor and update dependencies across
the project. Updates are proposed via pull requests on a weekly schedule
(Mondays).

### Monitored Ecosystems

- **Python packages** (pyproject.toml): Groups type stubs, documentation deps,
  and dev tools together. Security-critical dependencies (docker, click,
  requests, PyYAML) create individual PRs for visibility.
- **GitHub Actions** (workflow files): Groups Docker actions and GitHub official
  actions separately.
- **Docker images** (Dockerfiles): Monitors base images in
  `src/lib/image/Dockerfile` and `install/docs/Dockerfile`.

### Manual Updates Required

Docker image versions in `src/lib/minitrino.env` (e.g., `POSTGRES_VER`,
`MINIO_VER`) are not auto-detected by Dependabot and require periodic manual
review and updates.

### Reviewing Dependabot PRs

When reviewing Dependabot PRs:

1. Verify CI tests pass
1. Review changelog and breaking changes
1. For grouped updates (dev tools, docs deps), quick review is sufficient
1. For security-critical deps, perform thorough testing with affected CLI
   commands
