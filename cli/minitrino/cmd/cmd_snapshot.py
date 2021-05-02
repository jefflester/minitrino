#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
import stat
import shutil
import tarfile
import fileinput

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino import errors as err
from minitrino.settings import SNAPSHOT_ROOT_FILES
from minitrino.settings import PROVISION_SNAPSHOT_TEMPLATE
from minitrino.settings import LIB
from minitrino.settings import MODULE_ROOT
from minitrino.settings import MODULE_CATALOG
from minitrino.settings import MODULE_SECURITY
from minitrino.settings import MODULE_RESOURCES
from minitrino.settings import SCRUB_KEYS


@click.command(
    "snapshot",
    help=(
        """Create a snapshot of a Minitrino environment. A tarball is placed in
        the Minitrino `lib/snapshots/` directory.

        To take a snapshot of an active environment, leave the `--module` and
        option out of the command. 

        To take a snapshot of modules whether they are active or not, specify
        the modules via the `--module` option."""
    ),
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help=("""A specific module to snapshot."""),
)
@click.option(
    "-n",
    "--name",
    required=True,
    type=str,
    help=(
        """Basename of the resulting snapshot tarball file. Allowed characters:
        alphanumerics, hyphens, and underscores."""
    ),
)
@click.option(
    "-d",
    "--directory",
    type=click.Path(),
    help=(
        """Directory to save the resulting snapshot file in. Defaults to the
        snapshots directory in the Minitrino library."""
    ),
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help=("""Overwrite the file if it already exists."""),
)
@click.option(
    "--no-scrub",
    is_flag=True,
    default=False,
    help=(
        """Do not scrub sensitive data from user config file.

        WARNING: all sensitive information (passwords and keys) will be kept in
        the user config file added to the snapshot. Only use this if you are
        prepared to share those secrets with another person."""
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx, modules, name, directory, force, no_scrub):
    """Snapshot command for Minitrino."""

    # The snapshot temp files are saved in ~/.minitrino/snapshots/<name>
    # regardless of the directory provided. The artifact (tarball) will go
    # to either the default directory or the user-provided directory.

    utils.check_lib(ctx)

    if directory and not os.path.isdir(directory):
        raise err.UserError(
            f"Cannot save snapshot in nonexistent directory: {directory}",
            "Pick any directory that exists, and this will work.",
        )

    if not directory:
        directory = os.path.join(ctx.minitrino_lib_dir, "snapshots")

    validate_name(name)
    check_exists(name, directory, force)

    if modules:
        ctx.logger.log(f"Creating snapshot of specified modules...")
        snapshot_runner(name, no_scrub, False, modules, directory)
    else:
        modules = ctx.modules.get_running_modules()
        if not modules:
            ctx.logger.log(
                f"No running Minitrino modules to snapshot. Snapshotting "
                f"Trino resources only.",
                level=ctx.logger.verbose,
            )
        else:
            ctx.logger.log(f"Creating snapshot of active environment...")
        snapshot_runner(name, no_scrub, True, list(modules.keys()), directory)

    check_complete(name, directory)
    ctx.logger.log(
        f"Snapshot complete and saved at path: {os.path.join(directory, name)}.tar.gz"
    )


@pass_environment
def validate_name(ctx, name):
    """Validates the chosen filename for correct input."""

    for char in name:
        if all((char != "_", char != "-", not char.isalnum())):
            raise err.UserError(
                f"Illegal character found in provided filename: '{char}'. ",
                f"Alphanumeric, hyphens, and underscores are allowed. "
                f"Rename and retry.",
            )


@pass_environment
def check_exists(ctx, name, directory, force):
    """Checks if the resulting tarball exists. If it exists, the user is
    prompted to overwrite the existing file."""

    if force:
        return

    snapshot_file = os.path.abspath(os.path.join(directory, f"{name}.tar.gz"))
    if os.path.isfile(snapshot_file):
        response = ctx.logger.prompt_msg(
            f"Snapshot file {name}.tar.gz already exists. Overwrite? [Y/N]"
        )
        if not utils.validate_yes(response):
            ctx.logger.log(f"Opted to skip snapshot.")
            sys.exit(0)


@pass_environment
def prepare_snapshot_dir(ctx, name, active, no_scrub, modules):
    """Checks if the snapshot temp directory exists. If it does, clears
    files/directories inside of it. If it doesn't, (1) creates it and clones the
    library structure, (2) adds a Bash file that can be executed to spin up the
    environment as it was snapshotted.

    Returns the absolute path of the named snapshot directory."""

    if os.path.isdir(ctx.snapshot_dir):
        ctx.logger.log(
            "Snapshot temp directory exists. Removing and recreating...",
            level=ctx.logger.verbose,
        )
        shutil.rmtree(ctx.snapshot_dir)
        os.mkdir(ctx.snapshot_dir)
    else:
        ctx.logger.log(
            "Snapshot directory does not exist. Creating...", level=ctx.logger.verbose
        )
        os.mkdir(ctx.snapshot_dir)

    snapshot_name_dir = clone_lib_dir(name)
    handle_copy_config_file(snapshot_name_dir, no_scrub)
    build_snapshot_command(snapshot_name_dir, modules, active)

    return snapshot_name_dir


@pass_environment
def build_snapshot_command(ctx, snapshot_name_dir, modules=[], active=True):
    """Builds a basic shell command that can be used to provision an environment
    with the minitrino CLI. Used for snapshot purposes."""

    command_string = build_command_string(modules)
    create_snapshot_command_file(command_string, snapshot_name_dir)


@pass_environment
def build_command_string(ctx, modules=[]):
    """Builds a command string that can be used to create an environment with
    the designated modules."""

    option_string = ""

    if modules:
        options = ""
        for module in modules:
            options += f" {module}"
        option_string = f"--module {options}"

    bash_source = '"${BASH_SOURCE%/*}"'
    command_string = (
        f"minitrino -v --env LIB_PATH={bash_source}/lib provision {option_string}\n\n"
    )

    return command_string.replace("  ", " ")


@pass_environment
def create_snapshot_command_file(ctx, command_string="", snapshot_name_dir=""):
    """Creates an .sh file in the minitrino directory for usage by the snapshot
    command. This way, a similar command used to provision the environment is
    preserved."""

    file_dest = os.path.join(snapshot_name_dir, "provision-snapshot.sh")
    ctx.logger.log(
        f"Creating snapshot command to file at path: {file_dest}",
        level=ctx.logger.verbose,
    )

    # Create provisioning command snapshot file from template and make it
    # executable
    try:
        with open(file_dest, "w") as provision_command_file:
            provision_command_file.write(PROVISION_SNAPSHOT_TEMPLATE.lstrip())
        st = os.stat(file_dest)
        os.chmod(
            file_dest,
            st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )
    except Exception as e:
        utils.handle_exception(e, ctx.verbose)

    with open(file_dest, "a") as provision_snapshot_file:
        provision_snapshot_file.write(command_string)


@pass_environment
def clone_lib_dir(ctx, name):
    """Clones the library directory structure and necessary top-level files in
    preparation for copying over module directories.

    Returns the absolute path of the named snapshot directory."""

    snapshot_name_dir = os.path.join(ctx.snapshot_dir, name)
    os.makedirs(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_CATALOG))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_SECURITY))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES))

    # Copy root lib files to snapshot
    for filename in os.listdir(ctx.minitrino_lib_dir):
        if filename in SNAPSHOT_ROOT_FILES:
            file_path = os.path.join(ctx.minitrino_lib_dir, filename)
            shutil.copy(file_path, os.path.join(snapshot_name_dir, LIB))

    # Copy everything from lib/modules/resources
    resources_dir = os.path.join(ctx.minitrino_lib_dir, MODULE_ROOT, MODULE_RESOURCES)
    for filename in os.listdir(resources_dir):
        file_path = os.path.join(resources_dir, filename)
        shutil.copy(
            file_path,
            os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES),
        )

    return snapshot_name_dir


