#!/usr/bin/env python3
"""
Plugin pruner for Minitrino images.

Removes unused plugins from the plugin directory of a Trino/Starburst
installation, keeping only those in a static allowlist and any specified
by KEEP_PLUGINS (env var or argument).
"""
import argparse
import os
import shutil
from typing import Optional

LOG_PREFIX = "[prune_plugins]"


def prune_plugins(cluster_dist: str, keep_plugins_env: Optional[str] = None) -> None:
    """
    Remove unused plugins from the plugin directory.

    Keep only those in the static list and any specified by
    KEEP_PLUGINS.

    Parameters
    ----------
    cluster_dist : str
        Cluster distribution name ("trino" or "starburst").
    keep_plugins_env : str or None, optional
        Comma- or space-separated list of additional plugins to keep
        (default is None).
    """
    keep = [
        "audit-log",
        "clickhouse",
        "delta-lake",
        "elasticsearch",
        "exchange-filesystem",
        "exchange-hdfs",
        "faker",
        "functions-python",
        "generic-jdbc",
        "geospatial",
        "group-providers",
        "hive",
        "iceberg",
        "jmx",
        "mariadb",
        "memory",
        "mysql",
        "mysql-event-listener",
        "okta-authenticator",
        "opensearch",
        "oracle",
        "password-authenticators",
        "pinot",
        "postgresql",
        "resource-group-managers",
        "sep-stargate",
        "session-property-managers",
        "sep-sqlserver",
        "spooling-filesystem",
        "sqlserver",
        "starburst-functions",
        "starburst-hive-based-ranger",
        "starburst-ranger",
        "stargate-parallel",
        "thrift",
        "tpcds",
        "tpch",
        "warp-speed",
    ]
    if keep_plugins_env:
        extra = [
            p.strip()
            for chunk in keep_plugins_env.split(",")
            for p in chunk.split()
            if p.strip()
        ]
        keep.extend(extra)
        print(f"{LOG_PREFIX} Additional plugins to keep from KEEP_PLUGINS: {extra}")
    plugin_dir = f"/usr/lib/{cluster_dist}/plugin"
    if not os.path.isdir(plugin_dir):
        print(f"{LOG_PREFIX} Plugin dir {plugin_dir} does not exist; skipping prune.")
        return
    for name in os.listdir(plugin_dir):
        if name not in keep:
            path = os.path.join(plugin_dir, name)
            print(f"{LOG_PREFIX} Removing plugin: {name}")
            shutil.rmtree(path, ignore_errors=True)


def main() -> None:
    """Run plugin pruner."""
    parser = argparse.ArgumentParser(
        description="Prune plugins from a Minitrino installation."
    )
    parser.add_argument(
        "cluster_dist", help="Cluster distribution name (trino or starburst)"
    )
    parser.add_argument(
        "--keep-plugins",
        dest="keep_plugins",
        default=None,
        help="Comma- or space-separated list of additional plugins to keep",
    )
    args = parser.parse_args()
    # Prefer CLI arg, then env var
    keep_plugins_env = args.keep_plugins or os.environ.get("KEEP_PLUGINS")
    prune_plugins(args.cluster_dist, keep_plugins_env)


if __name__ == "__main__":
    main()
