"""Snapshot command for Minitrino CLI.

Provides functionality to create, validate, and manage snapshots of Minitrino
environments, including modules and configuration files.
"""

import os
import click
import stat
import shutil
import tarfile
import fileinput

from typing import Optional

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError

from minitrino.settings import (
    LIB,
    SCRUB_KEYS,
    MODULE_ROOT,
    MODULE_ADMIN,
    MODULE_CATALOG,
    MODULE_SECURITY,
    MODULE_RESOURCES,
    SNAPSHOT_ROOT_FILES,
    PROVISION_SNAPSHOT_TEMPLATE,
)


@click.command(
    "snapshot",
    help=(
        """Create a snapshot of a Minitrino environment. By default, applies to
        'default' cluster.
        
        Once a snapshot is created, a tarball is placed in the Minitrino
        `lib/snapshots/` directory - usually `~/.minitrino/lib/snapshots/`.

        To snapshot an active environment, do not pass in the `--module` option.

        To snapshot modules whether they are active or not, specify target modules via
        the `--module` option.
        
        To snapshot a specific running cluster, use the `CLUSTER_NAME` environment
        variable or the `--cluster` / `-c` option, e.g.: 
        
        `minitrino -c my-cluster snapshot`, or specify all clusters via:\n `minitrino -c
        '*' snapshot`"""
    ),
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help="Specific module to snapshot.",
)
@click.option(
    "-n",
    "--name",
    required=True,
    type=str,
    help="Basename of the snapshot tarball.",
)
@click.option(
    "-d",
    "--directory",
    type=click.Path(),
    help="Directory to save the snapshot file in.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the snapshot file if it already exists.",
)
@click.option(
    "--no-scrub",
    is_flag=True,
    default=False,
    help="Do not scrub sensitive data from user config file.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    modules: list[str],
    name: str,
    directory: str,
    force: bool,
    no_scrub: bool,
) -> None:
    """Run the main entrypoint for the `snapshot` command in Minitrino.

    Parameters
    ----------
    modules : list of str
        Modules to snapshot. If empty, snapshots active environment.
    name : str
        Basename for the resulting snapshot tarball.
    directory : str
        Directory to save the snapshot file in.
    force : bool
        If True, overwrite the file if it already exists.
    no_scrub : bool
        If True, do not scrub sensitive data from user config file.
    """
    # The snapshot temp files are saved in ~/.minitrino/snapshots/<name> regardless of
    # the directory provided. The artifact (tarball) will go to either the default
    # directory or the user-provided directory.

    utils.check_lib(ctx)

    if directory and not os.path.isdir(directory):
        raise UserError(
            f"Cannot save snapshot in nonexistent directory: {directory}",
            "Pick any directory that exists, and this will work.",
        )

    if not directory:
        directory = os.path.join(ctx.lib_dir, "snapshots")

    validate_name(name)
    check_exists(name, directory, force)

    if modules:
        ctx.logger.info(f"Creating snapshot of specified modules...")
        modules = ctx.modules.check_dep_modules(modules)
        snapshot_runner(name, no_scrub, False, modules, directory)
    else:
        running = ctx.modules.running_modules()
        if not running:
            ctx.logger.verbose(
                f"No running Minitrino modules to snapshot. Snapshotting "
                f"root resources only.",
            )
            modules = []
        else:
            ctx.logger.info(f"Creating snapshot of active environment...")
            modules = ctx.modules.check_dep_modules(list(running.keys()))
        snapshot_runner(name, no_scrub, True, modules, directory)

    check_complete(name, directory)
    ctx.logger.info(
        f"Snapshot complete and saved at path: {os.path.join(directory, name)}.tar.gz"
    )


def validate_name(name: str) -> None:
    """Validate the chosen filename for correct input.

    Parameters
    ----------
    name : str
        The filename to validate.

    Raises
    ------
    UserError
        If the filename contains illegal characters.
    """
    for char in name:
        if all((char != "_", char != "-", not char.isalnum())):
            raise UserError(
                f"Illegal character found in provided filename: '{char}'. ",
                f"Alphanumeric, hyphens, and underscores are allowed. "
                f"Rename and retry.",
            )


@utils.pass_environment()
def check_exists(ctx: MinitrinoContext, name: str, directory: str, force: bool) -> None:
    """Check if the resulting tarball exists.

    If it exists, prompt the user to overwrite.

    Parameters
    ----------
    name : str
        Name of the snapshot file.
    directory : str
        Directory containing the snapshot file.
    force : bool
        If True, overwrite without prompting.
    """
    if force:
        return

    snapshot_file = os.path.abspath(os.path.join(directory, f"{name}.tar.gz"))
    if os.path.isfile(snapshot_file):
        response = ctx.logger.prompt_msg(
            f"Snapshot file {name}.tar.gz already exists. Overwrite? [Y/N]"
        )
        if not utils.validate_yes(response):
            ctx.logger.info(f"Opted to skip snapshot.")
            return


