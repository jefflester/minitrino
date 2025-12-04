# GitHub Workflows

All workflows are stored in `.github/workflows/`.

## Creation of a Release Branch

A release branch is any branch whose name matches the following regex:

```text
[0-9]\.[0-9]\.[0-9]
```

When working on a release branch, version files are automatically synchronized to
match the branch name. This happens via a pre-commit hook
(`.precommit/sync_version_files.py`) that updates the following files on your
first commit:

- `readme.md`
- `src/lib/version`
- `pyproject.toml`

The version sync happens automatically when you commit, so no additional steps are
required:

```sh
git checkout -B 3.0.0
# Make changes
git commit -m "Your changes"
# Version files are automatically synced and staged by the pre-commit hook
git push --set-upstream origin 3.0.0
```

Additionally, the `update-version-files.yaml` workflow runs as a fallback when a
release branch is pushed to the remote repository, ensuring version files remain
synchronized even if the pre-commit hook did not run.

## PR from Release Branch

When a PR is created from a release branch and targets `master`, the `ci.yaml`
workflow is triggered, which includes the following automated jobs:

- **Change detection** - Determines which components changed (CLI, library, or image)
- **Test release creation** - Creates a draft release and tag (`0.0.0`) with the
  release branch as its target, allowing the testing suite to access an updated
  Minitrino library reflective of the current state of the release branch
- **CLI tests** - Unit and integration tests for the CLI (runs if CLI files changed)
- **Library tests** - Tests modules with both Trino and Starburst distributions
  (runs if library files changed)
- **Image build tests** - Builds and tests the container image (runs if image files
  changed)

All tests are described in detail in the [testing overview](cli-and-library-tests).

## Merging a PR into `master`

Upon completion of the code tests and the merging of a release branch PR into
`master`, the `release.yaml` workflow is triggered. This workflow runs in three
stages:

### Stage 1: PyPI Publish

- Builds the CLI package
- Publishes it to PyPI (idempotent - skips if version exists)
- Waits for PyPI availability before proceeding

### Stage 2: Smoke Test (Release Gate)

Before creating the GitHub release, the workflow runs comprehensive smoke tests
on both **Ubuntu 22.04** and **macOS 13** to verify the PyPI package works
correctly in an isolated environment.

The smoke test intentionally does **not** checkout the repository. This simulates
an end-user installation experience and catches bugs like library path resolution
that might incorrectly fall back to repository paths during development.

**Tests performed:**

1. **Install from PyPI** - Installs the newly released version
1. **CLI accessibility** - Verifies `minitrino --version` and `--help` work
1. **Config command** - Tests `minitrino config --reset` without a library
   installed
1. **Library installation** - Tests `minitrino lib-install` without a library
   installed
1. **Modules command** - Verifies `minitrino modules` works with the installed
   library
1. **Provision smoke test** - Runs `minitrino provision` for 30 seconds to
   validate the basic provisioning flow starts correctly

### Stage 3: GitHub Release (Only if Smoke Test Passes)

Only after the smoke test passes on all platforms:

- Creates a GitHub release whose name matches the merged PR branch (e.g., `3.0.0`)
- Publishes the release and marks it as `latest`

### Handling Failures

If the smoke test fails, the PyPI package has been published but no GitHub
release is created. This means:

- The package exists on PyPI but is not "officially" released
- Users who install by specific version can still access it
- No announcement or `latest` tag points to the broken version

To fix:

1. Create a new release branch with the fix
1. Bump the version (e.g., `3.0.3` → `3.0.4`)
1. Create a new release PR

The PyPI upload step is idempotent—it checks if the version already exists
before uploading, so re-running the release workflow will not fail on the
upload step.

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