@pass_environment
def handle_copy_config_file(ctx, snapshot_name_dir, no_scrub):
    """Handles the copying of the user config file to the named snapshot
    directory. Calls `scrub_config_file()` if `no_scrub` is True."""

    if no_scrub:
        response = ctx.logger.prompt_msg(
            f"All sensitive information in user config will be added to the snapshot. Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            copy_config_file(snapshot_name_dir, no_scrub)
        else:
            ctx.logger.log(f"Opted to scrub sensitive user config data.")
            copy_config_file(snapshot_name_dir)
    else:
        copy_config_file(snapshot_name_dir)


@pass_environment
def copy_config_file(ctx, snapshot_name_dir, no_scrub=False):
    """Copies user config file to the named snapshot directory."""

    if os.path.isfile(ctx.config_file):
        shutil.copy(ctx.config_file, snapshot_name_dir)
    else:
        ctx.logger.log(
            f"No user config file at path: {ctx.config_file}. Will not be added to snapshot.",
            level=ctx.logger.warn,
        )
        return

    if not no_scrub:
        scrub_config_file(snapshot_name_dir)


@pass_environment
def scrub_config_file(ctx, snapshot_name_dir):
    """Scrubs the user config file of sensitive data."""

    snapshot_config_file = os.path.join(snapshot_name_dir, "minitrino.cfg")
    if os.path.isfile(snapshot_config_file):
        for line in fileinput.input(snapshot_config_file, inplace=True):
            if "=" in line:
                print(line.replace(line, scrub_line(line)))
            else:
                print(line.replace(line, line.rstrip()))
    else:
        ctx.logger.log(
            f"No user config file at path: {ctx.config_file}. Nothing to scrub.",
            level=ctx.logger.warn,
        )


@pass_environment
def scrub_line(ctx, line):
    """Scrubs a line from a snapshot config file. Returns the scrubbed line."""

    # If the key has a substring that matches any of the scrub keys, we know
    # it's an item whose value needs to be scrubbed
    line = utils.parse_key_value_pair(line, err_type=err.UserError)
    if any(item in line[0].lower() for item in SCRUB_KEYS):
        line[1] = "*" * 20

    return "=".join(line)


@pass_environment
def copy_module_dirs(ctx, snapshot_name_dir, modules=[]):
    """Copies module directories into the named snapshot directory."""

    for module in modules:
        module_dir = ctx.modules.data.get(module, "").get("module_dir", "")
        module_type = ctx.modules.data.get(module, "").get("type", "")
        dest_dir = os.path.join(
            os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, module_type),
            os.path.basename(module_dir),
        )
        shutil.copytree(module_dir, dest_dir)


@pass_environment
def create_named_tarball(ctx, name, snapshot_name_dir, save_dir):
    """Creates a tarball of the named snapshot directory and placed in the
    library's snapshot directory."""

    with tarfile.open(os.path.join(save_dir, f"{name}.tar.gz"), "w:gz") as tar:
        tar.add(snapshot_name_dir, arcname=os.path.basename(snapshot_name_dir))


def snapshot_runner(name, no_scrub, active, modules=[], directory=""):
    """Executes sequential snapshot command functions."""

    snapshot_name_dir = prepare_snapshot_dir(name, active, no_scrub, modules)
    copy_module_dirs(snapshot_name_dir, modules)
    create_named_tarball(name, snapshot_name_dir, directory)


@pass_environment
def check_complete(ctx, name, directory):
    """Checks if the snapshot completed. If detected as incomplete, exists with
    a non-zero status code."""

    snapshot_file = os.path.join(directory, f"{name}.tar.gz")
    if not os.path.isfile(snapshot_file):
        raise err.MinitrinoError(f"Snapshot tarball failed to write to {snapshot_file}")
