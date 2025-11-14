#!/usr/bin/env python3
"""Tarball Naming and Directory Permutations.

This script supports downloading and unpacking Trino and Starburst
tarballs. The tarball file name and unpack directory structure depend on
the distribution, version, and architecture. The following permutations
are supported:

Trino
-----

Tarball Name
    trino-server-{TRINO_VER}.tar.gz
Unpack Dir
    trino-server-{TRINO_VER}
e.g.
    trino-server-438.tar.gz

Starburst
---------

For versions >= 462:

Tarball Name
    starburst-enterprise-{CLUSTER_VER}.{ARCH}.tar.gz
Unpack Dir
    starburst-enterprise-{CLUSTER_VER}-{ARCH}
e.g.
    starburst-enterprise-462-e.0.aarch64.tar.gz

For versions < 462:

Tarball Name
    starburst-enterprise-{CLUSTER_VER}.tar.gz
Unpack Dir
    starburst-enterprise-{CLUSTER_VER}
e.g.
    starburst-enterprise-438-e.12.tar.gz

Variables
---------

* {TRINO_VER} is the full Trino version string (e.g. 438)
* {CLUSTER_VER} is the full Starburst version string (e.g. 462-e.0)
* {VER_PREFIX} is the first three digits of {CLUSTER_VER}
* {ARCH} is the architecture (e.g. x86_64, aarch64)

The script dynamically constructs these names and paths based on the
provided distribution, version, and detected architecture.
"""

import os
import platform
import shutil
import sys
import tarfile
import time
import urllib.request

LOG_PREFIX = "[downloader]"
TRINO_URL = "https://repo1.maven.org/maven2/io/trino/trino-server"
STARBURST_URL = "https://s3.us-east-2.amazonaws.com/software.starburstdata.net"


def get_arch() -> tuple[str, str]:
    """Detect the current system architecture.

    Returns
    -------
    tuple of str
        (arch_sep_s3, arch_bin), e.g. ("x86_64", "amd64") or ("aarch64",
        "arm64").

    Raises
    ------
    RuntimeError
        If the architecture is not supported.
    """
    raw_arch = platform.machine()
    if raw_arch in ("x86_64", "amd64"):
        return "x86_64", "amd64"
    elif raw_arch in ("arm64", "aarch64"):
        return "aarch64", "arm64"
    else:
        raise RuntimeError(f"Unsupported architecture: {raw_arch}")


def resolve_tarball_info(
    cluster_dist: str, cluster_ver: str
) -> tuple[str, str, str, str]:
    """Resolve the tarball info.

    Parameters
    ----------
    cluster_dist : str
        Cluster distribution ("trino" or "starburst").
    cluster_ver : str
        Cluster version string.

    Returns
    -------
    tuple
        (url, tar_name, unpack_dir, arch_bin)
    """
    arch_sep_s3, arch_bin = get_arch()
    if cluster_dist == "trino":
        trino_ver = cluster_ver
        tar_name = f"trino-server-{trino_ver}.tar.gz"
        url = f"{TRINO_URL}/{trino_ver}/{tar_name}"
        unpack_dir = f"trino-server-{trino_ver}"
    elif cluster_dist == "starburst":
        trino_ver = cluster_ver[:3]
        if int(trino_ver) >= 462:
            tar_name = f"starburst-enterprise-{cluster_ver}.{arch_sep_s3}.tar.gz"
            unpack_dir = f"starburst-enterprise-{cluster_ver}-{arch_sep_s3}"
        else:
            tar_name = f"starburst-enterprise-{cluster_ver}.tar.gz"
            unpack_dir = f"starburst-enterprise-{cluster_ver}"
        url = f"{STARBURST_URL}/{cluster_ver[:3]}e/{cluster_ver}/{tar_name}"
    else:
        raise RuntimeError("Invalid cluster distribution")
    return url, tar_name, unpack_dir, arch_bin


def download_tarball(url: str, tar_path: str) -> None:
    """Download a tarball from a URL to a local file.

    Parameters
    ----------
    url : str
        The URL to download from.
    tar_path : str
        Path to save the downloaded tarball.
    """
    print(f"{LOG_PREFIX} Downloading {url} ...")
    with urllib.request.urlopen(url) as response, open(tar_path, "wb") as out_file:
        total_size = response.getheader("Content-Length")
        total_size = int(total_size) if total_size is not None else None
        chunk_size = 8192
        downloaded = 0
        last_print_time = time.time()
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            now = time.time()
            if total_size:
                percent = (downloaded / total_size) * 100
                status = f"Downloading tarball... {percent:.1f}% complete"
            else:
                status = f"Downloading tarball... {downloaded // 1024} KB"
            if now - last_print_time >= 2:
                print(f"{LOG_PREFIX} {status}")
                sys.stdout.flush()
                last_print_time = now
        if total_size:
            print(f"{LOG_PREFIX} Downloading tarball... 100.0% complete")
        print(f"{LOG_PREFIX} Downloaded to {tar_path}")


def unpack_tarball(tar_path: str, dest_dir: str) -> None:
    """Extract a gzipped tarball to a destination directory.

    Parameters
    ----------
    tar_path : str
        Path to the tarball file.
    dest_dir : str
        Directory to extract contents into.
    """
    print(f"{LOG_PREFIX} Extracting {tar_path} ...")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=dest_dir)
    print(f"{LOG_PREFIX} Extracted to {dest_dir}")


def unpack_and_copy(cluster_dist: str, unpack_dir: str, arch_bin: str) -> None:
    """Copy files from the unpacked tarball to the destination.

    Parameters
    ----------
    cluster_dist : str
        Cluster distribution name.
    unpack_dir : str
        Directory of the unpacked tarball.
    arch_bin : str
        Architecture string for binaries (e.g. "amd64").
    """
    dest_dir = f"/usr/lib/{cluster_dist}"
    os.makedirs(dest_dir, exist_ok=True)
    # Copy all files from unpack_dir to dest_dir
    for item in os.listdir(unpack_dir):
        s = os.path.join(unpack_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
    # Remove non-linux and non-arch-specific bins
    bin_dir = os.path.join(dest_dir, "bin")
    for name in os.listdir(bin_dir):
        if name.startswith("darwin-") or (
            name.startswith("linux-") and name != f"linux-{arch_bin}"
        ):
            path = os.path.join(bin_dir, name)
            print(f"{LOG_PREFIX} Removing bin: {name}")
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
    # Copy linux-arch_bin if present
    src_arch_bin = os.path.join(unpack_dir, "bin", f"linux-{arch_bin}")
    if os.path.isdir(src_arch_bin):
        dest_arch_bin = os.path.join(bin_dir, f"linux-{arch_bin}")
        if os.path.exists(dest_arch_bin):
            shutil.rmtree(dest_arch_bin)
        shutil.copytree(src_arch_bin, dest_arch_bin)


def main(cluster_ver: str, cluster_dist: str) -> None:
    """Download, extract, and copy distro tarball.

    Parameters
    ----------
    cluster_ver : str
        Cluster version string.
    cluster_dist : str
        Cluster distribution string ("trino" or "starburst").
    """
    url, tar_name, unpack_dir, arch_bin = resolve_tarball_info(
        cluster_dist, cluster_ver
    )
    tmp_dir = "/tmp"
    tar_path = os.path.join(tmp_dir, tar_name)
    download_tarball(url, tar_path)
    os.chdir(tmp_dir)
    unpack_tarball(tar_path, tmp_dir)
    unpack_and_copy(cluster_dist, unpack_dir, arch_bin)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: downloader.py <CLUSTER_VER> <CLUSTER_DIST>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
