"""Resource management commands for Minitrino CLI."""

import itertools
import sys
import textwrap
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

import click
import humanize
from dateutil.parser import parse as parse_date
from tabulate import tabulate

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "resources",
    help="Display all Docker resources in the Minitrino environment.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext):
    """Display resource information.

    Show resource usage for the environment.
    """
    ctx.initialize()
    utils.check_daemon(ctx.docker_client)

    resources = ctx.cluster.resource.resources()
    containers = resources.containers()
    volumes = resources.volumes()
    networks = resources.networks()
    images = [
        img
        for img in resources.images()
        if img.tags and any(t.strip() for t in img.tags)
    ]

    containers = sorted(containers, key=lambda c: (c.cluster_name, c.name))
    volumes = sorted(volumes, key=lambda v: (v.cluster_name, v.name))
    networks = sorted(networks, key=lambda n: (n.cluster_name, n.name))

    spinner_done = start_spinner("Fetching container stats...")
    container_stats: dict = {}
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
    time.sleep(0.1)  # Allow spinner thread to exit
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()

    container_rows = []
    for c in containers:
        cluster = c.cluster_name
        created = parse_date(c.attrs["Created"])
        age = humanize.naturaltime(datetime.now(timezone.utc) - created)
        stats = container_stats.get(c.id, {"memory": "N/A", "cpu": "N/A"})
        container_rows.append(
            [
                cluster,
                c.name,
                color_status(c.status),
                age,
                stats["memory"],
                stats["cpu"],
            ]
        )

    image_rows = []
    for img in sorted(images, key=lambda x: x.tags[0]):
        size = humanize.naturalsize(img.attrs["Size"])
        tags = textwrap.shorten(", ".join(img.tags), width=60, placeholder="...")
        image_created = parse_date(img.attrs["Created"])
        age = humanize.naturaltime(datetime.now(timezone.utc) - image_created)
        image_rows.append([tags, size, age])

    volume_rows = []
    for v in volumes:
        cluster = v.cluster_name
        created_str = v.attrs.get("CreatedAt")
        try:
            vol_created: Optional[datetime] = (
                parse_date(created_str) if created_str else None
            )
            age = (
                humanize.naturaltime(datetime.now(timezone.utc) - vol_created)
                if vol_created
                else "Unknown"
            )
        except Exception:
            age = "Unknown"
        volume_rows.append([cluster, v.name, age])

    network_rows = [
        [n.cluster_name, n.name, n.attrs.get("Driver", "N/A")] for n in networks
    ]

    sections = [
        (
            "Containers",
            container_rows,
            ["Cluster", "Name", "Status", "Age", "Memory", "CPU"],
        ),
        ("Images", image_rows, ["Tags", "Size", "Age"]),
        ("Volumes", volume_rows, ["Cluster", "Name", "Age"]),
        ("Networks", network_rows, ["Cluster", "Name", "Driver"]),
    ]

    rendered_sections = []
    max_divider_len = 0
    for title, rows, headers in sections:
        table_str, divider_len = render_table(rows, headers)
        rendered_sections.append((title, table_str, divider_len))
        max_divider_len = max(max_divider_len, divider_len)

    for title, table_str, _ in rendered_sections:
        full_output = "\n".join(
            [
                "-" * max_divider_len,
                f"{title}",
                "-" * max_divider_len,
                table_str,
                "-" * max_divider_len,
            ]
        )
        sys.stdout.write(full_output + "\n")


@utils.pass_environment()
def start_spinner(ctx: MinitrinoContext, message: str = "Fetching container stats..."):
    """Start the spinner.

    Parameters
    ----------
    message : str
        Message to display alongside the spinner.
    """
    spinner_done = threading.Event()

    def spin():
        prefix = ctx.logger.styled_prefix()
        for c in itertools.cycle(r"\|/-"):
            if spinner_done.is_set():
                break
            sys.stdout.write(f"\r{prefix}{message} {c}")
            sys.stdout.flush()
            time.sleep(0.1)

    thread = threading.Thread(target=spin)
    thread.start()
    return spinner_done


def render_table(rows: Optional[list[list[Any]]], headers: list[str]):
    """Render a table of resources.

    Parameters
    ----------
    rows : list[list[Any]]
        Data rows to be rendered.
    headers : list[str]
        Table column headers.

    Returns
    -------
    tuple[str, int]
        Rendered table string and the length of its longest line.
    """
    if rows is None:
        rows = []
    rendered = tabulate(rows, headers=headers, stralign="left", tablefmt="github")
    divider_len = max(len(line) for line in rendered.splitlines())
    return rendered, divider_len


def format_bytes(val: int | float):
    """Format bytes as a human-readable string.

    Parameters
    ----------
    val : int or float

    Returns
    -------
    str
        Human-readable memory string or 'N/A'.
    """
    return (
        humanize.naturalsize(val)
        if isinstance(val, (int, float)) and val > 0
        else "N/A"
    )


def format_cpus(nanos: int):
    """Convert CPU units to a readable format.

    Parameters
    ----------
    nanos : int

    Returns
    -------
    str
        CPU usage as a percentage string or 'N/A'.
    """
    return f"{nanos / 1e9:.2f}" if isinstance(nanos, int) and nanos > 0 else "N/A"


def color_status(status: str):
    """Apply color to status text.

    Parameters
    ----------
    status : str
        Container status (e.g., 'running', 'exited').

    Returns
    -------
    str
        Colorized status string.
    """
    if "up" in status.lower():
        return click.style(status, fg="green")
    if "exited" in status.lower():
        return click.style(status, fg="red")
    return status


def get_container_stats(container) -> dict:
    """Fetch memory and CPU usage statistics for a container.

    Parameters
    ----------
    container : docker.models.containers.Container

    Returns
    -------
    dict
        Dictionary with keys 'memory' and 'cpu' representing usage
        stats.
    """
    try:
        stats = container.stats(stream=False)
        mem = stats.get("memory_stats", {}).get("usage", 0)
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        cpu_usage = cpu_stats.get("cpu_usage", {})
        precpu_usage = precpu_stats.get("cpu_usage", {})
        cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
        system_cpu_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
            "system_cpu_usage", 0
        )
        percpu_usage = cpu_usage.get("percpu_usage", [1])
        cpu_percent = (
            (cpu_delta / system_cpu_delta) * len(percpu_usage) * 100.0
            if system_cpu_delta > 0
            else 0.0
        )
        return {"memory": humanize.naturalsize(mem), "cpu": f"{cpu_percent:.2f}%"}
    except Exception:
        return {"memory": "N/A", "cpu": "N/A"}
