<p align="center">
    <img alt="Minitrino Logo" src=".github/img/minitrino-small.png" />
</p>

# Minitrino

A command line tool that makes it easy to run modular Trino environments locally.

[![PyPI
version](https://img.shields.io/pypi/v/minitrino)](https://pypi.org/project/minitrino/)
![CI
Tests](https://github.com/jefflester/minitrino/actions/workflows/ci.yaml/badge.svg)
[![Trino
Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://trinodb.io/slack.html)

______________________________________________________________________

> **📘 [Complete Documentation](https://minitrino.readthedocs.io/)** - User
> guides, API reference, and all 39 modules

______________________________________________________________________

**Latest Stable Release**: 3.0.1

## What is Minitrino?

Minitrino lets you spin up complete Trino or Starburst clusters locally with
minimal configuration. Mix and match from **39+ modules** to create the exact
environment you need:

- **Catalogs**: Hive, Iceberg, Delta Lake, Postgres, MySQL, ClickHouse,
  Elasticsearch, and more
- **Security**: LDAP, OAuth2, Kerberos, TLS, BIAC, password files
- **Admin Tools**: MinIO, Insights, Cache Service, Resource Groups, SCIM

Perfect for local development, testing configurations, learning features, and
plugin development.

## Compatibility

- **[Trino](https://trino.io/)** versions 443 and later
- **[Starburst Enterprise](https://docs.starburst.io/latest/index.html)**
  versions 443-e and later

## Quick Start

### Installation

```sh
pip install minitrino
minitrino lib-install
```

### Run Your First Cluster

```sh
# Start a Trino cluster with Hive and Iceberg
minitrino -v provision -m hive -m iceberg

# Access the Trino UI at http://localhost:8080
# Or connect with the CLI
minitrino exec -i 'trino-cli'
```

### Switch to Starburst

```sh
# Use Starburst with enterprise modules
minitrino -v provision -i starburst -m insights -m cache-service
```

### Clean Up

```sh
minitrino down    # Stop the cluster
minitrino remove  # Remove all resources
```

## Key Features

- 🎯 **Zero Config** - Start clusters with a single command
- 🔧 **39+ Modules** - Pre-configured catalogs, security, and admin tools
- 🐳 **Docker-Based** - Isolated containers, no system pollution
- 🔄 **Multi-Cluster** - Run multiple independent clusters simultaneously
- 🚀 **Fast Setup** - First provision ~5 min, subsequent provisions ~30 sec
- 📦 **Both Distributions** - Switch between Trino and Starburst with a flag

## Documentation

**📘 [Complete Documentation](https://minitrino.readthedocs.io/)**

### Getting Started

- [Installation &
  Upgrades](https://minitrino.readthedocs.io/en/latest/get-started/user/installation-and-upgrades.html)
  - Install via PyPI, upgrade procedures, version compatibility
- [Workflow
  Examples](https://minitrino.readthedocs.io/en/latest/get-started/user/workflow-examples.html)
  - Complete guide with provisioning, modules, and configuration
- [CLI
  Reference](https://minitrino.readthedocs.io/en/latest/get-started/user/cli-reference.html)
  - All commands, options, and flags
- [Troubleshooting](https://minitrino.readthedocs.io/en/latest/get-started/user/troubleshooting.html)
  - Common issues and solutions

### For Developers

- [Build a
  Module](https://minitrino.readthedocs.io/en/latest/get-started/dev/build-a-module.html)
  - Step-by-step module creation guide
- [Testing
  Guide](https://minitrino.readthedocs.io/en/latest/get-started/dev/cli-and-library-tests.html)
  - CLI and library test documentation
- [GitHub
  Workflows](https://minitrino.readthedocs.io/en/latest/get-started/dev/github-workflows.html)
  - CI/CD and release process

### Resources

- [All
  Modules](https://minitrino.readthedocs.io/en/latest/modules/index.html) -
  Browse all 39 admin, catalog, and security modules
- [Environment Variables &
  Config](https://minitrino.readthedocs.io/en/latest/get-started/user/environment-variables-and-config.html)
  - Configuration hierarchy and customization
- [API
  Reference](https://minitrino.readthedocs.io/en/latest/api/index.html) -
  Python API documentation

## Support & Community

- 📖 [Documentation](https://minitrino.readthedocs.io/)
- 🐛 [Report
  Issues](https://github.com/jefflester/minitrino/issues)
- 💬 [Trino Slack](https://trinodb.io/slack.html)
- 🤝 [Contributing
  Guide](https://minitrino.readthedocs.io/en/latest/get-started/user/reporting-bugs-and-contributing.html)
