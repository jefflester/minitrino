#!/usr/bin/env python3
r"""CLI for running library module tests.

Provides a convenient interface over pytest for running module test
suites with standard options::

    python ./src/tests/lib/runner.py \
        --debug --remove-images --image trino \
        ldap minio iceberg
"""

import argparse
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))

_src_dir = os.path.abspath(os.path.join(HERE, "../.."))
_repo_root = os.path.abspath(os.path.join(_src_dir, ".."))

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _get_retry_count() -> int:
    """Determine retry count from environment variables.

    Returns
    -------
    int
        Number of retry attempts (0 = no retries).
    """
    is_github = os.environ.get("IS_GITHUB", "").lower() == "true"
    retry_count = 1 if is_github else 0
    if "LIB_TEST_RETRY_COUNT" in os.environ:
        with contextlib.suppress(ValueError):
            retry_count = int(os.environ["LIB_TEST_RETRY_COUNT"])
    return retry_count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run module tests (delegates to pytest)."
    )
    parser.add_argument(
        "--image",
        choices=["trino", "starburst"],
        default="trino",
        help="Image to use for cluster container.",
    )
    parser.add_argument(
        "--remove-images",
        action="store_true",
        default=False,
        help="Remove images after each module test.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--lf",
        action="store_true",
        default=False,
        help="Rerun the last failed test(s) first.",
    )
    parser.add_argument(
        "-x",
        action="store_true",
        default=False,
        help="Exit on first failure.",
    )
    parser.add_argument(
        "--watchdog-timeout",
        type=int,
        default=600,
        help="Seconds of output silence before the watchdog kills the "
        "process (default: 600). Set to 0 to disable.",
    )
    parser.add_argument(
        "modules", nargs="*", help="Modules to test (e.g., ldap, iceberg)"
    )
    return parser.parse_args()


def main() -> None:
    """Translate runner args to pytest args and invoke pytest."""
    import pytest

    args = _parse_args()

    pytest_args: list[str] = [
        os.path.join(HERE, "test_modules.py"),
        "-s",
        "--override-ini=addopts=",
        "--image",
        args.image,
    ]

    if args.debug:
        pytest_args += ["-v"]

    if args.remove_images:
        pytest_args.append("--remove-images")

    if args.x:
        pytest_args.append("-x")

    if args.lf:
        pytest_args.append("--lf")

    if args.modules:
        pytest_args += ["--modules", " ".join(args.modules)]

    retry_count = _get_retry_count()
    if retry_count > 0:
        pytest_args += ["--reruns", str(retry_count), "--reruns-delay", "2"]

    if args.watchdog_timeout > 0:
        os.environ["WATCHDOG_TIMEOUT"] = str(args.watchdog_timeout)

    sys.exit(pytest.main(pytest_args))


if __name__ == "__main__":
    main()
