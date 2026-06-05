"""Starburst version resolution utilities (stdlib only, no third-party deps)."""

import re
import urllib.request
import xml.etree.ElementTree as ET

STARBURST_S3_BUCKET = "https://s3.us-east-2.amazonaws.com/software.starburstdata.net"


def resolve_latest_starburst_ver(base_ver: str) -> str:
    """Resolve the latest patch release for a Starburst LTS version.

    Queries the S3 bucket listing for ``{base_ver}e/`` prefixes and
    returns the highest non-RC release (e.g. ``479-e.8``). Falls back
    to ``{base_ver}-e.0`` (the initial patch, a real release name) on
    any failure, so a transient lookup error does not produce an
    invalid version string that is guaranteed to 404 on download.

    Parameters
    ----------
    base_ver : str
        The base version number (e.g. ``"479"``).
    """
    fallback = f"{base_ver}-e.0"
    try:
        url = f"{STARBURST_S3_BUCKET}?prefix={base_ver}e/&delimiter=/"
        with urllib.request.urlopen(url, timeout=15) as resp:
            tree = ET.parse(resp)
    except Exception:
        return fallback

    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    prefixes = [
        el.text.rstrip("/").split("/")[-1]
        for el in tree.findall(".//s3:CommonPrefixes/s3:Prefix", ns)
        if el.text
    ]

    release_re = re.compile(rf"^{re.escape(base_ver)}-e(?:\.(\d+))?$")
    candidates: list[tuple[int, str]] = []
    for p in prefixes:
        m = release_re.match(p)
        if m:
            candidates.append((int(m.group(1)) if m.group(1) else 0, p))

    if not candidates:
        return fallback

    return max(candidates, key=lambda c: c[0])[1]
