#!/usr/bin/env python3
"""Generate GitHub Actions test matrix for parallelized library tests.

This script dynamically generates a matrix of test segments by:
1. Fetching all available modules from minitrino
2. Filtering based on image type (trino excludes enterprise modules)
3. Filtering out skipCi modules when running in GitHub CI
4. Splitting modules into chunks of specified size
5. Outputting GitHub Actions matrix JSON
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any


def filter_skip_ci_modules(modules: list[str]) -> list[str]:
    """
    Filter out modules marked with skipCi: true from test JSON files.

    Parameters
    ----------
    modules : list[str]
        List of module names

    Returns
    -------
    list[str]
        Filtered list excluding modules with skipCi: true
    """
    # Determine path to test JSON directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(script_dir, "json")

    filtered = []
    for module in modules:
        json_path = os.path.join(json_dir, f"{module}.json")
        try:
            with open(json_path) as f:
                data = json.load(f)
                if not data.get("skipCi", False):
                    filtered.append(module)
                else:
                    print(
                        f"Skipping module '{module}' (skipCi: true)",
                        file=sys.stderr,
                    )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # If JSON doesn't exist or is invalid, include the module
            print(
                f"Warning: Could not check skipCi for '{module}': {e}",
                file=sys.stderr,
            )
            filtered.append(module)

    return filtered


def get_modules(image: str) -> list[str]:
    """
    Get list of modules to test based on image type.

    Parameters
    ----------
    image : str
        Image type: 'trino' or 'starburst'

    Returns
    -------
    list[str]
        Sorted list of module names to test
    """
    try:
        result = subprocess.run(
            ["minitrino", "modules", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        modules_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running minitrino modules: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from minitrino: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter modules based on image type
    if image == "trino":
        # Trino: exclude enterprise modules
        modules = [
            name
            for name, metadata in modules_data.items()
            if not metadata.get("enterprise", False)
        ]
    else:
        # Starburst: include all modules
        modules = list(modules_data.keys())

    # Exclude "test" module (used for CLI integration tests, not library tests)
    modules = [name for name in modules if name != "test"]

    # Filter out skipCi modules when running in GitHub CI
    is_github = os.environ.get("IS_GITHUB", "").lower() == "true"
    if is_github:
        modules = filter_skip_ci_modules(modules)

    # Sort for consistent ordering
    return sorted(modules)


def split_into_chunks(modules: list[str]) -> list[list[str]]:
    """
    Split module list evenly across optimal number of runners.

    The algorithm targets ~5 modules per runner, then distributes
    modules as evenly as possible across the calculated number of runners.

    Parameters
    ----------
    modules : list[str]
        List of module names

    Returns
    -------
    list[list[str]]
        List of module chunks, evenly distributed

    Examples
    --------
    >>> split_into_chunks(['a', 'b', 'c', 'd', 'e'])
    [['a', 'b', 'c', 'd', 'e']]  # 5 modules → 1 runner

    >>> split_into_chunks(['a'] * 23)
    [['a'] * 8, ['a'] * 8, ['a'] * 7]  # 23 modules → 3 runners (8, 8, 7)

    >>> split_into_chunks(['a'] * 35)
    [['a'] * 9, ['a'] * 9, ['a'] * 9, ['a'] * 8]  # 35 modules → 4 runners (9, 9, 9, 8)
    """
    import math

    num_modules = len(modules)
    if num_modules == 0:
        return []

    # Calculate optimal number of runners (target ~5 modules per runner)
    num_runners = math.ceil(num_modules / 5)

    # Calculate base modules per runner and remainder
    base_per_runner = num_modules // num_runners
    remainder = num_modules % num_runners

    # Distribute modules evenly
    chunks = []
    start_idx = 0
    for i in range(num_runners):
        # First 'remainder' runners get base+1, rest get base
        chunk_size = base_per_runner + (1 if i < remainder else 0)
        chunks.append(modules[start_idx : start_idx + chunk_size])
        start_idx += chunk_size

    return chunks


def generate_matrix(image: str) -> dict[str, Any]:
    """
    Generate GitHub Actions matrix configuration.

    Automatically calculates optimal number of runners and distributes
    modules evenly across them (targeting ~5 modules per runner).

    Parameters
    ----------
    image : str
        Image type: 'trino' or 'starburst'

    Returns
    -------
    dict
        GitHub Actions matrix configuration
    """
    modules = get_modules(image)
    chunks = split_into_chunks(modules)

    matrix = {
        "include": [
            {
                "segment": i + 1,
                "modules": " ".join(chunk),
                "module_count": len(chunk),
            }
            for i, chunk in enumerate(chunks)
        ]
    }

    return matrix


def main() -> None:
    """Generate library test matrix."""
    parser = argparse.ArgumentParser(
        description="Generate test matrix for parallelized library tests. "
        "Automatically distributes modules evenly across runners "
        "(targeting ~5 per runner)."
    )
    parser.add_argument(
        "--image",
        choices=["trino", "starburst"],
        required=True,
        help="Image type to test (trino excludes enterprise modules)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "github"],
        default="github",
        help="Output format: 'json' for pretty-printed JSON, "
        "'github' for Actions output",
    )

    args = parser.parse_args()

    matrix = generate_matrix(args.image)

    if args.output == "json":
        # Pretty-print for local testing
        print(json.dumps(matrix, indent=2))
    else:
        # GitHub Actions output format
        matrix_json = json.dumps(matrix)
        print(f"matrix={matrix_json}")

        # Also print summary for visibility
        total_modules = sum(item["module_count"] for item in matrix["include"])
        segments = len(matrix["include"])
        print(
            f"Generated {segments} test segments for {total_modules} modules",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
