"""Resource management commands for Minitrino CLI."""

import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

import click
import humanize
from dateutil.parser import parse as parse_date
from tabulate import tabulate

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.shutdown import shutdown_event


@click.command(
    "resources",
    help="Display all Docker resources in the Minitrino environment.",
)
@click.option(
    "--container", "-c", "show_container", is_flag=True, help="Show only containers."
)
@click.option("--volume", "-v", "show_volume", is_flag=True, help="Show only volumes.")
@click.option("--image", "-i", "show_image", is_flag=True, help="Show only images.")
@click.option(
    "--network", "-n", "show_network", is_flag=True, help="Show only networks."
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    show_container: bool = False,
    show_network: bool = False,
    show_volume: bool = False,
    show_image: bool = False,
):
    """Display resource information.

    Show resource usage for the environment.

    Parameters
    ----------
    ctx : MinitrinoContext
        The Minitrino context.
    show_container : bool
        If True, shows only containers.
    show_network : bool
        If True, shows only networks.
    show_volume : bool
        If True, shows only volumes.
    show_image : bool
        If True, shows only images.
    """
    ctx.initialize()
    utils.check_daemon(ctx.docker_client)

    resources = ctx.cluster.resource.resources()
    show_any = show_container or show_network or show_volume or show_image
    fetch_containers = show_container or not show_any
    fetch_images = show_image or not show_any
    fetch_volumes = show_volume or not show_any
    fetch_networks = show_network or not show_any

    containers = []
    container_rows = []
    container_stats: dict = {}
    if fetch_containers:
        containers = resources.containers()
        containers = sorted(containers, key=lambda c: (c.cluster_name, c.name))
        with ctx.logger.spinner("Fetching container stats..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_container = {
                    executor.submit(get_container_stats, c): c for c in containers
                }
                for future in as_completed(future_to_container):
                    if shutdown_event.is_set():
                        ctx.logger.warn(
                            "Shutdown detected. Aborting container stats fetch."
                        )
                        break
                    container = future_to_container[future]
                    try:
                        stats = future.result()
                    except Exception:
                        stats = {"memory": "N/A", "cpu": "N/A"}
                    container_stats[container.id] = stats
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

        container_network_rows = []
        for c in containers:
            ports, host_endpoints = c.ports_and_host_endpoints()
            ports_str = ", ".join(ports) if ports else "<none>"
            endpoints_str = ", ".join(host_endpoints) if host_endpoints else "<none>"
            container_network_rows.append(
                [
                    c.cluster_name,
                    c.name,
                    ports_str,
                    endpoints_str,
                ]
            )

    image_rows = []
    if fetch_images:
        images = [
            img
            for img in resources.images()
            if img.tags and any(t.strip() for t in img.tags)
        ]
        for img in sorted(images, key=lambda x: x.tags[0]):
            size = humanize.naturalsize(img.attrs["Size"])
            tags = textwrap.shorten(", ".join(img.tags), width=60, placeholder="...")
            image_created = parse_date(img.attrs["Created"])
            age = humanize.naturaltime(datetime.now(timezone.utc) - image_created)
            image_rows.append([tags, size, age])

    volume_rows = []
    if fetch_volumes:
        volumes = resources.volumes()
        volumes = sorted(volumes, key=lambda v: (v.cluster_name, v.name))
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

    network_rows = []
    if fetch_networks:
        networks = resources.networks()
        networks = sorted(networks, key=lambda n: (n.cluster_name, n.name))
        network_rows = [
            [n.cluster_name, n.name, n.attrs.get("Driver", "N/A")] for n in networks
        ]

    # Determine which sections to display based on flags
    sections = []
    if fetch_containers:
        sections.append(
            (
                "Containers",
                container_rows,
                ["Cluster", "Name", "Status", "Age", "Memory", "CPU"],
            )
        )
        sections.append(
            (
                "Container Ports and Endpoints",
                container_network_rows,
                ["Cluster", "Name", "Ports", "Host Endpoints"],
            )
        )
    if show_image or not show_any:
        sections.append(("Images", image_rows, ["Tags", "Size", "Age"]))
    if show_volume or not show_any:
        sections.append(("Volumes", volume_rows, ["Cluster", "Name", "Age"]))
    if show_network or not show_any:
        sections.append(("Networks", network_rows, ["Cluster", "Name", "Driver"]))

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


def get_container_stats(container: MinitrinoContainer) -> dict:
    """Fetch memory and CPU usage statistics for a container.

    Parameters
    ----------
    container : MinitrinoContainer

    Returns
    -------
    dict
        Dictionary with keys 'memory' and 'cpu' representing usage
        stats.
    """
    try:
        stats: dict = container.stats(stream=False)
        mem: int = stats.get("memory_stats", {}).get("usage", 0)
        cpu_stats: dict = stats.get("cpu_stats", {})
        precpu_stats: dict = stats.get("precpu_stats", {})
        cpu_usage: dict = cpu_stats.get("cpu_usage", {})
        precpu_usage: dict = precpu_stats.get("cpu_usage", {})
        cpu_delta: int = cpu_usage.get("total_usage", 0) - precpu_usage.get(
            "total_usage", 0
        )
        system_cpu_delta: int = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
            "system_cpu_usage", 0
        )
        percpu_usage: list[int] = cpu_usage.get("percpu_usage", [1])
        cpu_percent: float = (
            (cpu_delta / system_cpu_delta) * len(percpu_usage) * 100.0
            if system_cpu_delta > 0
            else 0.0
        )
        return {"memory": humanize.naturalsize(mem), "cpu": f"{cpu_percent:.2f}%"}
    except Exception:
        return {"memory": "N/A", "cpu": "N/A"}
