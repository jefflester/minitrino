# Welcome to Minitrino Documentation

Minitrino makes it easy to run modular Trino environments locally, with rich
support for Starburst features, custom modules, and developer workflows.

```{toctree}
:maxdepth: 2
:caption: User Guide

home.md
guide/user/installation-and-upgrades.md
guide/user/environment-variables-and-config.md
guide/user/workflow-examples.md
guide/user/troubleshooting.md
guide/user/reporting-bugs-and-contributing.md
```

```{toctree}
:maxdepth: 2
:caption: Developer Guides

guide/dev/build-a-module.md
guide/dev/cli-and-library-tests.md
guide/dev/github-workflows.md
```

```{toctree}
:maxdepth: 2
:caption: Admin Modules

modules/admin/cache-service.md
modules/admin/data-products.md
modules/admin/file-group-provider.md
modules/admin/insights.md
modules/admin/ldap-group-provider.md
modules/admin/minio.md
modules/admin/mysql-event-listener.md
modules/admin/resource-groups.md
modules/admin/results-cache.md
modules/admin/session-property-manager.md
modules/admin/spooling-protocol.md
```

```{toctree}
:maxdepth: 2
:caption: Catalog Modules

modules/catalog/clickhouse.md
modules/catalog/db2.md
modules/catalog/delta-lake.md
modules/catalog/elasticsearch.md
modules/catalog/faker.md
modules/catalog/hive.md
modules/catalog/iceberg.md
modules/catalog/mariadb.md
modules/catalog/mysql.md
modules/catalog/pinot.md
modules/catalog/postgres.md
modules/catalog/sqlserver.md
modules/catalog/stargate-parallel.md
modules/catalog/stargate.md
```

```{toctree}
:maxdepth: 2
:caption: Security Modules

modules/security/biac.md
modules/security/file-access-control.md
modules/security/ldap.md
modules/security/oauth2.md
modules/security/password-file.md
modules/security/tls.md
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/cluster.rst
api/cmd.rst
api/cmd_exec.rst
api/context.rst
api/docker.rst
api/envvars.rst
api/errors.rst
api/logging.rst
api/minitrino.cmd.rst
api/minitrino.rst
api/modules.rst
api/core.cluster.rst
api/core.docker.rst
api/core.logging.rst
api/core.rst
api/minitrino.core.cluster.rst
api/minitrino.core.docker.rst
api/minitrino.core.logging.rst
api/minitrino.core.rst
```

______________________________________________________________________

For more information, visit the [Minitrino GitHub
repository](https://github.com/jefflester/minitrino).