@utils.pass_environment()
def prepare_snapshot_dir(
    ctx: MinitrinoContext, name: str, no_scrub: bool, modules: list[str]
) -> str:
    """Prepare the snapshot temporary directory.

    If the directory exists, clear it. Otherwise, create it and clone the library
    structure, along with a shell script to provision the environment.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    no_scrub : bool
        If True, do not scrub sensitive data from config.
    modules : list of str
        List of modules to include in the snapshot.

    Returns
    -------
    str
        Absolute path of the named snapshot directory.
    """
    if os.path.isdir(ctx.snapshot_dir):
        ctx.logger.verbose(
            "Snapshot temp directory exists. Removing and recreating...",
        )
        shutil.rmtree(ctx.snapshot_dir)
        os.mkdir(ctx.snapshot_dir)
    else:
        ctx.logger.verbose("Snapshot directory does not exist. Creating...")
        os.mkdir(ctx.snapshot_dir)

    snapshot_name_dir = clone_lib_dir(name)
    handle_copy_config_file(snapshot_name_dir, no_scrub)
    create_snapshot_shell_script(snapshot_name_dir, modules)

    return snapshot_name_dir


def create_snapshot_shell_script(
    snapshot_name_dir: str, modules: Optional[list[str]] = None
) -> None:
    """Write a shell script to the snapshot directory for provisioning the environment.

    Parameters
    ----------
    snapshot_name_dir : str
        Directory where the shell script will be created.
    modules : list of str, optional
        List of modules to include in the command.
    """
    if modules is None:
        modules = []
    command_string = build_command_string(modules)
    write_snapshot_shell_script(command_string, snapshot_name_dir)


def build_command_string(modules: Optional[list[str]] = None) -> str:
    """Build a command string for provisioning an environment with designated modules.

    Parameters
    ----------
    modules : list of str, optional
        List of modules to include in the command.

    Returns
    -------
    str
        The constructed command string.
    """
    modules = modules or []
    option_string = ""
    if modules:
        options = ""
        for module in modules:
            options += f"--module {module} "
        option_string = f"{options}"

    bash_source = '"${BASH_SOURCE%/*}"'
    command_string = (
        f"minitrino -v --env LIB_PATH={bash_source}/lib provision {option_string}\n\n"
    )

    return command_string.replace("  ", " ")


def write_snapshot_shell_script(
    ctx: MinitrinoContext, command_string: str = "", snapshot_name_dir: str = ""
) -> None:
    """Write a shell script to the snapshot directory for provisioning the environment.

    Write a shell script to the snapshot directory for provisioning the environment.

    Parameters
    ----------
    command_string : str, optional
        The command string to write to the file.
    snapshot_name_dir : str, optional
        The directory where the shell file will be created.
    """
    file_dest = os.path.join(snapshot_name_dir, "provision-snapshot.sh")
    ctx.logger.verbose(
        f"Creating snapshot command to file at path: {file_dest}",
    )

    # Create provisioning command snapshot file from template and make it executable
    with open(file_dest, "w") as provision_command_file:
        provision_command_file.write(PROVISION_SNAPSHOT_TEMPLATE.lstrip())
    st = os.stat(file_dest)
    os.chmod(
        file_dest,
        st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    with open(file_dest, "a") as provision_snapshot_file:
        provision_snapshot_file.write(command_string)


@utils.pass_environment()
def clone_lib_dir(ctx: MinitrinoContext, name: str) -> str:
    """Clone the library directory structure and necessary top-level files.

    Clone the library directory structure and necessary top-level files in preparation
    for copying over module directories.

    Parameters
    ----------
    name : str
        Name of the snapshot.

    Returns
    -------
    str
        Absolute path of the named snapshot directory.
    """
    snapshot_name_dir = os.path.join(ctx.snapshot_dir, name)
    os.makedirs(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_ADMIN))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_CATALOG))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_SECURITY))
    os.mkdir(os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES))

    # Copy root lib files to snapshot
    for filename in os.listdir(ctx.lib_dir):
        if filename in SNAPSHOT_ROOT_FILES:
            file_path = os.path.join(ctx.lib_dir, filename)
            if os.path.isfile(file_path):
                shutil.copy(file_path, os.path.join(snapshot_name_dir, LIB))
            elif os.path.isdir(file_path):
                shutil.copytree(
                    file_path, os.path.join(snapshot_name_dir, LIB, filename)
                )

    # Copy everything from lib/modules/resources
    resources_dir = os.path.join(ctx.lib_dir, MODULE_ROOT, MODULE_RESOURCES)
    for filename in os.listdir(resources_dir):
        file_path = os.path.join(resources_dir, filename)
        shutil.copy(
            file_path,
            os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, MODULE_RESOURCES),
        )

    return snapshot_name_dir


