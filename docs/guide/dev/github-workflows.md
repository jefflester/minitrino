# GitHub Workflows

All workflows are stored in `.github/workflows/`.

## Creation of a Release Branch

A release branch is any branch whose name matches the following regex:

```text
[0-9]\.[0-9]\.[0-9]
```

When a branch with this naming convention is created, the
`update-version-files.yaml` workflow is triggered. This workflow updates three
version references in three separate files to match the name of the new release
branch, then commits the changes to the new branch:

- `readme.md`
- `src/lib/version`
- `src/cli/setup.py`

Developers must run `git pull` after this workflow completes to ensure the local
branch remains in sync with the remote branch.

```sh
git checkout -B 3.0.0
git push --set-upstream origin 3.0.0

# Wait a few seconds for the workflow to run
git pull
```

## PR from Release Branch

When a PR is created from a release branch and targets `master`, the following
workflows are triggered:

- `lib-tests.yaml`
- `cli-tests.yaml`
- `test-release.yaml`

The first two workflows automate the tests described in [testing
overview](https://github.com/jefflester/minitrino/wiki/CLI-and-Library-Tests).
The `test-release.yaml` workflow creates a draft release and tag (`0.0.0`) with
the release branch as its target. This allows for the testing suite to have
access to an updated Minitrino library reflective of the current state of the
release branch.

## Merging a PR into `master`

Upon completion of the code tests and the merging of a feature branch PR into
`master`, the `release.yaml` workflow is triggered. This workflow:

- Creates a release whose name matches the name of the PR branch (e.g. `3.0.0`)
- Publishes the release and marks it as `latest`
- Builds the CLI package and publishes it to PyPi
