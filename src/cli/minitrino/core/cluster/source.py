"""Source code build resolution and staging for local distribution builds."""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from minitrino.core.errors import UserError

if TYPE_CHECKING:
    from minitrino.core.envvars import EnvironmentVariables
    from minitrino.core.logging.logger import MinitrinoLogger

DIST_PATTERNS: dict[str, dict[str, str]] = {
    "starburst": {
        "target_path": os.path.join("core", "starburst-enterprise", "target"),
        "dir_prefix": "starburst-enterprise-",
    },
    "trino": {
        "target_path": os.path.join("core", "trino-server", "target"),
        "dir_prefix": "trino-server-",
    },
}

ARCH_SUFFIXES = ("-aarch64", "-x86_64")


@dataclass
class SourceBuild:
    """Result of resolving and staging a local source code build.

    Attributes
    ----------
    staging_dir : str
        Absolute path to the staged distribution directory.
    version : str
        Extracted version string (e.g., "468-e.5" or "474").
    distribution : str
        Distribution type ("starburst" or "trino").
    """

    staging_dir: str
    version: str
    distribution: str


def resolve_and_stage(
    source_path: str,
    distribution: str,
    env: EnvironmentVariables,
    user_dir: str,
    lib_dir: str,
    logger: MinitrinoLogger,
) -> SourceBuild:
    """Resolve a source code path and stage the distribution for Docker build.

    Parameters
    ----------
    source_path : str
        Path to a source repository root or direct distribution
        directory.
    distribution : str
        Distribution type from --image flag ("starburst", "trino", or
        "" for auto-detect).
    env : EnvironmentVariables
        Current environment variables (used to read KEEP_PLUGINS).
    user_dir : str
        Minitrino user directory (~/.minitrino/).
    lib_dir : str
        Minitrino library directory (contains image/scripts/).
    logger : MinitrinoLogger
        Logger instance.

    Returns
    -------
    SourceBuild
        Resolved and staged build information.
    """
    detected_dist, dist_dir = _detect_distribution(source_path, distribution, logger)
    dir_name = os.path.basename(dist_dir)
    prefix = DIST_PATTERNS[detected_dist]["dir_prefix"]
    version = _extract_version(dir_name, prefix)

    removelist = _load_plugin_removelist(lib_dir)
    keep_plugins = env.get("KEEP_PLUGINS", "")
    staging_dir = os.path.join(user_dir, ".staging", f"{detected_dist}-{version}")

    logger.info(f"Using local {detected_dist} build: {dist_dir} (version {version})")
    _stage_distribution(dist_dir, staging_dir, removelist, keep_plugins, logger)

    return SourceBuild(
        staging_dir=staging_dir,
        version=version,
        distribution=detected_dist,
    )


def _detect_distribution(
    path: str,
    distribution: str,
    logger: MinitrinoLogger,
) -> tuple[str, str]:
    """Detect the distribution type and locate the target directory.

    Parameters
    ----------
    path : str
        Source path (repo root or direct distribution directory).
    distribution : str
        User-specified distribution ("starburst", "trino", or "").
    logger : MinitrinoLogger
        Logger instance.

    Returns
    -------
    tuple[str, str]
        (distribution_type, distribution_directory_path)
    """
    if _is_distribution_dir(path):
        detected = _detect_dist_type_from_dir(path)
        if distribution and detected != distribution:
            raise UserError(
                f"Distribution mismatch: --image is '{distribution}' but the "
                f"distribution directory appears to be '{detected}'.",
                "Ensure --image matches your source code, or omit --image "
                "for auto-detection.",
            )
        logger.debug(f"Path is a direct distribution directory: {path}")
        return detected, path

    detected_dist = None
    dist_dir = None

    for dist_type, pattern in DIST_PATTERNS.items():
        target_path = os.path.join(path, pattern["target_path"])
        if os.path.isdir(target_path):
            found_dir = _find_best_dist_dir(target_path, pattern["dir_prefix"])
            if found_dir:
                detected_dist = dist_type
                dist_dir = found_dir
                break

    if not detected_dist or not dist_dir:
        raise UserError(
            f"Could not find distribution build output in '{path}'.",
            "Expected a Starburst Enterprise or Trino repository root with "
            "Maven build output. Have you run 'mvn install -DskipTests'?",
        )

    if distribution and detected_dist != distribution:
        raise UserError(
            f"Distribution mismatch: --image is '{distribution}' but "
            f"source code is '{detected_dist}'.",
            "Ensure --image matches your source code, or omit --image "
            "for auto-detection.",
        )

    return detected_dist, dist_dir


