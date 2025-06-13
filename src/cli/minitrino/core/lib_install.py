"""Commands for installing Minitrino libraries."""

import os
import re
import shutil
import tarfile

import requests

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError


class MinitrinoLibary:
    """
    A class to manage the installation of Minitrino libraries.

    This class provides methods to validate, download, extract, and install
    Minitrino libraries from GitHub releases. It also handles cleanup of
    temporary files and directories during the installation process.

    Parameters
    ----------
    ctx : MinitrinoContext
        The context object containing configuration and state for Minitrino.

    Attributes
    ----------
    _ctx : MinitrinoContext
        The context object passed during initialization.
    _version : str
        The version of the library to install. Defaults to an empty string.
    _list_releases : bool
        A flag to indicate whether to list available releases. Defaults to False.
    """

    def __init__(self, ctx: MinitrinoContext) -> None:
        self._ctx = ctx
        self._version = ""
        self._list_releases = False

    # def cli(ctx: MinitrinoContext, version: str, list_releases: bool) -> None:
    def cli(self) -> None:
        """
        Install the Minitrino library from a tagged GitHub release.

        If a library directory already exists, prompt the user for
        permission before overwriting it. The version defaults to the
        current CLI version if not explicitly specified.

        Parameters
        ----------
        version : str
            The library version to install. If empty, defaults to the CLI
            version.
        list_releases : bool
            If True, list all available releases and exit.
        """
        self._ctx.initialize()
        if self._list_releases:
            self.list_github_releases(log=True)
            return
        if not self._version:
            self._version = utils.cli_ver()
        self.validate(self._version)
        lib_dir = os.path.join(self._ctx.minitrino_user_dir, "lib")
        if os.path.isdir(lib_dir):
            response = self._ctx.logger.prompt_msg(
                f"The Minitrino library at {lib_dir} will be overwritten. "
                f"Continue? [Y/N]"
            )
            if utils.validate_yes(response):
                self._ctx.logger.debug("Removing existing library directory...")
                shutil.rmtree(lib_dir)
            else:
                self._ctx.logger.info("Opted to skip library installation.")
                return
        self.download_and_extract(self._version)
        self._ctx.logger.info("Library installation complete.")

    # def validate(version: str) -> None:
    def validate(self, version: str) -> None:
        """Validate the version string."""
        if not version:
            return
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            cli_ver = utils.cli_ver()
            raise UserError(
                f"Release version must be in X.Y.Z format (e.g., {cli_ver})"
            )
        release = [r for r in self.list_github_releases() if r == version]
        if not release:
            raise MinitrinoError(f"Release {version} not found on GitHub")

    # def list_github_releases(ctx: MinitrinoContext, log: bool = False) -> list[str]:
    def list_github_releases(self, log: bool = False) -> list[str]:
        """Return a list of release tag names for the given GitHub repo."""
        releases = []
        page = 1
        releases_url = "https://api.github.com/repos/jefflester/minitrino/releases"
        while True:
            resp = requests.get(releases_url, params={"per_page": 100, "page": page})
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            releases.extend([release["tag_name"] for release in data])
            if len(data) < 100:
                break
            page += 1
        if log:
            self._ctx.logger.info("Available Minitrino releases:")
            self._ctx.logger.info(*sorted(releases))
        return releases

    # def download_and_extract(ctx: MinitrinoContext, version: str = "") -> None:
    def download_and_extract(self, version: str = "") -> None:
        """Download and extract the Minitrino library from GitHub.

        Download the release tarball for the given version, unpack it, and
        move the `lib/` directory to the user's Minitrino directory. If the
        library fails to install, raise a `MinitrinoError`.

        Parameters
        ----------
        version : str, optional
            The version to download. Defaults to an empty string.
        """
        fname = f"{version}.tar.gz"
        uri = f"https://github.com/jefflester/minitrino/archive/refs/tags/{fname}"
        tarball = os.path.join(self._ctx.minitrino_user_dir, fname)
        file_basename = f"minitrino-{version}"  # filename after unpacking
        lib_dir = os.path.join(
            self._ctx.minitrino_user_dir, file_basename, "src", "lib"
        )

        try:
            try:
                self.download_file(uri, tarball)
            except requests.HTTPError as e:
                raise MinitrinoError(f"Failed to download Minitrino library: {e}")
            if not os.path.isfile(tarball):
                raise MinitrinoError(
                    f"Failed to download Minitrino library ({tarball} not found)."
                )
            self._ctx.logger.debug(
                f"Unpacking tarball at {tarball} and copying library...",
            )
            self.extract_tarball(tarball, self._ctx.minitrino_user_dir)
            shutil.move(lib_dir, os.path.join(self._ctx.minitrino_user_dir, "lib"))
            lib_dir = os.path.join(self._ctx.minitrino_user_dir, "lib")
            if not os.path.isdir(lib_dir):
                raise MinitrinoError(
                    f"Library failed to install (not found at {lib_dir})"
                )
            self.cleanup(tarball, file_basename)
        except Exception as e:
            self.cleanup(tarball, file_basename, False)
            raise MinitrinoError(str(e))

    # def download_file(url: str, dest_path: str) -> None:
    def download_file(self, url: str, dest_path: str) -> None:
        """Download a file from a URL to a local path using requests."""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    # def extract_tarball(self, tarball_path: str, extract_dir: str) -> None:
    def extract_tarball(self, tarball_path: str, extract_dir: str) -> None:
        """Extract a .tar.gz file to the given directory."""
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=extract_dir, filter="fully_trusted")

    # def cleanup( ctx: MinitrinoContext,tarball: str = "",
    #   file_basename: str = "", trigger_error: bool = True) -> None:
    def cleanup(
        self,
        tarball: str = "",
        file_basename: str = "",
        trigger_error: bool = True,
    ) -> None:
        """
        Remove the downloaded tarball and extracted files using Python only.

        Parameters
        ----------
        tarball : str, optional
            Path to the downloaded tarball.
        file_basename : str, optional
            Base name of the unpacked directory to remove.
        trigger_error : bool, optional
            If True, log errors on failure. Default is True.
        """
        tarball_path = tarball
        unpacked_dir = (
            os.path.join(self._ctx.minitrino_user_dir, file_basename)
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
                if os.path.isdir(unpacked_dir):
                    shutil.rmtree(unpacked_dir)
                else:
                    os.remove(unpacked_dir)
            except Exception as e:
                errors.append(
                    f"Failed to remove unpacked directory {unpacked_dir}: {e}"
                )
        if errors and trigger_error:
            for err in errors:
                self._ctx.logger.error(err)
            raise MinitrinoError("Cleanup failed: " + "; ".join(errors))
