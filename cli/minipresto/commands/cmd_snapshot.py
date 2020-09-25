#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
import stat
import shutil
import tarfile
import traceback
import fileinput

from minipresto.cli import pass_environment
from minipresto.exceptions import MiniprestoException
from minipresto.core import Modules
from minipresto.core import check_daemon
from minipresto.core import handle_exception
from minipresto.core import handle_generic_exception
from minipresto.core import validate_yes_response
from minipresto.core import validate_module_dirs

from minipresto.settings import SNAPSHOT_ROOT_FILES
from minipresto.settings import PROVISION_SNAPSHOT_TEMPLATE
from minipresto.settings import LIB
from minipresto.settings import MODULE_ROOT
from minipresto.settings import MODULE_CATALOG
from minipresto.settings import MODULE_SECURITY
from minipresto.settings import MODULE_RESOURCES
from minipresto.settings import SCRUB_KEYS


@click.command("snapshot", help="""
Creates a snapshot of a minipresto environment. Places a tarball in the
Minipresto `lib/snapshots/` directory.

To take a snapshot of an active environment, leave the `--catalog` and
`--security` options out of the command. 

To take a snapshot of modules, whether they are active or not, specify the
modules via the `--catalog` and `--security` options.
""")
@click.option("-c", "--catalog", default=[], type=str, multiple=True, help="""
Catalog modules to include in the snapshot. 
""")
@click.option("-s", "--security", default=[], type=str, multiple=True, help="""
Security modules to include in the snapshot. 
""")
@click.option("-n", "--name", required=True, type=str, help="""
Basename of the resulting snapshot tarball file. Allowed characters:
alphanumerics, hyphens, and underscores.
""")
@click.option("-f", "--force", is_flag=True, default=False, help="""
Skips checking if the resulting tarball file exists (and overrides the file if
it does exist).
""")
@click.option("--no-scrub", is_flag=True, default=False, help="""
Prevents the scrubbing of sensitive data from user config.

WARNING: all sensitive information (passwords and keys) will be kept in the
config file added to the snapshot. Only use this if you are prepared to share
those secrets with another person.
""")


@pass_environment
def cli(ctx, catalog, security, name, force, no_scrub):
    """Snapshot command for minipresto."""

    try:
        validate_name(name)
        check_exists(name, force)

        if catalog or security:
            ctx.log(f"Creating snapshot of inactive environment...")
            snapshot_runner(name, no_scrub, False, catalog, security)
        else:
            ctx.log(f"Creating snapshot of active environment...")
            modules = Modules(ctx)
            snapshot_runner(name, no_scrub, True, modules.catalog, modules.security)

        check_complete(name)
        ctx.log(f"Snapshot complete.")

    except MiniprestoException as e:
        handle_exception(e)

    except Exception as e:
        handle_generic_exception(e)


@pass_environment
def prepare_snapshot_dir(ctx, name, active, no_scrub, catalog=[], security=[]):
    """
    Checks if the snapshot directory exists. If it does, clears
    files/directories inside of it. If it doesn't, creates it and clones the
    required project structure. Copies the provisioning command snapshot file
    for actively environment snapshots.

    Returns the absolute path of the named snapshot directory.
    """

    if os.path.isdir(ctx.snapshot_dir):
        ctx.vlog(f"Snapshot directory exists. Removing and recreating...")
        shutil.rmtree(ctx.snapshot_dir)
        os.mkdir(ctx.snapshot_dir)
    else:
        ctx.vlog(f"Snapshot directory does not exist. Creating...")
        os.mkdir(ctx.snapshot_dir)

    snapshot_name_dir = clone_lib_dir(name)
    handle_copy_config_file(snapshot_name_dir, no_scrub)

    prepare_snapshot_command_file(snapshot_name_dir, active, catalog, security)

    return snapshot_name_dir


@pass_environment
def prepare_snapshot_command_file(
    ctx, snapshot_name_dir, active, catalog=[], security=[]
):
    """Prepares the snapshot command file."""

    build_snapshot_command(snapshot_name_dir, catalog, security, active)


