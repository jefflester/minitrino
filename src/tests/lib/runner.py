#!/usr/bin/env python3
"""Test runner for Minitrino module tests."""

import argparse
import json
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
    """
    Log the status of each completed test, including timestamp.

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
    sep = "=" * utils.TERMINAL_WIDTH + "\n"
    underline = "-" * utils.TERMINAL_WIDTH + "\n"
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


def main() -> None:
    """Run the test runner main entry point."""
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

    common.start_docker_daemon()
    ModuleTest.cleanup()

    tests = os.path.join(HERE, "json")
    complete_msgs: list[tuple[str, bool, str]] = []  # (message, success, timestamp)

    def run_module_test(module, json_data, args, complete_msgs, any_failed) -> bool:
        try:
            test = ModuleTest(json_data, module, args.image, debug=args.debug, x=args.x)
            test.run()
            test.cleanup(args.remove_images, args.debug)
            msg = f"All tests passed for module: '{module}'"
            test.log_success(msg)
            complete_msgs.append((msg, True, utils._timestamp()))
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

    try:
        any_failed = False
        for t in os.listdir(tests):
            module = os.path.basename(t).split(".")[0]
            if args.lf:
                if module not in utils.get_failed_tests():
                    continue
            elif args.modules and module not in args.modules:
                continue
            with open(os.path.join(tests, t)) as f:
                json_data = json.load(f)
            any_failed = run_module_test(
                module, json_data, args, complete_msgs, any_failed
            )
        log_complete_msgs(complete_msgs)
    except KeyboardInterrupt as e:
        ModuleTest.log_failure("Test run interrupted by user (Ctrl+C)", e)
        if complete_msgs:
            log_complete_msgs(complete_msgs, e)
        sys.exit(130)


if __name__ == "__main__":
    main()
