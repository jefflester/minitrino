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

    log_level = logging.DEBUG if args.debug else logging.INFO
    common.logger = common.get_logger(log_level)

    common.start_docker_daemon()
    ModuleTest.cleanup()

    tests = os.path.join(HERE, "json")
    complete_msgs: list[tuple[str, bool, str]] = []  # (message, success, timestamp)

    def run_module_test(module, json_data, args, complete_msgs, any_failed) -> bool:
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

    try:
        any_failed = False
        all_json_files = [f for f in os.listdir(tests) if f.endswith(".json")]
        all_modules = sorted([os.path.splitext(f)[0] for f in all_json_files])

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

        failed_this_run: list[str] = []
        for module in modules_to_run:
            json_file = os.path.join(tests, f"{module}.json")
            if not os.path.isfile(json_file):
                continue
            with open(json_file) as f:
                json_data = json.load(f)
            prev_failed = any_failed
            any_failed = run_module_test(
                module, json_data, args, complete_msgs, any_failed
            )
            if any_failed and not prev_failed:
                failed_this_run.clear()  # -x: only record the first failure
            if any_failed:
                failed_this_run.append(module)
                if args.x:
                    common.logger.debug("Recording failed module and exiting")
                    utils.record_failed_test(module, first=True)
                    log_complete_msgs(complete_msgs)
        if failed_this_run and not args.x:
            common.logger.debug("Recording failed modules")
            with open(os.path.join(common.MINITRINO_USER_DIR, ".lastfailed"), "w") as f:
                for m in failed_this_run:
                    f.write(f"{m}\n")
        log_complete_msgs(complete_msgs)
    except KeyboardInterrupt as e:
        ModuleTest.log_failure("Test run interrupted by user (Ctrl+C)", e)
        if complete_msgs:
            log_complete_msgs(complete_msgs, e)
        sys.exit(130)


if __name__ == "__main__":
    main()
