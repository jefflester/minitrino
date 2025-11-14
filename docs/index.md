# Minitrino

A command line tool that makes it easy to run modular Trino environments
locally.

Minitrino is ideal for local Trino development and testing, as it can deploy
both single-node and multi-node Trino clusters on-demand, along with a multitude
of technologies, any combination of which can be easily provisioned by the user.
Along with a local Trino cluster, Minitrino can provision:

- **Pre-configured plugins**: Authenticators, access control plugins, resource
  managers, and UIs.
- **Data sources**: Data sources for Trino connectors to connect to through
  pre-configured catalogs.
- **Related services**: Local object storage and metadata managers to support
  various, localized big data platforms (Hive, Delta, Iceberg, etc.).

All of this can be deployed with minimal to no configuration requirements.

[![PyPI
version](https://img.shields.io/pypi/v/minitrino)](https://pypi.org/project/minitrino/)
![CLI
Tests](https://github.com/jefflester/minitrino/actions/workflows/cli-tests.yaml/badge.svg)
![Library
Tests](https://github.com/jefflester/minitrino/actions/workflows/lib-tests-trino.yaml/badge.svg)
[![Trino
Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://trinodb.io/slack.html)

## Quick Start

To learn more about the CLI and underlying library, visit the following
documentation pages:

- [Installation and Upgrades](get-started/user/installation-and-upgrades)
- [Workflow Examples](get-started/user/workflow-examples)
- [Environment Variables and Config](get-started/user/environment-variables-and-config)
- [Build a Module](get-started/dev/build-a-module)

## Why Support Both Trino and Starburst?

Minitrino 3.0.0 introduces native support for both [Trino](https://trino.io/)
(open-source) and
[Starburst Enterprise Platform](https://docs.starburst.io/latest/index.html)
(SEP), giving users flexibility to work with either distribution.

### Unified Developer Experience

Whether you're working with Trino or Starburst, Minitrino provides a consistent,
easy-to-use interface for local development and testing. Switch between
distributions simply by setting the `IMAGE` environment variable.

### Community Support

Both Trino and Starburst have vibrant communities. This tool serves users across
the entire ecosystem—from open-source enthusiasts to enterprise
developers—making it easier to experiment, learn, and test features regardless
of your chosen distribution.

### Flexible Enterprise Testing

For Starburst users, Minitrino enables local testing of Enterprise features
using a license file, while Trino users can leverage the full open-source
ecosystem. Both distributions share the same modular architecture, allowing for
consistent workflows.

### Practical Benefits

The tool accommodates diverse use cases: testing Trino plugins, evaluating
Starburst Enterprise features, learning SQL-on-anything fundamentals, or
validating configurations before production deployment—all with minimal setup
and no cloud costs.

```{toctree}
---
caption: Getting Started
---
get-started/index
```

```{toctree}
---
caption: Modules
hidden:
---
modules/index
```

```{toctree}
---
caption: API Reference
maxdepth: 4
hidden:
glob:
---
api/index
```
