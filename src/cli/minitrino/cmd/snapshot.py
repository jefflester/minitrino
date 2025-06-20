"""Snapshot command for Minitrino CLI.

Provides functionality to create, validate, and manage snapshots of
Minitrino environments, including modules and configuration files.
"""

import fileinput
import os
import shutil
import stat
import tarfile
import tempfile
from typing import Optional

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.settings import (
    LIB,
    MODULE_ADMIN,
    MODULE_CATALOG,
    MODULE_RESOURCES,
    MODULE_ROOT,
    MODULE_SECURITY,
    PROVISION_SNAPSHOT_TEMPLATE,
    SCRUB_KEYS,
    SCRUBBED,
    SNAPSHOT_ROOT_FILES,
)


@click.command(
    "snapshot",
    help=(
        "Create a snapshot of a Minitrino environment. By default, applies to "
        "'default' cluster.\n\n"
        "Once a snapshot is created, a tarball is placed in the Minitrino "
        "lib/snapshots/ directory, usually ~/.minitrino/lib/snapshots/.\n\n"
        "To snapshot an active environment, do not pass in the --module option."
        "\n\n"
        "To snapshot modules whether they are active or not, specify target "
        "modules via the --module option.\n\n"
        "To snapshot a specific running cluster, use the CLUSTER_NAME environment"
        " variable or the --cluster / -c option, e.g.:\n\n"
        "minitrino -c my-cluster snapshot\n\n"
        "or snapshot all clusters via:\n\n"
        "minitrino -c '*' snapshot"
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
    """
    CLI entrypoint for snapshot command.

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
    ctx.initialize()
    utils.check_lib(ctx)

    if directory and not os.path.isdir(directory):
        raise UserError(
            f"Cannot save snapshot in nonexistent directory: {directory}",
            "Pick any directory that exists, and this will work.",
        )

    if not directory:
        directory = os.path.join(ctx.minitrino_user_dir, "snapshots")

    validate_name(name)
    check_exists(name, directory, force)

    modules = list(modules) or []
    for module in modules:
        ctx.modules.validate_module_name(module)
    if modules:
        ctx.logger.info("Creating snapshot of specified modules...")
        modules = ctx.modules.check_dep_modules(list(modules))
        snapshot_runner(name, no_scrub, modules, directory)
    else:
        running = ctx.modules.running_modules()
        if not running:
            ctx.logger.debug(
                "No running Minitrino modules to snapshot. Snapshotting "
                "root resources only.",
            )
            modules = []
        else:
            ctx.logger.info("Creating snapshot of active environment...")
            modules = ctx.modules.check_dep_modules(list(running.keys()))
        snapshot_runner(name, no_scrub, modules, directory)

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
                "Alphanumeric, hyphens, and underscores are allowed. "
                "Rename and retry.",
            )


@utils.pass_environment()
def check_exists(ctx: MinitrinoContext, name: str, directory: str, force: bool) -> None:
    """
    Check if the snapshot tarball exists and handle overwrite logic.

    Parameters
    ----------
    name : str
        Name of the snapshot file.
    directory : str
        Directory containing the snapshot file.
    force : bool
        If True, overwrite without prompting.
    """
    snapshot_file = os.path.abspath(os.path.join(directory, f"{name}.tar.gz"))
    if os.path.isfile(snapshot_file):
        msg = f"Snapshot file {name}.tar.gz already exists."
        if force:
            ctx.logger.info(f"{msg} Overwriting...")
            return
        response = ctx.logger.prompt_msg(f"{msg} Overwrite? [Y/N]")
        if not utils.validate_yes(response):
            ctx.logger.info("Opted to skip snapshot.")
            return


def create_temp_snapshot_dir(name: str, no_scrub: bool, modules: list[str]) -> str:
    """
    Create and populate a temporary directory for snapshot staging.

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
    temp_root = tempfile.mkdtemp(prefix="minitrino-snap-")
    temp_snapshot_dir = os.path.join(temp_root, name)
    os.makedirs(temp_snapshot_dir)
    copy_core_lib_structure(temp_snapshot_dir, name)
    copy_user_config(temp_snapshot_dir, no_scrub)
    write_provision_script(temp_snapshot_dir, modules)
    return temp_snapshot_dir


@utils.pass_environment()
def write_provision_script(
    ctx: MinitrinoContext, temp_snapshot_dir: str, modules: Optional[list[str]] = None
) -> None:
    """
    Write the provisioning shell script for restoring the snapshot.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory where the shell script will be created.
    modules : list of str, optional
        List of modules to include in the command.
    """
    if modules is None:
        modules = []
    command_string = build_command_string(modules)

    file_dest = os.path.join(temp_snapshot_dir, "provision-snapshot.sh")
    ctx.logger.debug(
        f"Creating snapshot command to file at path: {file_dest}",
    )
    with open(file_dest, "w") as provision_command_file:
        provision_command_file.write(PROVISION_SNAPSHOT_TEMPLATE.lstrip())
    st = os.stat(file_dest)
    os.chmod(
        file_dest,
        st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    with open(file_dest, "a") as provision_snapshot_file:
        provision_snapshot_file.write(command_string)


def build_command_string(modules: Optional[list[str]] = None) -> str:
    """
    Build the shell command for provisioning from the snapshot.

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


@utils.pass_environment()
def copy_core_lib_structure(
    ctx: MinitrinoContext, temp_snapshot_dir: str, name: str
) -> None:
    """
    Copy core Minitrino library files and structure to the snapshot dir.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory where the snapshot will be created.
    name : str
        Name of the snapshot.
    """
    os.makedirs(os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, MODULE_ADMIN))
    os.mkdir(os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, MODULE_CATALOG))
    os.mkdir(os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, MODULE_SECURITY))
    os.mkdir(os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, MODULE_RESOURCES))

    # Copy root lib files to snapshot
    for filename in os.listdir(ctx.lib_dir):
        if filename in SNAPSHOT_ROOT_FILES:
            file_path = os.path.join(ctx.lib_dir, filename)
            if os.path.isfile(file_path):
                shutil.copy(file_path, os.path.join(temp_snapshot_dir, LIB))
            elif os.path.isdir(file_path):
                shutil.copytree(
                    file_path, os.path.join(temp_snapshot_dir, LIB, filename)
                )

    # Copy everything from lib/modules/resources
    resources_dir = os.path.join(ctx.lib_dir, MODULE_ROOT, MODULE_RESOURCES)
    for filename in os.listdir(resources_dir):
        file_path = os.path.join(resources_dir, filename)
        shutil.copy(
            file_path,
            os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, MODULE_RESOURCES),
        )


@utils.pass_environment()
def copy_user_config(
    ctx: MinitrinoContext, temp_snapshot_dir: str, no_scrub: bool
) -> None:
    """
    Copy user config, optionally scrub sensitive data.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory where the config file will be copied.
    no_scrub : bool
        If True, do not scrub sensitive data from config.
    """
    if no_scrub:
        response = ctx.logger.prompt_msg(
            "All sensitive information in user config will be added "
            "to the snapshot. Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            copy_and_scrub_user_config(temp_snapshot_dir, no_scrub)
        else:
            ctx.logger.info("Opted to scrub sensitive user config data.")
            copy_and_scrub_user_config(temp_snapshot_dir)
    else:
        copy_and_scrub_user_config(temp_snapshot_dir)


@utils.pass_environment()
def copy_and_scrub_user_config(
    ctx: MinitrinoContext, temp_snapshot_dir: str, no_scrub: bool = False
) -> None:
    """
    Copy the user config file and scrub sensitive data if requested.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory where the config file will be copied.
    no_scrub : bool, optional
        If True, do not scrub sensitive data from config.
    """
    if os.path.isfile(ctx.config_file):
        shutil.copy(ctx.config_file, temp_snapshot_dir)
    else:
        ctx.logger.warn(
            f"No user config file at path: {ctx.config_file}. "
            "Will not be added to snapshot.",
        )
        return

    if not no_scrub:
        scrub_user_config(temp_snapshot_dir)


@utils.pass_environment()
def scrub_user_config(ctx: MinitrinoContext, temp_snapshot_dir: str) -> None:
    """
    Scrub sensitive data from the user config file.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory containing the config file to scrub.
    """
    snapshot_config_file = os.path.join(temp_snapshot_dir, "minitrino.cfg")
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


@utils.pass_environment()
def scrub_line(ctx: MinitrinoContext, line: str) -> str:
    """
    Scrub a single line of config if it contains a sensitive key.

    Parameters
    ----------
    line : str
        The line to scrub.

    Returns
    -------
    str
        The scrubbed line.
    """
    k, v = utils.parse_key_value_pair(ctx, line)
    if any(item in k.lower() for item in SCRUB_KEYS):
        v = SCRUBBED
    return "=".join([k, v])


@utils.pass_environment()
def copy_module_dirs(
    ctx: MinitrinoContext, temp_snapshot_dir: str, modules: Optional[list[str]] = None
) -> None:
    """
    Copy specified module directories into the snapshot directory.

    Parameters
    ----------
    temp_snapshot_dir : str
        Directory where modules will be copied.
    modules : list of str, optional
        List of modules to copy.
    """
    modules = modules or []
    for module in modules:
        module_dir = ctx.modules.data.get(module, {}).get("module_dir", "")
        module_type = ctx.modules.data.get(module, {}).get("type", "")
        dest_dir = os.path.join(
            os.path.join(temp_snapshot_dir, LIB, MODULE_ROOT, module_type),
            os.path.basename(module_dir),
        )
        shutil.copytree(module_dir, dest_dir)


def create_snapshot_tarball(name: str, temp_snapshot_dir: str, save_dir: str) -> None:
    """
    Create a tarball archive of the snapshot directory.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    temp_snapshot_dir : str
        Directory to archive.
    save_dir : str
        Directory to save the tarball.
    """
    with tarfile.open(os.path.join(save_dir, f"{name}.tar.gz"), "w:gz") as tar:
        tar.add(temp_snapshot_dir, arcname=os.path.basename(temp_snapshot_dir))


def move_snapshot_to_destination(
    name: str, temp_snapshot_dir: str, directory: str
) -> None:
    """
    Move resources to the user-specified directory.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    temp_snapshot_dir : str
        Directory to move.
    directory : str
        Directory to save the tarball.
    """
    target_tarball_path = os.path.join(directory, f"{name}.tar.gz")
    target_snapshot_dir = os.path.join(directory, name)

    if os.path.exists(target_snapshot_dir):
        shutil.rmtree(target_snapshot_dir)
    shutil.move(temp_snapshot_dir, target_snapshot_dir)

    temp_tarball_path = os.path.join(
        os.path.dirname(temp_snapshot_dir), f"{name}.tar.gz"
    )

    if os.path.exists(target_tarball_path):
        os.remove(target_tarball_path)
    shutil.move(temp_tarball_path, target_tarball_path)

    temp_root = os.path.dirname(temp_snapshot_dir)
    if os.path.exists(temp_root):
        try:
            os.rmdir(temp_root)
        except OSError:
            pass


def snapshot_runner(
    name: str,
    no_scrub: bool,
    modules: Optional[list[str]] = None,
    directory: str = "",
) -> None:
    """
    Orchestrate the full snapshot creation and output process.

    Parameters
    ----------
    name : str
        Name of the snapshot.
    no_scrub : bool
        If True, do not scrub sensitive data from config.
    modules : list[str], optional
        List of modules to snapshot.
    directory : str, optional
        Directory to save the snapshot tarball.
    """
    modules = modules or []
    temp_snapshot_dir = create_temp_snapshot_dir(name, no_scrub, modules)
    copy_module_dirs(temp_snapshot_dir, modules)
    create_snapshot_tarball(name, temp_snapshot_dir, os.path.dirname(temp_snapshot_dir))
    move_snapshot_to_destination(name, temp_snapshot_dir, directory)


def check_complete(name: str, directory: str):
    """
    Check if the snapshot tarball was created successfully.

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