@utils.pass_environment()
def handle_copy_config_file(
    ctx: MinitrinoContext, snapshot_name_dir: str, no_scrub: bool
) -> None:
    """Handle copying of the user config file to the snapshot directory.

    If `no_scrub` is True, prompt the user to confirm inclusion of sensitive data. If
    declined, scrub the config file.

    Parameters
    ----------
    snapshot_name_dir : str
        Directory where the config file will be copied.
    no_scrub : bool
        If True, do not scrub sensitive data from config.
    """
    if no_scrub:
        response = ctx.logger.prompt_msg(
            "All sensitive information in user config will be added to the snapshot. Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            copy_config_file(snapshot_name_dir, no_scrub)
        else:
            ctx.logger.info("Opted to scrub sensitive user config data.")
            copy_config_file(snapshot_name_dir)
    else:
        copy_config_file(snapshot_name_dir)


@utils.pass_environment()
def copy_config_file(
    ctx: MinitrinoContext, snapshot_name_dir: str, no_scrub: bool = False
) -> None:
    """Copy the user config file to the named snapshot directory.

    Optionally scrub sensitive data.

    Parameters
    ----------
    snapshot_name_dir : str
        Directory where the config file will be copied.
    no_scrub : bool, optional
        If True, do not scrub sensitive data from config.
    """
    if os.path.isfile(ctx.config_file):
        shutil.copy(ctx.config_file, snapshot_name_dir)
    else:
        ctx.logger.warn(
            f"No user config file at path: {ctx.config_file}. Will not be added to snapshot.",
        )
        return

    if not no_scrub:
        scrub_config_file(snapshot_name_dir)


@utils.pass_environment()
def scrub_config_file(ctx: MinitrinoContext, snapshot_name_dir: str) -> None:
    """Scrub sensitive data from the user config file in the snapshot directory.

    Parameters
    ----------
    snapshot_name_dir : str
        Directory containing the config file to scrub.
    """
    snapshot_config_file = os.path.join(snapshot_name_dir, "minitrino.cfg")
    if os.path.isfile(snapshot_config_file):
        for line in fileinput.input(snapshot_config_file, inplace=True):
            if "=" in line:
                print(line.replace(line, scrub_line(line)))
            else:
                print(line.replace(line, line.rstrip()))
    else:
        ctx.logger.warn(
            f"No user config file at path: {ctx.config_file}. Nothing to scrub.",
        )


def scrub_line(line: str) -> str:
    """Scrub a line from a snapshot config file.

    If the key in the line matches any of the sensitive keys, its value is replaced.

    Parameters
    ----------
    line : str
        The line to scrub.

    Returns
    -------
    str
        The scrubbed line.
    """
    # If the key has a substring that matches any of the scrub keys, we know it's an
    # item whose value needs to be scrubbed
    k, v = utils.parse_key_value_pair(line, err_type=UserError)
    if any(item in k.lower() for item in SCRUB_KEYS):
        v = "*" * 20

    return "=".join([k, v])


@utils.pass_environment()
def copy_module_dirs(
    ctx: MinitrinoContext, snapshot_name_dir: str, modules: Optional[list[str]] = None
) -> None:
    """Copy module directories into the named snapshot directory.

    Parameters
    ----------
    snapshot_name_dir : str
        Directory where modules will be copied.
    modules : list of str, optional
        List of modules to copy.
    """
    if modules is None:
        modules = []
    for module in modules:
        module_dir = ctx.modules.data.get(module, {}).get("module_dir", "")
        module_type = ctx.modules.data.get(module, {}).get("type", "")
        dest_dir = os.path.join(
            os.path.join(snapshot_name_dir, LIB, MODULE_ROOT, module_type),
            os.path.basename(module_dir),
        )
        shutil.copytree(module_dir, dest_dir)


def create_named_tarball(name: str, snapshot_name_dir: str, save_dir: str) -> None:
    """Create a snapshot tarball.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    snapshot_name_dir : str
        Directory to archive.
    save_dir : str
        Directory to save the tarball.
    """
    with tarfile.open(os.path.join(save_dir, f"{name}.tar.gz"), "w:gz") as tar:
        tar.add(snapshot_name_dir, arcname=os.path.basename(snapshot_name_dir))


def snapshot_runner(
    name: str,
    no_scrub: bool,
    active_env: bool,
    modules: Optional[list[str]] = None,
    directory: str = "",
) -> None:
    """Execute the sequential snapshot command functions.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    no_scrub : bool
        If True, do not scrub sensitive data from config.
    active_env : bool
        If True, snapshot active environment; otherwise, snapshot specified modules.
    modules : list[str], optional
        List of modules to snapshot.
    directory : str, optional
        Directory to save the snapshot tarball.
    """
    if modules is None:
        modules = []
    snapshot_name_dir = prepare_snapshot_dir(name, no_scrub, modules)
    copy_module_dirs(snapshot_name_dir, modules)
    create_named_tarball(name, snapshot_name_dir, directory)


def check_complete(name: str, directory: str):
    """Check if the snapshot completed successfully.

    If incomplete, raise an error.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    directory : str
        Directory containing the snapshot file.

    Raises
    ------
    MinitrinoError
        If the snapshot tarball was not written.
    """
    snapshot_file = os.path.join(directory, f"{name}.tar.gz")
    if not os.path.isfile(snapshot_file):
        raise MinitrinoError(f"Snapshot tarball failed to write to {snapshot_file}")
