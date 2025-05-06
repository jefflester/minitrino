#!/usr/bin/env python3

import sys
import time
import click
import humanize
import itertools
import threading

from minitrino.components import Environment
from minitrino.cli import pass_environment
from minitrino import utils
from minitrino.settings import COMPOSE_LABEL
from minitrino.settings import RESOURCE_LABEL
from tabulate import tabulate
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date


def start_spinner(message="Fetching container stats..."):
    spinner_done = threading.Event()

    def spin():
        for c in itertools.cycle(r"\|/-"):
            if spinner_done.is_set():
                break
            sys.stdout.write(f"\r[i]  {message} {c}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\n")

    thread = threading.Thread(target=spin)
    thread.start()
    return spinner_done


@click.command(
    "resources",
    help=(
        """Display all resources in the Minitrino environment:
        
        - Clusters\n
        - Containers\n
        - Images\n
        - Volumes\n
        - Networks
        """
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx: Environment):
    utils.check_daemon(ctx.docker_client)

    resources = ctx.get_cluster_resources()
    containers = resources["containers"]
    images = resources["images"]
    volumes = resources["volumes"]
    networks = resources["networks"]

    from concurrent.futures import ThreadPoolExecutor, as_completed

    spinner_done = start_spinner("Fetching container stats...")
    container_stats = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_container = {
            executor.submit(get_container_stats, c): c for c in containers
        }
        for future in as_completed(future_to_container):
            container = future_to_container[future]
            try:
                stats = future.result()
            except Exception:
                stats = {"memory": "N/A", "cpu": "N/A"}
            container_stats[container.id] = stats
    spinner_done.set()
    sys.stdout.write("\n")

    ctx.logger.info("\n" + "-" * 80 + "\nContainers:")
    container_rows = []
    for c in containers:
        created = parse_date(c.attrs["Created"])
        age = humanize.naturaltime(datetime.now(timezone.utc) - created)
        stats = container_stats.get(c.id, {"memory": "N/A", "cpu": "N/A"})
        container_rows.append(
            [
                c.name,
                color_status(c.status),
                age,
                stats["memory"],
                stats["cpu"],
            ]
        )
    ctx.logger.info(
        tabulate(
            container_rows,
            headers=["Name", "Status", "Age", "Memory", "CPU"],
            stralign="left",
        )
    )

    ctx.logger.info("\n" + "-" * 80 + "\nImages:")
    image_rows = []
    for img in images:
        size = humanize.naturalsize(img.attrs["Size"])
        tags = ", ".join(img.tags) or "<none>"
        if len(tags) > 60:
            tags = tags[:57] + "..."
        created = parse_date(img.attrs["Created"])
        age = humanize.naturaltime(datetime.now(timezone.utc) - created)
        image_rows.append([tags, size, age])
    ctx.logger.info(
        tabulate(image_rows, headers=["Tags", "Size", "Age"], stralign="left")
    )

    ctx.logger.info("\n" + "-" * 80 + "\nVolumes:")
    volume_rows = []
    for v in volumes:
        created_str = v.attrs.get("CreatedAt")
        try:
            created = parse_date(created_str) if created_str else None
            age = (
                humanize.naturaltime(datetime.now(timezone.utc) - created)
                if created
                else "Unknown"
            )
        except Exception:
            age = "Unknown"
        volume_rows.append([v.name, age])
    ctx.logger.info(tabulate(volume_rows, headers=["Name", "Age"], stralign="left"))

    ctx.logger.info("\n" + "-" * 80 + "\nNetworks:")
    network_rows = [[n.name, n.attrs.get("Driver", "N/A")] for n in networks]
    ctx.logger.info(tabulate(network_rows, headers=["Name", "Driver"], stralign="left"))


def format_bytes(val):
    return (
        humanize.naturalsize(val)
        if isinstance(val, (int, float)) and val > 0
        else "N/A"
    )


def format_cpus(nanos):
    return f"{nanos / 1e9:.2f}" if isinstance(nanos, int) and nanos > 0 else "N/A"


def color_status(status):
    if "up" in status.lower():
        return click.style(status, fg="green")
    if "exited" in status.lower():
        return click.style(status, fg="red")
    return status


def get_container_stats(container):
    try:
        stats = container.stats(stream=False)
        mem = stats.get("memory_stats", {}).get("usage", 0)
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_cpu_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        cpu_percent = (
            (cpu_delta / system_cpu_delta)
            * len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
            * 100.0
            if system_cpu_delta > 0
            else 0.0
        )
        return {"memory": humanize.naturalsize(mem), "cpu": f"{cpu_percent:.2f}%"}
    except Exception:
        return {"memory": "N/A", "cpu": "N/A"}
