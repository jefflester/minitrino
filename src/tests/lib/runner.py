#!/usr/bin/env python3
"""Test runner for Minitrino module tests."""

import argparse
import json
import logging
import os
import sys
import traceback

SCRIPT_PATH = os.path.realpath(__file__)
HERE = os.path.dirname(SCRIPT_PATH)

src_dir = os.path.abspath(os.path.join(HERE, "../.."))
repo_root = os.path.abspath(os.path.join(src_dir, ".."))

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


from tests import common  # noqa: E402
from tests.lib import utils  # noqa: E402
from tests.lib.module_test import ModuleTest  # noqa: E402

CONTAINER_NAME = "minitrino-lib-test"


def log_complete_msgs(
    complete_msgs: list[tuple[str, bool, str]], error: BaseException | None = None
) -> None:
    """Log the status of each completed test, including timestamp.

    - If error is not None, raise it.
    - If any test failed, exit with code 1.
    - If all tests passed, exit with code 0.

    Parameters
    ----------
    complete_msgs : list of tuple[str, bool, str]
        Each tuple contains (message, success, timestamp).
    error : Exception | None
        Caught exception if any.
    """
    sep = "=" * utils.get_terminal_width() + "\n"
    underline = "-" * utils.get_terminal_width() + "\n"
    failed = False

    sys.stdout.write("\n" + sep)
    utils.log_status("::::: TEST RESULTS :::::")
    sys.stdout.write(underline)
    for msg, success, timestamp in complete_msgs:
        if success:
            ModuleTest.log_success(msg, timestamp=timestamp)
        else:
            ModuleTest.log_failure(msg, timestamp=timestamp)
            if not failed:
                failed = True
    total = len(complete_msgs)
    passed = sum(1 for _, success, _ in complete_msgs if success)
    sys.stdout.write(underline)
    utils.log_status(f"Summary: {passed}/{total} modules passed")
    sys.stdout.write(sep.rstrip() + "\n")

    if error:
        if isinstance(error, KeyboardInterrupt):
            sys.exit(130)
        else:
            raise error
    elif failed:
        sys.exit(1)
    else:
        sys.exit(0)


def run_module_test(
    module: str,
    json_data: dict,
    args: argparse.Namespace,
    complete_msgs: list[tuple[str, bool, str]],
    any_failed: bool,
) -> bool:
    """Run tests for a single module.

    Parameters
    ----------
    module : str
        Module name to test.
    json_data : dict
        Test configuration for the module.
    args : argparse.Namespace
        Command-line arguments.
    complete_msgs : list[tuple[str, bool, str]]
        List to append completion messages to.
    any_failed : bool
        Whether any previous tests have failed.

    Returns
    -------
    bool
        True if any tests have failed (including this one), False otherwise.
    """
    try:
        test = ModuleTest(json_data, module, args.image, debug=args.debug, x=args.x)
        if not test.run():
            return any_failed
        msg = f"All tests passed for module: '{module}'"
        test.log_success(msg)
        complete_msgs.append((msg, True, utils._timestamp()))
        test.cleanup(args.remove_images, args.debug)
        return any_failed
    except Exception as e:
        if any_failed:
            utils.record_failed_test(module, first=False)
        else:
            utils.record_failed_test(module, first=True)
        msg = f"Tests failed for module: '{module}'"
        test.log_failure(msg, e, utils._timestamp())
        if args.debug:
            traceback.print_exc()
        utils.dump_container_logs(args.debug)
        complete_msgs.append((msg, False, utils._timestamp()))
        if args.x:
            log_complete_msgs(complete_msgs, e)
        test.cleanup(args.remove_images, args.debug)
        return True


def get_retry_count() -> int:
    """Determine retry count based on environment variables.

    Returns
    -------
    int
        Number of retry attempts (0 means no retry, just one attempt).

    Notes
    -----
    - If IS_GITHUB=true: defaults to 1 retry
    - LIB_TEST_RETRY_COUNT env var overrides the default
    """
    is_github = os.environ.get("IS_GITHUB", "").lower() == "true"
    retry_count = 0
    if is_github:
        retry_count = 1  # Default retry count for CI
    # Override with explicit env var if set
    if "LIB_TEST_RETRY_COUNT" in os.environ:
        try:
            retry_count = int(os.environ["LIB_TEST_RETRY_COUNT"])
        except ValueError:
            common.logger.warning(
                f"Invalid LIB_TEST_RETRY_COUNT value: "
                f"{os.environ['LIB_TEST_RETRY_COUNT']}, using default"
            )

    if retry_count > 0:
        common.logger.info(f"Module test retry count: {retry_count}")

    return retry_count


def determine_modules_to_run(
    args: argparse.Namespace, all_modules: list[str]
) -> list[str]:
    """Determine which modules to run based on command-line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    all_modules : list[str]
        List of all available module names.

    Returns
    -------
    list[str]
        Sorted list of module names to run.

    Notes
    -----
    Priority order:
    1. --lf flag: Run last failed modules, then remaining modules
    2. Explicit module list: Run specified modules
    3. Default: Run all modules
    """
    modules_to_run: list[str] = []
    modules_run_set: set[str] = set()

    if args.lf:
        # Get failed modules from .lastfailed, sorted
        try:
            failed_modules = sorted(utils.get_failed_tests())
        except Exception:
            failed_modules = []
        # Only keep those that still exist in the json dir
        failed_modules = [m for m in failed_modules if m in all_modules]
        modules_to_run.extend(failed_modules)
        modules_run_set.update(failed_modules)
        # After .lastfailed, run the rest of the modules that come
        # after the last failed (in sorted order)
        if failed_modules:
            last_failed = failed_modules[-1]
            idx = all_modules.index(last_failed)
            rest = [m for m in all_modules[idx + 1 :] if m not in modules_run_set]
            modules_to_run.extend(rest)
    elif args.modules:
        # Use user-provided modules, sorted, and filter to those that exist
        modules_to_run = sorted([m for m in args.modules if m in all_modules])
    else:
        # Default: all modules, sorted
        modules_to_run = all_modules

    return modules_to_run


