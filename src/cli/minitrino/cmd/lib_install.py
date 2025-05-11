#!/usr/bin/env python3

import os
import click
import shutil

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError


@click.command(
    "lib-install",
    help="Install the Minitrino library.",
)
@click.option(
    "-v",
    "--version",
    default="",
    type=str,
    help="Library version.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext, version: str) -> None:
    """
    Installs the Minitrino library from a tagged GitHub release.

    If a library directory already exists, prompts the user for permission
    before overwriting it. The version defaults to the current CLI version if
    not explicitly specified.

    Parameters
    ----------
    `version` : `str`
        The library version to install. If empty, defaults to the CLI version.

    Returns
    -------
    `None`
    """

    if not version:
        version = utils.cli_ver()

    lib_dir = os.path.join(ctx.minitrino_user_dir, "lib")
    if os.path.isdir(lib_dir):
        response = ctx.logger.prompt_msg(
            f"The Minitrino library at {lib_dir} will be overwritten. "
            f"Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            ctx.logger.verbose("Removing existing library directory...")
            shutil.rmtree(lib_dir)
        else:
            ctx.logger.info("Opted to skip library installation.")
            return

    download_and_extract(version)
    ctx.logger.info("Library installation complete.")


@utils.pass_environment()
def download_and_extract(ctx: MinitrinoContext, version: str = "") -> None:
    """
    Downloads and extracts the Minitrino library from GitHub.

    Downloads the release tarball for the given version, unpacks it, and moves
    the `lib/` directory to the user's Minitrino directory. If the library fails
    to install, raises a `MinitrinoError`.

    Parameters
    ----------
    `version` : `str`, optional
        The version to download. Defaults to an empty string.
    """

    github_uri = (
        f"https://github.com/jefflester/minitrino/archive/refs/tags/{version}.tar.gz"
    )
    tarball = os.path.join(ctx.minitrino_user_dir, f"{version}.tar.gz")
    file_basename = f"minitrino-{version}"  # filename after unpacking
    lib_dir = os.path.join(ctx.minitrino_user_dir, file_basename, "src", "lib")

    try:
        # Download the release tarball
        cmd = f"curl -fsSL {github_uri} > {tarball}"
        ctx.cmd_executor.execute(cmd)
        if not os.path.isfile(tarball):
            raise MinitrinoError(
                f"Failed to download Minitrino library ({tarball} not found)."
            )

        # Unpack tarball and copy lib
        ctx.logger.verbose(
            f"Unpacking tarball at {tarball} and copying library...",
        )
        ctx.cmd_executor.execute(
            f"tar -xzvf {tarball} -C {ctx.minitrino_user_dir}",
        )
        shutil.move(lib_dir, os.path.join(ctx.minitrino_user_dir, "lib"))

        # Check that the library is present
        lib_dir = os.path.join(ctx.minitrino_user_dir, "lib")
        if not os.path.isdir(lib_dir):
            raise MinitrinoError(f"Library failed to install (not found at {lib_dir})")

        # Cleanup
        cleanup(tarball, file_basename)

    except Exception as e:
        cleanup(tarball, file_basename, False)
        raise MinitrinoError(str(e))


@utils.pass_environment()
def cleanup(
    ctx: MinitrinoContext,
    tarball: str = "",
    file_basename: str = "",
    trigger_error: bool = True,
) -> None:
    """
    Removes the downloaded tarball and extracted files from the user's
    directory.

    Parameters
    ----------
    `tarball` : `str`, optional
        Path to the downloaded tarball.
    `file_basename` : `str`, optional
        Base name of the unpacked directory to remove.
    `trigger_error` : `bool`, optional
        If True, triggers command errors on failure. Default is True.
    """

    ctx.cmd_executor.execute(
        f"rm -rf {tarball} {os.path.join(ctx.minitrino_user_dir, file_basename)}",
        trigger_error=trigger_error,
    )
