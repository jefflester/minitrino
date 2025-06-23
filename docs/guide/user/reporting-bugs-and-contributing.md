# Reporting Bugs and Contributing

## Reporting Bugs

To report bugs and other issues, please file a [GitHub
issue](https://github.com/jefflester/minitrino/issues). Issues should:

- Contain any relevant log messages (if the bug relates to a command, running
  with the `-v` flag will make debugging easier)
- Describe what the expected outcome is
- Describe the proposed code fix (optional)

## Contributing

Contributors have two options:

1. Fork the repository, then make a PR to merge your changes
1. If you have been added as a repository contributor, you can go with the
   method above or you can create a feature branch, then submit a PR for that
   feature branch when it is ready to be merged.

In either case, please provide a comprehensive description of your changes with
the PR. PRs will never be merged directly to `master`; they are merged into a
release branch. To learn more about PR and release workflows, visit the [GitHub
workflows
overview](https://github.com/jefflester/minitrino/wiki/GitHub-Workflows).

If your contribution modifies or adds modules to the library, you must add
[library
tests](https://github.com/jefflester/minitrino/wiki/CLI-and-Library-Tests#library-tests)
for all affected modules.

If your contribution modifies the CLI, you must add [CLI
tests](https://github.com/jefflester/minitrino/wiki/CLI-and-Library-Tests#cli-tests)
to ensure your changes work.
