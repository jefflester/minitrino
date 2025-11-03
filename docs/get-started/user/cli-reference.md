# CLI Reference

This page provides a complete reference for all Minitrino CLI commands and
options.

## Global Options

The following options are available for all Minitrino commands:

- `--version` - Display the Minitrino version and exit
- `-v, --verbose` - Enable verbose output for detailed logging
- `--log-level` - Set the logging level (ERROR, WARN, INFO, DEBUG)
- `-e, --env` - Set environment variables (format: `KEY=VALUE`)
- `-c, --cluster` - Specify the cluster name (use `'*'` for all clusters)

## Commands

### provision

```{eval-rst}
.. click:: minitrino.cmd.provision:cli
   :prog: minitrino provision
   :nested: full
```

---

### down

```{eval-rst}
.. click:: minitrino.cmd.down:cli
   :prog: minitrino down
   :nested: full
```

---

### remove

```{eval-rst}
.. click:: minitrino.cmd.remove:cli
   :prog: minitrino remove
   :nested: full
```

---

### restart

```{eval-rst}
.. click:: minitrino.cmd.restart:cli
   :prog: minitrino restart
   :nested: full
```

---

### exec

```{eval-rst}
.. click:: minitrino.cmd.exec:cli
   :prog: minitrino exec
   :nested: full
```

---

### resources

```{eval-rst}
.. click:: minitrino.cmd.resources:cli
   :prog: minitrino resources
   :nested: full
```

---

### snapshot

```{eval-rst}
.. click:: minitrino.cmd.snapshot:cli
   :prog: minitrino snapshot
   :nested: full
```

---

### modules

```{eval-rst}
.. click:: minitrino.cmd.modules:cli
   :prog: minitrino modules
   :nested: full
```

---

### config

```{eval-rst}
.. click:: minitrino.cmd.config:cli
   :prog: minitrino config
   :nested: full
```

---

### lib-install

```{eval-rst}
.. click:: minitrino.cmd.lib_install:cli
   :prog: minitrino lib-install
   :nested: full
```

## Tips and Tricks

### Operating on All Clusters

You can use `-c '*'` to operate on all clusters simultaneously:

```sh
# Snapshot all clusters
minitrino -c '*' snapshot

# Stop all clusters
minitrino -c '*' down
```

### Setting Environment Variables

Environment variables can be set via the `-e` flag:

```sh
minitrino -e CLUSTER_VER=476 -e LIC_PATH=/path/to/license provision
```

### Debug Mode

For detailed debugging information, use verbose mode with DEBUG log level:

```sh
minitrino --verbose --log-level DEBUG provision -m hive
```

### Interactive Container Shell

Get an interactive shell in the coordinator container:

```sh
minitrino exec -i
```

Or specify a different container:

```sh
minitrino exec -c hive -i
```
