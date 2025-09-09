from pathlib import Path

import tomli

pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
requirements_path = Path(__file__).parent.parent / "docs" / "requirements.txt"

with open(pyproject_path, "rb") as f:
    pyproject = tomli.load(f)

docs_deps = (
    pyproject.get("project", {}).get("optional-dependencies", {}).get("docs", [])
)

# Remove any trailing commas or whitespace, sort, and deduplicate
docs_deps = sorted(set(dep.strip().rstrip(",") for dep in docs_deps))

header = "# Auto-generated from pyproject.toml [project.optional-dependencies.docs]\n"
with open(requirements_path, "w") as f:
    f.write(header)
    for dep in docs_deps:
        f.write(f"{dep}\n")

print(f"Wrote {len(docs_deps)} dependencies to {requirements_path}")