@pass_environment
def build_snapshot_command(
    ctx, snapshot_name_dir, catalog=[], security=[], active=True
):
    """
    Builds a basic shell command that can be used to provision an environment
    with the minipresto CLI. Used for snapshot purposes.
    """

    if active:
        modules = Modules(ctx)
        if not modules.containers:
            raise MiniprestoException(
                f"No running Minipresto containers. To create a snapshot of an inactive environment, "
                f"you must specify the catalog and security modules. Run --help for more information."
            )
        command_string = build_command_string(catalog, security)
    else:
        command_string = build_command_string(catalog, security)

    create_snapshot_command_file(command_string, snapshot_name_dir)


@pass_environment
def build_command_string(ctx, catalog=[], security=[]):
    """
    Builds a command string that can be used to create an environment with the
    designated modules.
    """

    option_string = ""

    if catalog:
        options = ""
        for item in catalog:
            options += f" {item}"
        option_string = f"--catalog {options}"
    if security:
        options = ""
        for item in security:
            options += f" {item}"
        option_string = f"{option_string} --security {options}"

    bash_source = '"${BASH_SOURCE%/*}"'
    command_string = (
        f"minipresto -v --lib-path {bash_source}/lib provision {option_string}\n\n"
    )

    return command_string.replace("  ", " ")


@pass_environment
def create_snapshot_command_file(ctx, command_string="", snapshot_name_dir=""):
    """
    Creates an .sh file in the minipresto directory for usage by the snapshot
    command. This way, a similar command used to provision the environment is
    preserved.
    """

    file_dest = os.path.join(snapshot_name_dir, "provision-snapshot.sh")
    ctx.vlog(f"Writing snapshot command to file at path: {file_dest}")

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
        handle_generic_exception(e)

    with open(file_dest, "a") as provision_snapshot_file:
        provision_snapshot_file.write(command_string)


@pass_environment
def clone_lib_dir(ctx, name):
    """
    Clones the library directory structure and necessary top-level files in
    preparation for copying over module directories.

    Returns the absolute path of the named snapshot directory.
    """

    snapshot_name_dir = os.path.join(ctx.snapshot_dir, name)
    os.makedirs(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_CATALOG))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_SECURITY))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES))

    # Copy root files
    for filename in os.listdir(ctx.minipresto_lib_dir):
        if filename in SNAPSHOT_ROOT_FILES:
            file_path = os.path.join(ctx.minipresto_lib_dir, filename)
            shutil.copy(file_path, os.path.join(snapshot_name_dir, LIB))

    # Copy everything from module resources
    resources_dir = os.path.join(ctx.minipresto_lib_dir, MODULE_ROOT, MODULE_RESOURCES)
    for filename in os.listdir(resources_dir):
        file_path = os.path.join(resources_dir, filename)
        shutil.copy(
            file_path,
            os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES),
        )

    return snapshot_name_dir


@pass_environment
def handle_copy_config_file(ctx, snapshot_name_dir, no_scrub):
    """
    Handles the copying of the user config file to the named snapshot directory.
    Calls `scrub_config_file()` if `no_scrub` is True.
    """

    if no_scrub:
        response = ctx.prompt_msg(
            f"All sensitive information in user config will be added to the snapshot. Continue? [Y/N]"
        )
        if validate_yes_response(response):
            copy_config_file(snapshot_name_dir, no_scrub)
        else:
            ctx.log(f"Opted to scrub sensitive user config data.")
            copy_config_file(snapshot_name_dir)
    else:
        copy_config_file(snapshot_name_dir)


@pass_environment
def copy_config_file(ctx, snapshot_name_dir, no_scrub=False):
    """Copies user config file to the named snapshot directory."""

    if os.path.isfile(ctx.config_file):
        shutil.copy(ctx.config_file, snapshot_name_dir)
    else:
        ctx.log_warn(
            f"No user config file at path: {ctx.config_file}. Will not be added to snapshot."
        )
        return

    if not no_scrub:
        scrub_config_file(snapshot_name_dir)


