#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click

from docker.errors import APIError
from minipresto.cli import pass_environment
from minipresto.commands.core import MultiArgOption
from minipresto.commands.core import check_daemon
from minipresto.commands.core import convert_MultiArgOption_to_list
from minipresto.commands.core import validate_yes_response

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
@click.option("-l", "--label", type=str, default="", cls=MultiArgOption, help="""
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
    (label,) = convert_MultiArgOption_to_list(label)

    if images:
        remove_items({"item_type": IMAGE}, force, label)
    if volumes:
        remove_items({"item_type": VOLUME}, force, label)

    if all((not images, not volumes)):
        response = ctx.prompt_msg(
            "You are about to all remove minipresto images and volumes. Continue? [Y/N]"
        )
        if validate_yes_response(response):
            remove_items({"item_type": IMAGE}, force, label)
            remove_items({"item_type": VOLUME}, force, label)
        else:
            ctx.log(f"Opted to skip removal")
            sys.exit(0)

    ctx.log(f"Removal complete")


@pass_environment
def remove_items(ctx, key, force, labels=[]):
    """
    Removes Docker items. If no labels are passed in, all minipresto
    resources are removed. If label(s) are passed in, the removal is limited to
    the passed in labels.
    """

    item_type = key.get("item_type", "")

    if not labels:
        labels = [RESOURCE_LABEL]

    for label in labels:
        if item_type == IMAGE:
            images = ctx.docker_client.images.list(filters={"label": label})
            for image in images:
                try:
                    if force:
                        ctx.vlog(f"Forcing removal of minipresto image(s)")
                        ctx.docker_client.images.remove(
                            image.short_id, force=True, noprune=False
                        )
                        ctx.vlog(
                            f"{item_type.title()} removed: {image.short_id} {try_get_image_tag(image)}"
                        )
                    else:
                        ctx.docker_client.images.remove(image.short_id)
                        ctx.vlog(
                            f"{item_type.title()} removed: {image.short_id} {try_get_image_tag(image)}"
                        )
                except APIError as error:
                    ctx.vlog(
                        f"Cannot remove image: {image.short_id} {try_get_image_tag(image)}\n"
                        f"Error from Docker: {error.explanation}"
                    )
        elif item_type == VOLUME:
            volumes = ctx.docker_client.volumes.list(filters={"label": label})
            for volume in volumes:
                try:
                    if force:
                        ctx.vlog(f"Forcing removal of minipresto volume {volume.id}")
                        volume.remove(force=True)
                        ctx.vlog(f"{item_type.title()} removed: {volume.id}")
                    else:
                        volume.remove()
                        ctx.vlog(f"{item_type.title()} removed: {volume.id}")
                except APIError as error:
                    ctx.vlog(
                        f"Cannot remove volume: {volume.id}\n"
                        f"Error from Docker: {error.explanation}"
                    )


def try_get_image_tag(image):
    """
    Tries to get an image tag. If there is no tag, returns an empty string.
    """

    try:
        return f"| {image.tags[0]}"
    except:
        return ""
