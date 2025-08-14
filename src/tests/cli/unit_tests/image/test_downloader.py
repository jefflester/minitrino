"""Unit tests for the downloader script."""

import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add the scripts directory to the path
sys.path.insert(0, "/Users/jlester/work/repos/minitrino/src/lib/image/src/scripts")

from downloader import (  # noqa: E402
    download_tarball,
    get_arch,
    main,
    resolve_tarball_info,
    unpack_and_copy,
    unpack_tarball,
)


class TestGetArch:
    """Test suite for get_arch function."""

    @patch("platform.machine")
    def test_get_arch_x86_64(self, mock_machine):
        """Test architecture detection for x86_64."""
        mock_machine.return_value = "x86_64"

        arch_sep, arch_bin = get_arch()

        assert arch_sep == "x86_64"
        assert arch_bin == "amd64"

    @patch("platform.machine")
    def test_get_arch_amd64(self, mock_machine):
        """Test architecture detection for amd64."""
        mock_machine.return_value = "amd64"

        arch_sep, arch_bin = get_arch()

        assert arch_sep == "x86_64"
        assert arch_bin == "amd64"

    @patch("platform.machine")
    def test_get_arch_arm64(self, mock_machine):
        """Test architecture detection for arm64."""
        mock_machine.return_value = "arm64"

        arch_sep, arch_bin = get_arch()

        assert arch_sep == "aarch64"
        assert arch_bin == "arm64"

    @patch("platform.machine")
    def test_get_arch_aarch64(self, mock_machine):
        """Test architecture detection for aarch64."""
        mock_machine.return_value = "aarch64"

        arch_sep, arch_bin = get_arch()

        assert arch_sep == "aarch64"
        assert arch_bin == "arm64"

    @patch("platform.machine")
    def test_get_arch_unsupported(self, mock_machine):
        """Test unsupported architecture raises error."""
        mock_machine.return_value = "powerpc"

        with pytest.raises(RuntimeError) as exc_info:
            get_arch()
        assert "Unsupported architecture: powerpc" in str(exc_info.value)


class TestResolveTarballInfo:
    """Test suite for resolve_tarball_info function."""

    @patch("downloader.get_arch")
    def test_resolve_trino(self, mock_get_arch):
        """Test resolving Trino tarball info."""
        mock_get_arch.return_value = ("x86_64", "amd64")

        url, tar_name, unpack_dir, arch_bin = resolve_tarball_info("trino", "443")

        assert url == (  # noqa: E501
            "https://repo1.maven.org/maven2/io/trino/"
            "trino-server/443/trino-server-443.tar.gz"
        )
        assert tar_name == "trino-server-443.tar.gz"
        assert unpack_dir == "trino-server-443"
        assert arch_bin == "amd64"

    @patch("downloader.get_arch")
    def test_resolve_starburst_new_version(self, mock_get_arch):
        """Test resolving Starburst tarball info for version >= 462."""
        mock_get_arch.return_value = ("aarch64", "arm64")

        url, tar_name, unpack_dir, arch_bin = resolve_tarball_info(
            "starburst", "462-e.0"
        )

        assert url == (  # noqa: E501
            "https://s3.us-east-2.amazonaws.com/software.starburstdata.net/"
            "462e/462-e.0/starburst-enterprise-462-e.0.aarch64.tar.gz"
        )
        assert tar_name == "starburst-enterprise-462-e.0.aarch64.tar.gz"
        assert unpack_dir == "starburst-enterprise-462-e.0-aarch64"
        assert arch_bin == "arm64"

    @patch("downloader.get_arch")
    def test_resolve_starburst_old_version(self, mock_get_arch):
        """Test resolving Starburst tarball info for version < 462."""
        mock_get_arch.return_value = ("x86_64", "amd64")

        url, tar_name, unpack_dir, arch_bin = resolve_tarball_info(
            "starburst", "438-e.12"
        )

        assert url == (  # noqa: E501
            "https://s3.us-east-2.amazonaws.com/software.starburstdata.net/"
            "438e/438-e.12/starburst-enterprise-438-e.12.tar.gz"
        )
        assert tar_name == "starburst-enterprise-438-e.12.tar.gz"
        assert unpack_dir == "starburst-enterprise-438-e.12"
        assert arch_bin == "amd64"

    @patch("downloader.get_arch")
    def test_resolve_invalid_dist(self, mock_get_arch):
        """Test invalid distribution raises error."""
        mock_get_arch.return_value = ("x86_64", "amd64")

        with pytest.raises(RuntimeError) as exc_info:
            resolve_tarball_info("invalid", "443")
        assert "Invalid cluster distribution" in str(exc_info.value)


