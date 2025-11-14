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

When a PR is created from a release branch and targets `master`, the following
workflows are triggered:

- `cli-tests.yaml`
- `lib-tests-trino.yaml` - Library tests for Trino distributions
- `lib-tests-sep.yaml` - Library tests for Starburst Enterprise Platform (SEP)
  distributions
- `test-release.yaml`

The first three workflows automate the tests described in
[testing overview](cli-and-library-tests). The `test-release.yaml` workflow
creates a draft release and tag (`0.0.0`) with the release branch as its target.
This allows for the testing suite to have access to an updated Minitrino library
reflective of the current state of the release branch.

## Merging a PR into `master`

Upon completion of the code tests and the merging of a feature branch PR into
`master`, the `release.yaml` workflow is triggered. This workflow:

- Creates a release whose name matches the name of the PR branch (e.g. `3.0.0`)
- Publishes the release and marks it as `latest`
- Builds the CLI package and publishes it to PyPi
