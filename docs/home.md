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
Tests](https://github.com/jefflester/minitrino/actions/workflows/lib-tests.yaml/badge.svg)
[![Trino
Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://trinodb.io/slack.html)

## Quick Start

To learn more about the CLI and underlying library, visit the following wiki
pages:

- [Installation and
  Upgrades](https://github.com/jefflester/minitrino/wiki/Installation-and-Upgrades)
- [Workflow
  Examples](https://github.com/jefflester/minitrino/wiki/Workflow-Examples)
- [Environment Variables and
  Config](https://github.com/jefflester/minitrino/wiki/Environment-Variables-and-Config)
- [Build a Module](https://github.com/jefflester/minitrino/wiki/Build-a-Module)

## Why Starburst for the Base Image?

Starburst offers an enterprise version of Trino called [Starburst Enterprise
Platform](https://docs.starburst.io/latest/index.html) (SEP), and SEP images are
used as the base for [Minitrino's
image](https://github.com/jefflester/minitrino/tree/master/src/lib/image). There
are a few reasons why it's advantageous to use SEP as the base image––some
personal and others community-facing.

### Community: Comprehensive Plugin Support

Starburst offers almost all of the open source Trino plugins as part of its
distribution, and those plugins are free to be used without any licensing.

### Community: Accessible Entry Point

Trino can be complicated, especially for beginners. This tool provides a way for
them to quickly grasp the fundamentals at little or no cost (e.g. no cloud
expenses) and with a lower time commitment.

### Community: Growing User Base

The number of Starburst users continues to grow, and this tool can help them
test, experiment with, and learn almost any feature.

### Personal: Practicality and Familiarity

I work at Starburst, and my colleagues and I find this tool to be generally
useful.

```{toctree}
:caption: Getting Started

get-started/index
```

```{toctree}
:caption: Modules
:hidden:

modules/index
```

```{toctree}
:caption: API Reference
:maxdepth: 4
:hidden:
:glob:

api/index
```