class TestDownloadTarball:
    """Test suite for download_tarball function."""

    @patch("urllib.request.urlopen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("time.time")
    @patch("builtins.print")
    def test_download_with_content_length(
        self, mock_print, mock_time, mock_file, mock_urlopen
    ):
        """Test downloading tarball with Content-Length header."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.getheader.return_value = "1024"  # 1KB
        mock_response.read.side_effect = [b"x" * 512, b"x" * 512, b""]  # Two chunks
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock time for progress updates
        mock_time.side_effect = [0, 3, 6]  # Trigger print on second iteration

        download_tarball("http://example.com/file.tar.gz", "/tmp/file.tar.gz")

        # Verify file was opened for writing
        mock_file.assert_called_once_with("/tmp/file.tar.gz", "wb")

        # Verify data was written
        mock_file().write.assert_called()
        assert mock_file().write.call_count == 2

        # Verify progress messages
        mock_print.assert_any_call(
            "[downloader] Downloading http://example.com/file.tar.gz ..."
        )
        mock_print.assert_any_call(
            "[downloader] Downloading tarball... 100.0% complete"
        )

    @patch("urllib.request.urlopen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("time.time")
    @patch("builtins.print")
    def test_download_without_content_length(
        self, mock_print, mock_time, mock_file, mock_urlopen
    ):
        """Test downloading tarball without Content-Length header."""
        mock_response = MagicMock()
        mock_response.getheader.return_value = None
        mock_response.read.side_effect = [b"x" * 8192, b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        mock_time.side_effect = [0, 3]

        download_tarball("http://example.com/file.tar.gz", "/tmp/file.tar.gz")

        mock_file().write.assert_called_once_with(b"x" * 8192)


class TestUnpackTarball:
    """Test suite for unpack_tarball function."""

    @patch("tarfile.open")
    @patch("builtins.print")
    def test_unpack_tarball(self, mock_print, mock_tarfile):
        """Test unpacking a tarball."""
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        unpack_tarball("/tmp/file.tar.gz", "/dest/dir")

        mock_tarfile.assert_called_once_with("/tmp/file.tar.gz", "r:gz")
        mock_tar.extractall.assert_called_once_with(path="/dest/dir")
        mock_print.assert_any_call("[downloader] Extracting /tmp/file.tar.gz ...")
        mock_print.assert_any_call("[downloader] Extracted to /dest/dir")


class TestUnpackAndCopy:
    """Test suite for unpack_and_copy function."""

    @patch("os.makedirs")
    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    @patch("shutil.rmtree")
    @patch("shutil.copytree")
    @patch("shutil.copy2")
    @patch("os.remove")
    @patch("builtins.print")
    def test_unpack_and_copy_trino(
        self,
        mock_print,
        mock_remove,
        mock_copy2,
        mock_copytree,
        mock_rmtree,
        mock_exists,
        mock_isdir,
        mock_listdir,
        mock_makedirs,
    ):
        """Test unpacking and copying Trino files."""
        # Setup directory structure
        mock_listdir.side_effect = [
            ["bin", "lib", "plugin"],  # unpack_dir contents
            ["launcher", "darwin-amd64", "linux-amd64", "linux-arm64"],  # bin contents
        ]

        # Setup path checks
        mock_isdir.side_effect = [
            True,  # bin is dir
            True,  # lib is dir
            True,  # plugin is dir
            True,  # darwin-amd64 is dir
            True,  # linux-amd64 is dir
            True,  # linux-arm64 is dir
            False,  # src linux-amd64 doesn't exist
        ]

        mock_exists.side_effect = [True, True, True, True, True]  # Dirs exist checks

        unpack_and_copy("trino", "/tmp/trino-server-443", "amd64")

        # Verify destination directory was created
        mock_makedirs.assert_called_once_with("/usr/lib/trino", exist_ok=True)

        # Verify files were copied
        assert mock_copytree.call_count >= 2

        # Verify unwanted binaries were removed
        mock_rmtree.assert_any_call(
            "/usr/lib/trino/bin/darwin-amd64", ignore_errors=True
        )
        mock_rmtree.assert_any_call(
            "/usr/lib/trino/bin/linux-arm64", ignore_errors=True
        )

    @patch("downloader.os.makedirs")
    @patch("downloader.os.listdir")
    @patch("downloader.os.path.isdir")
    @patch("downloader.shutil.copy2")
    def test_unpack_and_copy_single_file(
        self, mock_copy2, mock_isdir, mock_listdir, mock_makedirs
    ):
        """Test copying single file."""
        mock_listdir.side_effect = [
            ["config.properties"],  # unpack_dir contents
            [],  # bin contents (empty)
        ]
        mock_isdir.side_effect = [
            False,
            False,
        ]  # config.properties is not a dir, bin check

        unpack_and_copy("trino", "/tmp/unpack", "amd64")

        mock_copy2.assert_called_once_with(
            "/tmp/unpack/config.properties", "/usr/lib/trino/config.properties"
        )


class TestMain:
    """Test suite for main function."""

    @patch("downloader.resolve_tarball_info")
    @patch("downloader.download_tarball")
    @patch("downloader.unpack_tarball")
    @patch("downloader.unpack_and_copy")
    @patch("downloader.os.chdir")
    def test_main(
        self,
        mock_chdir,
        mock_unpack_copy,
        mock_unpack,
        mock_download,
        mock_resolve,
    ):
        """Test main function orchestration."""
        mock_resolve.return_value = (
            "http://example.com/file.tar.gz",
            "file.tar.gz",
            "unpack_dir",
            "amd64",
        )

        main("443", "trino")

        mock_resolve.assert_called_once_with("trino", "443")
        mock_download.assert_called_once_with(
            "http://example.com/file.tar.gz", "/tmp/file.tar.gz"
        )
        mock_chdir.assert_called_once_with("/tmp")
        mock_unpack.assert_called_once_with("/tmp/file.tar.gz", "/tmp")
        mock_unpack_copy.assert_called_once_with("trino", "unpack_dir", "amd64")

    @patch("sys.argv", ["downloader.py"])
    @patch("downloader.os.environ", {"CLUSTER_DIST": "trino", "CLUSTER_VERSION": "443"})
    @patch("downloader.unpack_and_copy")
    @patch("downloader.unpack_tarball")
    @patch("downloader.download_tarball")
    @patch("downloader.resolve_tarball_info")
    @patch("downloader.os.chdir")
    def test_main_cli(
        self, mock_chdir, mock_resolve, mock_download, mock_unpack, mock_copy
    ):
        """Test main function with CLI execution."""
        mock_resolve.return_value = (
            "http://example.com/file.tar.gz",
            "file.tar.gz",
            "unpack_dir",
            "amd64",
        )

        # main() requires version and dist arguments from env vars
        main("443", "trino")

        mock_resolve.assert_called_once_with("trino", "443")
        mock_download.assert_called_once()
        mock_unpack.assert_called_once()
        mock_copy.assert_called_once()