def _is_distribution_dir(path: str) -> bool:
    """Check if a path is a direct distribution directory."""
    return all(
        os.path.isdir(os.path.join(path, d)) for d in ("bin", "lib", "plugin")
    ) and os.path.isfile(os.path.join(path, "bin", "launcher"))


def _detect_dist_type_from_dir(path: str) -> str:
    """Infer distribution type from a direct distribution directory name."""
    name = os.path.basename(path)
    for dist_type, pattern in DIST_PATTERNS.items():
        if name.startswith(pattern["dir_prefix"]):
            return dist_type
    if os.path.isdir(os.path.join(path, "secrets-plugin")):
        return "starburst"
    return "trino"


def _find_best_dist_dir(target_path: str, prefix: str) -> str | None:
    """Find the best distribution directory in a target path.

    Prefers non-architecture-specific directories. When multiple
    versions exist, picks the most recently modified.

    Parameters
    ----------
    target_path : str
        Path to the Maven target directory.
    prefix : str
        Directory name prefix (e.g., "starburst-enterprise-").

    Returns
    -------
    str or None
        Absolute path to the best distribution directory, or None.
    """
    pattern = os.path.join(target_path, f"{prefix}*")
    generic = []
    arch_specific = []
    for d in glob.glob(pattern):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        if name.endswith("-hardlinks"):
            continue
        if not _is_distribution_dir(d):
            continue
        if name.endswith(ARCH_SUFFIXES):
            arch_specific.append(d)
        else:
            generic.append(d)

    candidates = generic or arch_specific
    if not candidates:
        return None

    candidates.sort(key=lambda d: os.path.getmtime(d), reverse=True)
    return candidates[0]


def _extract_version(dir_name: str, prefix: str) -> str:
    """Extract the version string from a distribution directory name."""
    if not dir_name.startswith(prefix):
        raise UserError(
            f"Cannot extract version from directory name '{dir_name}'.",
            f"Expected directory name starting with '{prefix}'.",
        )
    version = dir_name[len(prefix) :]
    for suffix in ARCH_SUFFIXES:
        if version.endswith(suffix):
            version = version[: -len(suffix)]
            break
    return version


