"""Handles installation and management of Minitrino libraries."""

import contextlib
import json
import os
import re
import shutil
import tarfile
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import requests

from minitrino import utils
from minitrino.errors import MinitrinoError, UserError

BACKUP_PREFIX = "lib.bak."
BACKUP_RETENTION = 2

if TYPE_CHECKING:
    from minitrino.context import MinitrinoContext


class LibraryManager:
    """Handles installation and management of Minitrino libraries."""

    def __init__(self, ctx: "MinitrinoContext"):
        self._ctx = ctx
        self.releases_url = "https://api.github.com/repos/jefflester/minitrino/releases"
        # Only use GITHUB_TOKEN in CI to avoid rate limits during testing.
        # Never use user's personal token without explicit consent.
        self._github_token = (
            os.getenv("GITHUB_TOKEN") if os.getenv("IS_GITHUB") == "true" else None
        )

    def _get_github_headers(self) -> dict:
        """Get headers for GitHub API requests with authentication.

        Note: Only uses GITHUB_TOKEN when running in CI (IS_GITHUB=true).
        This avoids using personal tokens without user consent.
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._github_token:
            headers["Authorization"] = f"Bearer {self._github_token}"
        return headers

    def install(self, version: str = "", _skip_confirm: bool = False) -> None:
        """Install or update the Minitrino library.

        If a library already exists at the destination, it is renamed
        aside as `lib.bak.<UTC timestamp>` rather than deleted, then
        replaced with the freshly downloaded version. On any failure
        during download or extract, the backup is restored. Successful
        installs prune older backups, retaining the most recent
        `BACKUP_RETENTION` (default: 2).
        """
        if not version:
            version = utils.cli_ver()

        self.validate(version)
        lib_dir = os.path.join(self._ctx.minitrino_user_dir, "lib")

        backup_path = ""
        if os.path.isdir(lib_dir):
            if not _skip_confirm and not self._ctx.effective_assume_yes:
                response = self._ctx.logger.prompt_msg(
                    f"The Minitrino library at {lib_dir} will be backed up "
                    f"and replaced with version {version}. Continue? [Y/N]"
                )
                if not utils.validate_yes(response):
                    self._ctx.logger.info("Opted to skip library installation.")
                    return
            backup_path = self._reserve_backup_path()
            self._ctx.logger.info(f"Backing up existing library to {backup_path}...")
            os.rename(lib_dir, backup_path)

        try:
            self.download_and_extract(version)
        except Exception:
            if backup_path and os.path.isdir(backup_path):
                self._ctx.logger.warn(
                    f"Install failed; restoring previous library from {backup_path}."
                )
                if os.path.isdir(lib_dir):
                    shutil.rmtree(lib_dir, ignore_errors=True)
                os.rename(backup_path, lib_dir)
            elif backup_path:
                self._ctx.logger.warn(
                    f"Install failed and the backup at {backup_path} is no "
                    "longer present; the previous library could not be restored."
                )
            raise

        self._prune_backups()
        self._clear_decline_cache()
        self._ctx.logger.info("Library installation complete.")

    def _reserve_backup_path(self) -> str:
        """Return a fresh, non-colliding `lib.bak.<ts>` directory path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        candidate = os.path.join(self._ctx.minitrino_user_dir, f"{BACKUP_PREFIX}{ts}")
        # Disambiguate if multiple installs land within a one-second window.
        suffix = 1
        while os.path.exists(candidate):
            candidate = os.path.join(
                self._ctx.minitrino_user_dir, f"{BACKUP_PREFIX}{ts}-{suffix}"
            )
            suffix += 1
        return candidate

    def _prune_backups(self, keep: int = BACKUP_RETENTION) -> None:
        """Remove old `lib.bak.*` directories, keeping the N newest by mtime.

        Best-effort: failures are logged but never raised. The freshly
        installed lib stays intact even if pruning hits trouble.
        """
        parent = self._ctx.minitrino_user_dir
        try:
            names = os.listdir(parent)
        except OSError:
            return
        backups = []
        for name in names:
            if not name.startswith(BACKUP_PREFIX):
                continue
            path = os.path.join(parent, name)
            if not os.path.isdir(path):
                continue
            backups.append((name, path))
        # Backup names embed a zero-padded UTC timestamp
        # (lib.bak.YYYYMMDD-HHMMSS[-N]), so a lexicographic sort orders
        # them chronologically. Sorting by filesystem mtime would be
        # wrong: tarball extraction preserves the release's mtime, so a
        # freshly created backup can carry an older timestamp than an
        # existing one and be pruned by mistake.
        backups.sort(reverse=True)
        for _, path in backups[keep:]:
            try:
                shutil.rmtree(path)
                self._ctx.logger.debug(f"Pruned old library backup: {path}")
            except OSError as e:
                self._ctx.logger.warn(f"Failed to prune library backup {path}: {e}")

    def list_releases(self) -> list[str]:
        """List all available releases from GitHub."""
        releases = []
        page = 1
        headers = self._get_github_headers()
        while True:
            resp = requests.get(
                self.releases_url,
                params={"per_page": 100, "page": page},
                headers=headers,
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
        tarball = os.path.join(self._ctx.minitrino_user_dir, f"{version}.tar.gz")
        file_basename = f"minitrino-{version}"
        extracted_lib_dir = os.path.join(
            self._ctx.minitrino_user_dir, file_basename, "src", "lib"
        )
        dest_lib_dir = os.path.join(self._ctx.minitrino_user_dir, "lib")

        try:
            self._download_file(uri, tarball)
            self._extract_tarball(tarball, self._ctx.minitrino_user_dir)
            if not os.path.isdir(extracted_lib_dir):
                raise MinitrinoError(
                    f"Expected library directory not found in downloaded "
                    f"archive: {extracted_lib_dir}"
                )
            shutil.move(extracted_lib_dir, dest_lib_dir)
        except MinitrinoError:
            self._cleanup(tarball, file_basename, False)
            raise
        except Exception as e:
            self._cleanup(tarball, file_basename, False)
            raise MinitrinoError(str(e)) from e

        # Removing the tarball and unpacked source tree is cosmetic; a
        # failure here must never trigger a rollback of the install that
        # already succeeded above, so swallow cleanup errors.
        self._cleanup(tarball, file_basename, trigger_error=False)

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

    def _decline_cache_path(self) -> str:
        return os.path.join(self._ctx.minitrino_user_dir, "lib_sync_state.json")

    def _read_decline_cache(self) -> dict | None:
        try:
            with open(self._decline_cache_path()) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def _write_decline_cache(self, cli_ver: str, lib_ver: str) -> None:
        payload = {
            "declined_at": datetime.now(timezone.utc).isoformat(),
            "cli_ver": cli_ver,
            "lib_ver": lib_ver,
        }
        with open(self._decline_cache_path(), "w") as f:
            json.dump(payload, f)

    def _decline_is_fresh(self, cache: dict, ttl_hours: int = 24) -> bool:
        try:
            declined_at = datetime.fromisoformat(cache["declined_at"])
            age = datetime.now(timezone.utc) - declined_at
            return age.total_seconds() < ttl_hours * 3600
        except (KeyError, ValueError, TypeError):
            return False

    def _clear_decline_cache(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self._decline_cache_path())

    def auto_install_or_update(self) -> None:
        """Check CLI/library version compatibility and auto-sync if needed.

        State machine:
        - Not installed → prompt (default Y). No → cache decline, raise UserError.
        - Installed, versions match → no-op (debug log).
        - Installed, mismatch, assume_yes → auto-install.
        - Installed, mismatch, fresh decline cache → skip prompt, debug note.
        - Installed, mismatch, stale/no cache → prompt. Yes → install; No → cache, warn.
        """
        cli_version = utils.cli_ver()
        # Accessing lib_dir raises UserError when no library is resolvable.
        # Treat that as "not installed" so the install prompt below is
        # reachable on a fresh machine rather than aborting with a bare error.
        try:
            lib_path = self._ctx.lib_dir
        except UserError:
            lib_path = ""
        lib_version = (
            utils.lib_ver(ctx=self._ctx, lib_path=lib_path)
            if lib_path
            else "NOT INSTALLED"
        )

        if lib_version == "NOT INSTALLED":
            if self._ctx.effective_assume_yes:
                self._ctx.logger.info(
                    f"Library not installed. Auto-installing version {cli_version}..."
                )
                self.install(version=cli_version)
                return
            cache = self._read_decline_cache()
            if cache and self._decline_is_fresh(cache):
                raise UserError(
                    "The Minitrino library is required for this operation.",
                    "Run 'minitrino lib-install' to install it manually.",
                )
            response = self._ctx.logger.prompt_msg(
                f"The Minitrino library is not installed. Install version "
                f"{cli_version} to "
                f"{self._ctx.minitrino_user_dir}/lib? [Y/N]"
            )
            if utils.validate_yes(response):
                self.install(version=cli_version)
            else:
                self._write_decline_cache(cli_version, lib_version)
                raise UserError(
                    "The Minitrino library is required for this operation.",
                    "Run 'minitrino lib-install' to install it manually.",
                )
            return

        if cli_version == lib_version:
            self._ctx.logger.debug(
                "CLI and library versions match. No action required."
            )
            return

        if self._ctx.effective_assume_yes:
            self._ctx.logger.info(
                f"Version mismatch (CLI {cli_version} vs lib "
                f"{lib_version}). Auto-syncing library..."
            )
            self.install(version=cli_version, _skip_confirm=True)
            return

        cache = self._read_decline_cache()
        if cache and self._decline_is_fresh(cache):
            self._ctx.logger.debug(
                f"Library sync declined recently (CLI {cli_version} vs "
                f"lib {lib_version}). Skipping prompt."
            )
            return

        response = self._ctx.logger.prompt_msg(
            f"CLI version {cli_version} does not match library version "
            f"{lib_version}. Sync library to {cli_version}? [Y/N]"
        )
        if utils.validate_yes(response):
            self.install(version=cli_version, _skip_confirm=True)
        else:
            self._write_decline_cache(cli_version, lib_version)
            self._ctx.logger.warn(
                "Mismatched CLI and library versions may cause errors. "
                "Run 'minitrino lib-install' to sync manually."
            )

    def _cleanup(
        self, tarball: str = "", file_basename: str = "", trigger_error: bool = True
    ) -> None:
        """Clean up downloaded and extracted files."""
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
                (
                    shutil.rmtree(unpacked_dir)
                    if os.path.isdir(unpacked_dir)
                    else os.remove(unpacked_dir)
                )
            except Exception as e:
                errors.append(f"Failed to remove directory {unpacked_dir}: {e}")

        if errors and trigger_error:
            raise MinitrinoError("\n".join(errors))