@pass_environment
def scrub_config_file(ctx, snapshot_name_dir):
    """Scrubs the user config file of sensitive data."""

    snapshot_config_file = os.path.join(snapshot_name_dir, "minipresto.cfg")
    if os.path.isfile(snapshot_config_file):
        for line in fileinput.input(snapshot_config_file, inplace=True):
            if "=" in line:
                print(line.replace(line, scrub_line(line)))
            else:
                print(line.replace(line, line.rstrip()))
    else:
        ctx.log_warn(
            f"No user config file at path: {ctx.config_file}. Nothing to scrub."
        )


@pass_environment
def scrub_line(ctx, line):
    """
    Scrubs a line from a snapshot config file. Returns the scrubbed line.
    """

    line = line.strip().split("=")
    if not len(line) == 2:
        raise MiniprestoException(
            f"Invalid line in snapshot configuration file: '{''.join(line)}'. "
            f"Should be formatted as KEY=VALUE."
        )

    # If the key has a substring that matches any of the scrub keys, we know
    # it's an item whose value needs to be scrubbed
    if any(item in line[0].lower() for item in SCRUB_KEYS):
        line[1] = "*" * 20

    return "=".join(line)


def copy_module_dirs(snapshot_name_dir, catalog_dirs=[], security_dirs=[]):
    """Copies module directories into the named snapshot directory."""

    if catalog_dirs:
        for catalog_dir in catalog_dirs:
            dest_dir = os.path.join(
                os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_CATALOG),
                os.path.basename(catalog_dir),
            )
            shutil.copytree(catalog_dir, dest_dir)
    if security_dirs:
        for security_dir in security_dirs:
            dest_dir = os.path.join(
                os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_SECURITY),
                os.path.basename(security_dir),
            )
            shutil.copytree(security_dir, dest_dir)


@pass_environment
def create_named_tarball(ctx, name, snapshot_name_dir):
    """
    Creates a tarball of the named snapshot directory and placed in the
    library's snapshot directory.
    """

    snapshot_dir = os.path.join(ctx.minipresto_lib_dir, "snapshots")
    with tarfile.open(os.path.join(snapshot_dir, f"{name}.tar.gz"), "w:gz") as tar:
        tar.add(snapshot_name_dir, arcname=os.path.basename(snapshot_name_dir))


def snapshot_runner(name, no_scrub, active, catalog=[], security=[]):
    """Executes sequential snapshot command functions."""

    catalog_dirs, _ = validate_module_dirs(MODULE_CATALOG, catalog)
    security_dirs, _ = validate_module_dirs(MODULE_SECURITY, security)
    snapshot_name_dir = prepare_snapshot_dir(name, active, no_scrub, catalog, security)
    copy_module_dirs(snapshot_name_dir, catalog_dirs, security_dirs)
    create_named_tarball(name, snapshot_name_dir)


@pass_environment
def validate_name(ctx, name=""):
    """
    Validates the chosen filename for correct input.
    """

    for char in name:
        if all((char != "_", char != "-", not char.isalnum())):
            raise MiniprestoException(
                f"Illegal character found in provided filename: '{char}'. "
                f"Alphanumeric, hyphens, and underscores are allowed. "
                f"Rename and retry."
            )


@pass_environment
def check_exists(ctx, name, force):
    """
    Checks if the resulting tarball exists. If it exists, the user is prompted
    to overwrite the existing file.
    """

    if force:
        return

    snapshot_file = os.path.abspath(
        os.path.join(ctx.minipresto_lib_dir, "snapshots", f"{name}.tar.gz")
    )
    if os.path.isfile(snapshot_file):
        response = ctx.prompt_msg(
            f"Snapshot file {name}.tar.gz already exists. Overwrite? [Y/N]"
        )
        if validate_yes_response(response):
            pass
        else:
            ctx.log(f"Opted to skip snapshot.")
            sys.exit(0)
    else:
        pass


@pass_environment
def check_complete(ctx, name):
    """
    Checks if the snapshot completed. If detected as incomplete, exists with a
    non-zero status code.
    """

    snapshot_file = os.path.join(ctx.minipresto_lib_dir, "snapshots", f"{name}.tar.gz")
    if not os.path.isfile(snapshot_file):
        raise MiniprestoException(
            f"Snapshot tarball failed to write to {snapshot_file}"
        )
