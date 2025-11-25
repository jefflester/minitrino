import json
import re
import subprocess
import sys
from pathlib import Path

SWITCHER_PATH = Path("docs/_static/switcher.json")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
# Blacklisted versions with broken documentation builds
BLACKLISTED_VERSIONS = {"3.0.0"}


def get_current_version():
    tag = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True
    ).stdout.strip()
    if tag:
        return tag
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    return branch


current_version = get_current_version()

# Only proceed if version matches pattern, or is "latest"
if current_version not in ("master", "main", "latest") and not VERSION_PATTERN.match(
    current_version
):
    print(
        f"Skipping switcher update: {current_version} does not match version pattern."
    )
    sys.exit(0)

# Skip blacklisted versions
if current_version in BLACKLISTED_VERSIONS:
    print(f"Skipping switcher update: {current_version} is blacklisted.")
    sys.exit(0)

current_url = f"https://minitrino.readthedocs.io/en/{current_version}/"

with open(SWITCHER_PATH) as f:
    entries = json.load(f)

# Remove any blacklisted versions from existing entries
entries = [e for e in entries if e["version"] not in BLACKLISTED_VERSIONS]

if not any(e["version"] == current_version for e in entries):
    new_entry = {"version": current_version, "url": current_url, "preferred": True}
    idx = 1 if entries and entries[0]["version"] == "latest" else 0
    entries.insert(idx, new_entry)

    # Optionally sort by version descending (excluding 'latest')
    def version_key(e):
        if e["version"] == "latest":
            return (0, "")
        return (1, tuple(int(x) for x in e["version"].split(".") if x.isdigit()))

    entries = sorted(entries, key=version_key, reverse=True)
    with open(SWITCHER_PATH, "w") as f:
        json.dump(entries, f, indent=2)
    subprocess.run(["git", "add", str(SWITCHER_PATH)], check=True)
    print(f"Added entry for {current_version}")
else:
    print(f"Entry for {current_version} already exists.")
