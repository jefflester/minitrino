#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click
from concurrent.futures import ThreadPoolExecutor, as_completed

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino.settings import RESOURCE_LABEL


@click.command(
    "down",
    help=(
        """Bring down running Minitrino containers. This command follows the
        behavior of `docker compose down` where containers are both stopped and
        removed."""
    ),
)
@click.option(
    "-k",
    "--keep",
    is_flag=True,
    default=False,
    help=(
        """Does not remove containers; instead, containers will only be
        stopped."""
    ),
)
@click.option(
    "--sig-kill",
    is_flag=True,
    default=False,
    help=("""Stop Minitrino containers without a grace period."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx, sig_kill, keep):
    """Down command for Minitrino. Exits with a 0 status code if there are no
    running minitrino containers."""

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    if len(containers) == 0:
        ctx.logger.info("No containers to bring down.")
        sys.exit(0)

    # Helper function to stop a container
    def stop_container(container):
        identifier = utils.generate_identifier(
            {"ID": container.short_id, "Name": container.name}
        )
        if container.status == "running":
            if sig_kill:
                container.kill()
            else:
                container.stop()
            ctx.logger.verbose(f"Stopped container: {identifier}")
        return container

    # Helper function to remove a container
    def remove_container(container):
        identifier = utils.generate_identifier(
            {"ID": container.short_id, "Name": container.name}
        )
        container.remove()
        ctx.logger.verbose(f"Removed container: {identifier}")

    # Stop containers in parallel
    with ThreadPoolExecutor() as executor:
        stop_futures = {
            executor.submit(stop_container, container): container
            for container in containers
        }
        for future in as_completed(stop_futures):
            container = stop_futures[future]
            try:
                future.result()
            except Exception as e:
                ctx.logger.error(
                    f"Error stopping container '{container.name}': {str(e)}"
                )

    # Remove containers in parallel if not keeping them
    if not keep:
        with ThreadPoolExecutor() as executor:
            remove_futures = {
                executor.submit(remove_container, container): container
                for container in containers
            }
            for future in as_completed(remove_futures):
                container = remove_futures[future]
                try:
                    future.result()
                except Exception as e:
                    ctx.logger.error(
                        f"Error removing container '{container.name}': {str(e)}"
                    )

    ctx.logger.info("Brought down all Minitrino containers.")
