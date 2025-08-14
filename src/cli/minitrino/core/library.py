"""Handles installation and management of Minitrino libraries."""

import os
import re
import shutil
import tarfile
from typing import TYPE_CHECKING

import requests

from minitrino import utils
from minitrino.core.errors import MinitrinoError, UserError

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class LibraryManager:
    """Handles installation and management of Minitrino libraries."""

    def __init__(self, ctx: "MinitrinoContext"):
        self.ctx = ctx
        self.releases_url = "https://api.github.com/repos/jefflester/minitrino/releases"

    def install(self, version: str = "") -> None:
        """Install or update the Minitrino library."""
        if not version:
            version = utils.cli_ver()

        self.validate(version)
        lib_dir = os.path.join(self.ctx.minitrino_user_dir, "lib")

        if os.path.isdir(lib_dir):
            response = self.ctx.logger.prompt_msg(
                f"The Minitrino library at {lib_dir} will be overwritten. "
                f"Continue? [Y/N]"
            )
            if not utils.validate_yes(response):
                self.ctx.logger.info("Opted to skip library installation.")
                return
            self.ctx.logger.debug("Removing existing library directory...")
            shutil.rmtree(lib_dir)

        self.download_and_extract(version)
        self.ctx.logger.info("Library installation complete.")

    def list_releases(self) -> list[str]:
        """List all available releases from GitHub."""
        releases = []
        page = 1
        while True:
            resp = requests.get(
                self.releases_url, params={"per_page": 100, "page": page}
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            releases.extend([release["tag_name"] for release in data])
            if len(data) < 100:
                break
            page += 1
        return sorted(releases)

    def validate(self, version: str) -> None:
        """Validate the version string format and existence."""
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            cli_ver = utils.cli_ver()
            raise UserError(
                f"Release version must be in X.Y.Z format (e.g., {cli_ver})"
            )
        if version not in self.list_releases():
            raise MinitrinoError(f"Release {version} not found on GitHub")

    def download_and_extract(self, version: str) -> None:
        """Download and extract the library tarball."""
        base_url = "https://github.com/jefflester/minitrino"
        uri = f"{base_url}/archive/refs/tags/{version}.tar.gz"
        tarball = os.path.join(self.ctx.minitrino_user_dir, f"{version}.tar.gz")
        file_basename = f"minitrino-{version}"
        lib_dir = os.path.join(self.ctx.minitrino_user_dir, file_basename, "src", "lib")

        try:
            self._download_file(uri, tarball)
            self._extract_tarball(tarball, self.ctx.minitrino_user_dir)
            shutil.move(lib_dir, os.path.join(self.ctx.minitrino_user_dir, "lib"))
            self._cleanup(tarball, file_basename)
        except Exception as e:
            self._cleanup(tarball, file_basename, False)
            raise MinitrinoError(str(e))

    def _download_file(self, url: str, dest_path: str) -> None:
        """Download a file from URL to destination path."""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    @staticmethod
    def _extract_tarball(tarball_path: str, extract_dir: str) -> None:
        """Extract a .tar.gz file to the given directory."""
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=extract_dir, filter="fully_trusted")

    def auto_install_or_update(self) -> None:
        """
        Automatically install or update Minitrino libraries to match the CLI version.

        This method checks if the Minitrino library is installed and if its version
        matches the CLI version. If not installed, it will automatically install the
        library. If versions don't match, it will prompt the user to update.
        """
        cli_version = utils.cli_ver()
        library_version = utils.lib_ver(ctx=self.ctx, lib_path=self.ctx.lib_dir)

        if library_version == "NOT INSTALLED":
            self.ctx.logger.warn(
                "Minitrino library is not installed. Installing Minitrino libraries... "
            )
            self.install(version=cli_version)
        elif cli_version != library_version:
            response = self.ctx.logger.prompt_msg(
                f"The current CLI version is {cli_version} which does not match "
                f"the installed library version {library_version}. "
                f"Install library version {cli_version}? [Y/N]"
            )
            if utils.validate_yes(response):
                self.ctx.logger.info(
                    f"Overwriting existing Minitrino library to version {cli_version}"
                )
                self.install(version=cli_version)
            else:
                self.ctx.logger.warn(
                    "It is highly recommended to use matching CLI and library versions."
                    " Mismatched versions are likely to cause errors."
                    " To install the library manually, run `minitrino lib-install`."
                )
        else:
            self.ctx.logger.debug("CLI and library versions match. No action required.")

    def _cleanup(
        self, tarball: str = "", file_basename: str = "", trigger_error: bool = True
    ) -> None:
        """Clean up downloaded and extracted files."""
        tarball_path = tarball
        unpacked_dir = (
            os.path.join(self.ctx.minitrino_user_dir, file_basename)
            if file_basename
            else None
        )
        errors = []

        if tarball_path and os.path.isfile(tarball_path):
            try:
                os.remove(tarball_path)
            except Exception as e:
                errors.append(f"Failed to remove tarball {tarball_path}: {e}")

        if unpacked_dir and os.path.exists(unpacked_dir):
            try:
                (
                    shutil.rmtree(unpacked_dir)
                    if os.path.isdir(unpacked_dir)
                    else os.remove(unpacked_dir)
                )
            except Exception as e:
                errors.append(f"Failed to remove directory {unpacked_dir}: {e}")

        if errors and trigger_error:
            raise MinitrinoError("\n".join(errors))
