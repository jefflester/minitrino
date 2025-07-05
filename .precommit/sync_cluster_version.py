"""Sync the cluster version across all relevant files."""

import re
from pathlib import Path


def get_canonical_version() -> str:
    """Get the canonical version from minitrino.env."""
    env_path = Path("src/lib/minitrino.env")
    version = None
    for line in env_path.read_text().splitlines():
        if line.startswith("CLUSTER_VER="):
            version = line.split("=")[1].strip()
            break
    assert version, "CLUSTER_VER not found in minitrino.env"
    return version


def update_compose_yaml(version: str) -> None:
    """Update docker-compose.yaml with the canonical version."""
    compose_path = Path("src/lib/docker-compose.yaml")
    compose_text = compose_path.read_text()
    compose_text = re.sub(
        r"CLUSTER_VER: \$\{CLUSTER_VER:-\d+\}",
        f"CLUSTER_VER: ${{CLUSTER_VER:-{version}}}",
        compose_text,
    )
    compose_text = re.sub(
        r"\$\{CLUSTER_VER:-\d+\}", f"${{CLUSTER_VER:-{version}}}", compose_text
    )
    compose_path.write_text(compose_text)


def update_settings(version: str) -> None:
    """Update settings.py with the canonical version."""
    settings_path = Path("src/cli/minitrino/settings.py")
    settings_text = settings_path.read_text()
    settings_text = re.sub(
        r"DEFAULT_CLUSTER_VER\s*=\s*\d+",
        f"DEFAULT_CLUSTER_VER = {version}",
        settings_text,
    )
    settings_path.write_text(settings_text)


def main():
    """Sync the cluster version across all relevant files."""
    canonical_version = get_canonical_version()
    update_compose_yaml(canonical_version)
    update_settings(canonical_version)


if __name__ == "__main__":
    main()