def run_module_with_retry(
    module: str,
    json_data: dict,
    args: argparse.Namespace,
    complete_msgs: list[tuple[str, bool, str]],
    any_failed: bool,
    retry_count: int,
) -> bool:
    """Run a module test with retry logic.

    Parameters
    ----------
    module : str
        Module name to test.
    json_data : dict
        Test configuration for the module.
    args : argparse.Namespace
        Command-line arguments.
    complete_msgs : list[tuple[str, bool, str]]
        List to append completion messages to.
    any_failed : bool
        Whether any previous tests have failed.
    retry_count : int
        Number of retry attempts.

    Returns
    -------
    bool
        True if any tests have failed, False otherwise.
    """
    prev_failed = any_failed

    # Retry loop for module test
    for attempt in range(retry_count + 1):
        if attempt > 0:
            common.logger.info(
                f"Retrying module '{module}' (attempt {attempt + 1}/{retry_count + 1})"
            )
            # Cleanup between retries
            ModuleTest.cleanup(args.remove_images, args.debug)
            # Remove the previous failure message from complete_msgs
            # so we can add a new result after retry
            if complete_msgs and complete_msgs[-1][0].endswith(f"'{module}'"):
                complete_msgs.pop()
            # Reset any_failed to prev_failed state for retry
            any_failed = prev_failed

        any_failed = run_module_test(module, json_data, args, complete_msgs, any_failed)

        # Check if this module passed
        # (any_failed didn't change from prev_failed)
        module_failed_this_attempt = any_failed and not prev_failed
        if not module_failed_this_attempt:
            # Module passed, exit retry loop
            break

        # Module failed on this attempt
        if attempt >= retry_count:
            # No more retries available
            break

    return any_failed


def execute_module_tests(
    args: argparse.Namespace, modules_to_run: list[str], retry_count: int
) -> tuple[list[tuple[str, bool, str]], bool]:
    """Execute tests for all specified modules.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    modules_to_run : list[str]
        List of module names to test.
    retry_count : int
        Number of retry attempts for each module.

    Returns
    -------
    tuple[list[tuple[str, bool, str]], bool]
        (complete_msgs, any_failed) - Test results and failure status.
    """
    tests = os.path.join(HERE, "json")
    complete_msgs: list[tuple[str, bool, str]] = []
    any_failed = False
    failed_this_run: list[str] = []

    for module in modules_to_run:
        json_file = os.path.join(tests, f"{module}.json")
        if not os.path.isfile(json_file):
            continue
        with open(json_file) as f:
            json_data = json.load(f)

        # Track state before running this module
        prev_failed = any_failed

        any_failed = run_module_with_retry(
            module, json_data, args, complete_msgs, any_failed, retry_count
        )

        # Track failures for recording
        if any_failed and not prev_failed:
            # This module caused the first failure
            failed_this_run.clear()  # -x: only record the first failure
        if any_failed:
            failed_this_run.append(module)
            if args.x:
                common.logger.debug("Recording failed module and exiting")
                utils.record_failed_test(module, first=True)
                return complete_msgs, any_failed

    # Record failed modules for --lf flag
    if failed_this_run and not args.x:
        record_failed_modules(failed_this_run)

    return complete_msgs, any_failed


def record_failed_modules(failed_modules: list[str]) -> None:
    """Record failed modules to .lastfailed file for --lf flag.

    Parameters
    ----------
    failed_modules : list[str]
        List of module names that failed.
    """
    common.logger.debug("Recording failed modules")
    with open(os.path.join(common.MINITRINO_USER_DIR, ".lastfailed"), "w") as f:
        for m in failed_modules:
            f.write(f"{m}\n")


def main() -> None:
    """Run the test runner main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run module tests with optional flags."
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
        help="Remove images after run. WARNING: This will remove all Minitrino images.",
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
        help="Rerun the last failed test(s).",
    )
    parser.add_argument(
        "-x",
        action="store_true",
        default=False,
        help="Exit on failure; do not rollback resources.",
    )
    parser.add_argument(
        "modules", nargs="*", help="Modules to test (e.g., ldap, iceberg)"
    )
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    common.logger = common.get_logger(log_level)

    # Initialize environment
    common.start_docker_daemon()
    ModuleTest.cleanup()

    # Determine configuration
    retry_count = get_retry_count()

    # Discover and filter modules
    tests = os.path.join(HERE, "json")
    all_json_files = [f for f in os.listdir(tests) if f.endswith(".json")]
    all_modules = sorted([os.path.splitext(f)[0] for f in all_json_files])
    modules_to_run = determine_modules_to_run(args, all_modules)

    # Execute tests
    try:
        complete_msgs, any_failed = execute_module_tests(
            args, modules_to_run, retry_count
        )
        log_complete_msgs(complete_msgs)
    except KeyboardInterrupt as e:
        ModuleTest.log_failure("Test run interrupted by user (Ctrl+C)", e)
        sys.exit(130)


if __name__ == "__main__":
    main()
