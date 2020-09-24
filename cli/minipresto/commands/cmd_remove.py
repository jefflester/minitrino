#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click

from docker.errors import APIError
from minipresto.cli import pass_environment
from minipresto.core import check_daemon
from minipresto.core import validate_yes_response
from minipresto.core import generate_identifier

from minipresto.settings import IMAGE
from minipresto.settings import VOLUME
from minipresto.settings import RESOURCE_LABEL


@click.command("remove", help="""
Removes minipresto resources.
""")
@click.option("-i", "--images", is_flag=True, default=False, help="""
Removes minipresto images.
""")
@click.option("-v", "--volumes", is_flag=True, default=False, help="""
Removes minipresto volumes.
""")
@click.option("-l", "--label", type=str, default=[], multiple=True, help="""
Target specific labels for removal (key-value pair(s)).
""")
@click.option("-f", "--force", is_flag=True, default=False, help="""
Forces the removal of minipresto resources. Normal Docker removal
restrictions apply.
""")


@pass_environment
def cli(ctx, images, volumes, label, force):
    """Remove command for minipresto."""

    check_daemon()

    if images:
        remove_items(IMAGE, force, label)
    if volumes:
        remove_items(VOLUME, force, label)

    if all((not images, not volumes)):
        response = ctx.prompt_msg(
            "You are about to all remove minipresto images and volumes. Continue? [Y/N]"
        )
        if validate_yes_response(response):
            remove_items(IMAGE, force, label)
            remove_items(VOLUME, force, label)
        else:
            ctx.log(f"Opted to skip resource removal.")
            sys.exit(0)

    ctx.log(f"Removal complete.")


@pass_environment
def remove_items(ctx, item_type, force, labels=[]):
    """
    Removes Docker items. If no labels are passed in, all minipresto
    resources are removed. If label(s) are passed in, the removal is limited to
    the passed in labels.
    """

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
            identifier = generate_identifier(
                {"ID": image.short_id, "Image:Tag": try_get_image_tag(image)}
            )
            if force:
                ctx.docker_client.images.remove(
                    image.short_id, force=True, noprune=False
                )
                ctx.vlog(f"{item_type.title()} removed: {identifier}")
            else:
                ctx.docker_client.images.remove(image.short_id)
                ctx.vlog(f"{item_type.title()} removed: {identifier}")
        except APIError as e:
            ctx.vlog(
                f"Cannot remove image: {identifier}\n"
                f"Error from Docker: {e.explanation}"
            )

    volumes = list(set(volumes))
    for volume in volumes:
        try:
            identifier = generate_identifier({"ID": volume.id})
            if force:
                volume.remove(force=True)
                ctx.vlog(f"{item_type.title()} removed: {identifier}")
            else:
                volume.remove()
                ctx.vlog(f"{item_type.title()} removed: {identifier}")
        except APIError as e:
            ctx.vlog(
                f"Cannot remove volume: {identifier}\n"
                f"Error from Docker: {e.explanation}"
            )


def try_get_image_tag(image):
    """
    Tries to get an image tag. If there is no tag, returns an empty string.
    """

    try:
        return image.tags[0]
    except:
        return ""