def _load_plugin_removelist(lib_dir: str) -> list[str]:
    """Load the plugin removelist from plugin-removelist.txt.

    Parameters
    ----------
    lib_dir : str
        Minitrino library directory.

    Returns
    -------
    list[str]
        List of plugin names to remove during staging.
    """
    path = os.path.join(lib_dir, "image", "data", "plugin-removelist.txt")
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def _stage_distribution(
    dist_dir: str,
    staging_dir: str,
    removelist: list[str],
    keep_plugins: str,
    logger: MinitrinoLogger,
) -> None:
    """Stage the distribution directory for Docker build context.

    Uses rsync when available for fast incremental updates, with a
    shutil fallback.

    Parameters
    ----------
    dist_dir : str
        Path to the source distribution directory.
    staging_dir : str
        Path to the staging directory.
    removelist : list[str]
        Plugin names to exclude (unless overridden by KEEP_PLUGINS).
    keep_plugins : str
        KEEP_PLUGINS value (comma/space-separated names, "ALL", or "").
    logger : MinitrinoLogger
        Logger instance.
    """
    os.makedirs(staging_dir, exist_ok=True)

    # Work with 'ALL' or 'all'
    keep_all = keep_plugins.strip().lower() == "all" if keep_plugins else False
    extra_plugins: list[str] = []
    if keep_plugins and not keep_all:
        extra_plugins = [
            p.strip()
            for chunk in keep_plugins.split(",")
            for p in chunk.split()
            if p.strip()
        ]

    use_rsync = shutil.which("rsync") is not None
    sync_method = "rsync" if use_rsync else "shutil"
    logger.debug(f"Staging to {staging_dir} (sync method: {sync_method})")

    with logger.spinner("Staging local distribution..."):
        logger.debug("Staging bin/...")
        _sync_dir(
            os.path.join(dist_dir, "bin"),
            os.path.join(staging_dir, "bin"),
            use_rsync,
        )
        logger.debug("Staging lib/...")
        _sync_dir(
            os.path.join(dist_dir, "lib"),
            os.path.join(staging_dir, "lib"),
            use_rsync,
        )

        logger.debug("Staging plugins...")
        _stage_plugins(
            dist_dir, staging_dir, removelist, extra_plugins, keep_all, use_rsync
        )

        secrets_src = os.path.join(dist_dir, "secrets-plugin")
        if os.path.isdir(secrets_src):
            logger.debug("Staging secrets-plugin/...")
            _sync_dir(
                secrets_src,
                os.path.join(staging_dir, "secrets-plugin"),
                use_rsync,
            )

        notice_src = os.path.join(dist_dir, "NOTICE")
        if os.path.isfile(notice_src):
            shutil.copy2(notice_src, os.path.join(staging_dir, "NOTICE"))

    _prune_platform_binaries(staging_dir, logger)
    logger.debug(f"Staging complete: {staging_dir}")


def _stage_plugins(
    dist_dir: str,
    staging_dir: str,
    removelist: list[str],
    extra_plugins: list[str],
    keep_all: bool,
    use_rsync: bool,
) -> None:
    """Stage plugins from the distribution to the staging directory."""
    plugin_src = os.path.join(dist_dir, "plugin")
    plugin_dst = os.path.join(staging_dir, "plugin")
    os.makedirs(plugin_dst, exist_ok=True)

    _sync_dir(plugin_src, plugin_dst, use_rsync)

    if keep_all:
        return

    to_remove = set(removelist) - set(extra_plugins)
    for name in sorted(os.listdir(plugin_dst)):
        if name in to_remove:
            shutil.rmtree(os.path.join(plugin_dst, name), ignore_errors=True)


def _sync_dir(src: str, dst: str, use_rsync: bool) -> None:
    """Sync a directory from src to dst."""
    if not os.path.isdir(src):
        return
    if use_rsync:
        os.makedirs(dst, exist_ok=True)
        subprocess.run(
            ["rsync", "-a", "--delete", f"{src}/", f"{dst}/"],
            check=True,
            capture_output=True,
        )
    else:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def _prune_platform_binaries(staging_dir: str, logger: MinitrinoLogger) -> None:
    """Remove non-Linux and non-matching-architecture binaries."""
    bin_dir = os.path.join(staging_dir, "bin")
    if not os.path.isdir(bin_dir):
        return

    raw_arch = platform.machine()
    if raw_arch in ("x86_64", "amd64"):
        arch_bin = "amd64"
    elif raw_arch in ("arm64", "aarch64"):
        arch_bin = "arm64"
    else:
        return

    for name in os.listdir(bin_dir):
        path = os.path.join(bin_dir, name)
        if not os.path.isdir(path):
            continue
        if name.startswith("darwin-") or (
            name.startswith("linux-") and name != f"linux-{arch_bin}"
        ):
            logger.debug(f"Removing staged binary: {name}")
            shutil.rmtree(path, ignore_errors=True)
