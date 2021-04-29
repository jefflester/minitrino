#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
import shutil

from minipresto.cli import pass_environment
from minipresto import errors as err
from minipresto import utils


@click.command(
    "lib_install",
    help=("""Install the Minipresto library."""),
)
@click.option(
    "-v",
    "--version",
    default="",
    type=str,
    help=("""The version of the library to install."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx, version):
    """Library installation command for Minipresto."""

    if not version:
        version = utils.get_cli_ver()

    lib_dir = os.path.join(ctx.minipresto_user_dir, "lib")
    if os.path.isdir(lib_dir):
        response = ctx.logger.prompt_msg(
            f"The Minipresto library at {lib_dir} will be overwritten. "
            f"Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            ctx.logger.log(
                "Removing existing library directory...", level=ctx.logger.verbose
            )
            shutil.rmtree(lib_dir)
        else:
            ctx.logger.log("Opted to skip library installation.")
            sys.exit(0)

    download_and_extract(version)
    ctx.logger.log("Library installation complete.")


@pass_environment
def download_and_extract(ctx, version=""):

    github_uri = f"https://github.com/jefflester/minipresto/archive/{version}.tar.gz"
    tarball = os.path.join(ctx.minipresto_user_dir, f"{version}.tar.gz")
    file_basename = f"minitrino-{version}"  # filename after unpacking
    lib_dir = os.path.join(ctx.minipresto_user_dir, file_basename, "lib")

    try:
        # Download the release tarball
        cmd = f"curl -fsSL {github_uri} > {tarball}"
        ctx.cmd_executor.execute_commands(cmd)
        if not os.path.isfile(tarball):
            raise err.MiniprestoError(
                f"Failed to download Minipresto library ({tarball} not found)."
            )

        # Unpack tarball and copy lib
        ctx.logger.log(
            f"Unpacking tarball at {tarball} and copying library...",
            level=ctx.logger.verbose,
        )
        ctx.cmd_executor.execute_commands(
            f"tar -xzvf {tarball} -C {ctx.minipresto_user_dir}",
            f"mv {lib_dir} {ctx.minipresto_user_dir}",
        )

        # Check that the library is present
        lib_dir = os.path.join(ctx.minipresto_user_dir, "lib")
        if not os.path.isdir(lib_dir):
            raise err.MiniprestoError(
                f"Library failed to install (not found at {lib_dir})"
            )

        # Cleanup
        cleanup(tarball, file_basename)

    except Exception as e:
        cleanup(tarball, file_basename, False)
        raise err.MiniprestoError(str(e))


@pass_environment
def cleanup(ctx, tarball="", file_basename="", trigger_error=True):

    ctx.cmd_executor.execute_commands(
        f"rm -rf {tarball} {os.path.join(ctx.minipresto_user_dir, file_basename)}",
        trigger_error=trigger_error,
    )
