"""Sync version files to match branch name for release branches."""

import re
import subprocess
from pathlib import Path


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def is_version_branch(branch: str) -> bool:
    """Check if branch name matches version pattern (e.g., 3.0.1)."""
    return bool(re.match(r"^\d+\.\d+\.\d+$", branch))


def get_current_version() -> str | None:
    """Get the current version from src/lib/version file."""
    version_path = Path("src/lib/version")
    if not version_path.exists():
        return None
    return version_path.read_text().strip()


def update_lib_version(version: str) -> None:
    """Update src/lib/version file."""
    version_path = Path("src/lib/version")
    version_path.write_text(f"{version}\n")
    print(f"Updated {version_path}")


def update_pyproject_toml(version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    pyproject_text = pyproject_path.read_text()
    # Match version field in [project] section, not python_version
    updated_text = re.sub(
        r'^version = "[^"]*"',
        f'version = "{version}"',
        pyproject_text,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(updated_text)
    print(f"Updated {pyproject_path}")


def update_readme(version: str) -> None:
    """Update Latest Stable Release in readme.md."""
    readme_path = Path("readme.md")
    readme_text = readme_path.read_text()
    updated_text = re.sub(
        r"\*\*Latest Stable Release\*\*: \d+\.\d+\.\d+",
        f"**Latest Stable Release**: {version}",
        readme_text,
    )
    readme_path.write_text(updated_text)
    print(f"Updated {readme_path}")


def stage_files() -> None:
    """Stage the updated version files."""
    subprocess.run(
        ["git", "add", "src/lib/version", "pyproject.toml", "readme.md"],
        check=True,
    )
    print("Staged version files")


def main():
    """Sync version files to branch name for version branches."""
    branch = get_current_branch()

    # Only run on version branches
    if not is_version_branch(branch):
        return

    current_version = get_current_version()

    # Check if already synced
    if current_version == branch:
        return

    print(f"Syncing version files to {branch}")

    # Update all version files
    update_lib_version(branch)
    update_pyproject_toml(branch)
    update_readme(branch)

    # Stage the changes
    stage_files()

    print(f"Version files synced to {branch}")


if __name__ == "__main__":
    main()
