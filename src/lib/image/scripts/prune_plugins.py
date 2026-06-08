#!/usr/bin/env python3
"""Plugin pruner for Minitrino images.

Removes plugins listed in plugin-removelist.txt from a Trino/Starburst installation,
unless overridden by KEEP_PLUGINS (env var or argument).
"""

import argparse
import os
import shutil

LOG_PREFIX = "[prune_plugins]"


def load_removelist() -> list[str]:
    """Load the plugin removelist from plugin-removelist.txt.

    Returns
    -------
    list[str]
        List of plugin names to remove.
    """
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "data", "plugin-removelist.txt"),
        "/tmp/plugin-removelist.txt",
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path) as f:
                return [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
    print(f"{LOG_PREFIX} WARNING: plugin-removelist.txt not found, using empty list.")
    return []


def prune_plugins(cluster_dist: str, keep_plugins_env: str | None = None) -> None:
    """Remove plugins listed in the removelist from the plugin directory.

    Plugins in the removelist are deleted unless overridden by
    KEEP_PLUGINS. If KEEP_PLUGINS is "ALL", keeps all plugins.

    Parameters
    ----------
    cluster_dist : str
        Cluster distribution name ("trino" or "starburst").
    keep_plugins_env : str or None, optional
        Comma- or space-separated list of plugins to keep even if they
        appear in the removelist, or "ALL" to keep all plugins (default
        is None).
    """
    plugin_dir = f"/usr/lib/{cluster_dist}/plugin"
    if not os.path.isdir(plugin_dir):
        print(f"{LOG_PREFIX} Plugin dir {plugin_dir} does not exist; skipping prune.")
        return

    if keep_plugins_env and keep_plugins_env.strip().lower() == "all":
        print(f"{LOG_PREFIX} KEEP_PLUGINS=ALL specified; keeping all plugins.")
        return

    to_remove = set(load_removelist())
    if keep_plugins_env:
        overrides = [
            p.strip()
            for chunk in keep_plugins_env.split(",")
            for p in chunk.split()
            if p.strip()
        ]
        to_remove -= set(overrides)
        print(
            f"{LOG_PREFIX} Plugins overridden from removelist"
            f" by KEEP_PLUGINS: {overrides}"
        )
    for name in os.listdir(plugin_dir):
        if name in to_remove:
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
        help="Comma- or space-separated list of plugins to keep from the removelist",
    )
    args = parser.parse_args()
    keep_plugins_env = args.keep_plugins or os.environ.get("KEEP_PLUGINS")
    prune_plugins(args.cluster_dist, keep_plugins_env)


if __name__ == "__main__":
    main()
