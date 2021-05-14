#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino.settings import IMAGE
from minitrino.settings import VOLUME
from minitrino.settings import RESOURCE_LABEL
from docker.errors import APIError


@click.command(
    "remove",
    help=("""Remove Minitrino resources."""),
)
@click.option(
    "-i",
    "--images",
    is_flag=True,
    default=False,
    help=("""Remove Minitrino images."""),
)
@click.option(
    "-v",
    "--volumes",
    is_flag=True,
    default=False,
    help=("""Remove Minitrino container volumes."""),
)
@click.option(
    "-l",
    "--label",
    "labels",
    type=str,
    default=[],
    multiple=True,
    help=(
        """Target specific labels for removal (format: key-value
        pair(s))."""
    ),
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help=(
        """Force the removal of Minitrino resources. Normal Docker removal
        restrictions apply."""
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx, images, volumes, labels, force):
    """Remove command for Minitrino."""

    utils.check_daemon(ctx.docker_client)

    if all((not images, not volumes, not labels)) or all((images, volumes, not labels)):
        response = ctx.logger.prompt_msg(
            "You are about to all remove minitrino images and volumes. Continue? [Y/N]"
        )
        if utils.validate_yes(response):
            remove_items(IMAGE, force)
            remove_items(VOLUME, force)
        else:
            ctx.logger.log(f"Opted to skip resource removal.")
            sys.exit(0)

    if images:
        remove_items(IMAGE, force, labels)
    if volumes:
        remove_items(VOLUME, force, labels)

    ctx.logger.log(f"Removal complete.")


@pass_environment
def remove_items(ctx, item_type, force, labels=[]):
    """Removes Docker items. If no labels are passed in, all Minitrino
    resources are removed. If label(s) are passed in, the removal is limited to
    the passed in labels."""

    if not labels:
        labels = [RESOURCE_LABEL]

    images = []
    volumes = []
    for label in labels:
        if item_type == IMAGE:
            images.extend(ctx.docker_client.images.list(filters={"label": label}))
        if item_type == VOLUME:
            volumes.extend(ctx.docker_client.volumes.list(filters={"label": label}))

    images = list(set(images))
    for image in images:
        try:
            identifier = utils.generate_identifier(
                {"ID": image.short_id, "Image:Tag": try_get_image_tag(image)}
            )
            if force:
                ctx.docker_client.images.remove(
                    image.short_id, force=True, noprune=False
                )
            else:
                ctx.docker_client.images.remove(image.short_id)
            ctx.logger.log(
                f"{item_type.title()} removed: {identifier}",
                level=ctx.logger.verbose,
            )
        except APIError as e:
            ctx.logger.log(
                f"Cannot remove image: {identifier}\n"
                f"Error from Docker: {e.explanation}",
                level=ctx.logger.verbose,
            )

    volumes = list(set(volumes))
    for volume in volumes:
        try:
            identifier = utils.generate_identifier({"ID": volume.id})
            if force:
                volume.remove(force=True)
            else:
                volume.remove()
            ctx.logger.log(
                f"{item_type.title()} removed: {identifier}",
                level=ctx.logger.verbose,
            )
        except APIError as e:
            ctx.logger.log(
                f"Cannot remove volume: {identifier}\n"
                f"Error from Docker: {e.explanation}",
                level=ctx.logger.verbose,
            )


def try_get_image_tag(image):
    """Tries to get an image tag. If there is no tag, returns an empty string."""

    try:
        return image.tags[0]
    except:
        return ""
