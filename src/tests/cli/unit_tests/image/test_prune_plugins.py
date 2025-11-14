"""Unit tests for prune_plugins.py script."""

import os
import sys
from unittest.mock import call, patch

# Add the image scripts directory to path for imports dynamically
SCRIPT_PATH = os.path.realpath(__file__)
HERE = os.path.dirname(SCRIPT_PATH)
SCRIPTS_DIR = os.path.abspath(os.path.join(HERE, "../../../../lib/image/src/scripts"))
sys.path.insert(0, SCRIPTS_DIR)
from prune_plugins import main, prune_plugins  # noqa: E402


class TestPrunePlugins:
    """Test prune_plugins function."""

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_basic(self, mock_isdir, mock_listdir, mock_rmtree):
        """Test basic plugin pruning."""
        mock_isdir.return_value = True
        mock_listdir.return_value = [
            "hive",  # Keep - in the list
            "iceberg",  # Keep - in the list
            "mongodb",  # Remove - not in the list
            "redis",  # Remove - not in the list
            "memory",  # Keep - in the list
        ]

        prune_plugins("trino", None)

        # Should check if plugin dir exists
        mock_isdir.assert_called_once_with("/usr/lib/trino/plugin")

        # Should remove plugins not in the keep list
        expected_calls = [
            call("/usr/lib/trino/plugin/mongodb", ignore_errors=True),
            call("/usr/lib/trino/plugin/redis", ignore_errors=True),
        ]
        mock_rmtree.assert_has_calls(expected_calls, any_order=True)
        assert mock_rmtree.call_count == 2

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_with_keep_env(self, mock_isdir, mock_listdir, mock_rmtree):
        """Test plugin pruning with additional plugins to keep."""
        mock_isdir.return_value = True
        mock_listdir.return_value = [
            "hive",
            "mongodb",  # Would be removed, but added to keep list
            "redis",  # Would be removed, but added to keep list
            "custom",  # Not in default list, but added to keep list
        ]

        prune_plugins("starburst", "mongodb,redis custom")

        # Nothing should be removed since all are in the combined keep
        # list
        mock_rmtree.assert_not_called()

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_with_all(self, mock_isdir, mock_listdir, mock_rmtree):
        """Test plugin pruning with ALL specified."""
        mock_isdir.return_value = True
        mock_listdir.return_value = [
            "hive",
            "mongodb",
            "redis",
            "custom",
            "anything",
        ]

        prune_plugins("trino", "ALL")

        # Should check if plugin dir exists
        mock_isdir.assert_called_once_with("/usr/lib/trino/plugin")

        # Should not list directory or remove anything when ALL is
        # specified
        mock_listdir.assert_not_called()
        mock_rmtree.assert_not_called()

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_with_all_mixed_case(
        self, mock_isdir, mock_listdir, mock_rmtree
    ):
        """Test plugin pruning with ALL in different cases."""
        mock_isdir.return_value = True

        # Test various case combinations
        for keep_value in ["ALL", "all", "All", "  ALL  ", " all "]:
            prune_plugins("trino", keep_value)
            mock_listdir.assert_not_called()
            mock_rmtree.assert_not_called()
            mock_isdir.reset_mock()
            mock_listdir.reset_mock()
            mock_rmtree.reset_mock()

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_no_plugin_dir(self, mock_isdir, mock_listdir, mock_rmtree):
        """Test when plugin directory doesn't exist."""
        mock_isdir.return_value = False

        prune_plugins("trino", None)

        # Should check if plugin dir exists
        mock_isdir.assert_called_once_with("/usr/lib/trino/plugin")

        # Should not list or remove anything
        mock_listdir.assert_not_called()
        mock_rmtree.assert_not_called()

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_complex_keep_list(
        self, mock_isdir, mock_listdir, mock_rmtree
    ):
        """Test with complex keep list parsing."""
        mock_isdir.return_value = True
        mock_listdir.return_value = [
            "plugin1",
            "plugin2",
            "plugin3",
            "plugin4",
            "plugin5",
        ]

        # Complex format with commas, spaces, and mixed separators
        keep_env = "plugin1, plugin2  plugin3,plugin4,  plugin5"
        prune_plugins("trino", keep_env)

        # All plugins should be kept
        mock_rmtree.assert_not_called()

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_default_keep_list(
        self, mock_isdir, mock_listdir, mock_rmtree
    ):
        """Test that default keep list includes expected plugins."""
        mock_isdir.return_value = True

        # Test a subset of plugins that should be in the default keep
        # list
        default_plugins = [
            "hive",
            "iceberg",
            "delta-lake",
            "elasticsearch",
            "mysql",
            "postgresql",
            "clickhouse",
            "jmx",
            "memory",
            "tpch",
            "tpcds",
        ]

        mock_listdir.return_value = default_plugins + ["should-be-removed"]

        prune_plugins("trino", None)

        # Only the non-default plugin should be removed
        mock_rmtree.assert_called_once_with(
            "/usr/lib/trino/plugin/should-be-removed", ignore_errors=True
        )

    @patch("prune_plugins.shutil.rmtree")
    @patch("prune_plugins.os.listdir")
    @patch("prune_plugins.os.path.isdir")
    def test_prune_plugins_empty_keep_env(self, mock_isdir, mock_listdir, mock_rmtree):
        """Test with empty keep_plugins_env."""
        mock_isdir.return_value = True
        mock_listdir.return_value = ["hive", "not-in-list"]

        prune_plugins("trino", "")

        # Empty string should be treated as None
        mock_rmtree.assert_called_once_with(
            "/usr/lib/trino/plugin/not-in-list", ignore_errors=True
        )


class TestMain:
    """Test main function."""

    @patch("prune_plugins.prune_plugins")
    @patch("prune_plugins.os.environ.get")
    @patch("sys.argv", ["prune_plugins.py", "trino"])
    def test_main_no_args_no_env(self, mock_env_get, mock_prune):
        """Test main with no keep-plugins arg and no env var."""
        mock_env_get.return_value = None

        main()

        mock_prune.assert_called_once_with("trino", None)
        # Check that KEEP_PLUGINS was called (may be called multiple
        # times due to argparse)
        calls = [
            call
            for call in mock_env_get.call_args_list
            if call == (("KEEP_PLUGINS",), {})
        ]
        assert len(calls) >= 1

    @patch("prune_plugins.prune_plugins")
    @patch("prune_plugins.os.environ.get")
    @patch(
        "sys.argv",
        ["prune_plugins.py", "starburst", "--keep-plugins", "custom1,custom2"],
    )
    def test_main_with_cli_arg(self, mock_env_get, mock_prune):
        """Test main with keep-plugins CLI argument."""
        mock_env_get.return_value = "env-plugin"

        main()

        # CLI arg should take precedence over env var
        mock_prune.assert_called_once_with("starburst", "custom1,custom2")

    @patch("prune_plugins.prune_plugins")
    @patch("prune_plugins.os.environ.get")
    @patch("sys.argv", ["prune_plugins.py", "trino"])
    def test_main_with_env_var_only(self, mock_env_get, mock_prune):
        """Test main with only env var set."""
        mock_env_get.return_value = "env-plugin1,env-plugin2"

        main()

        mock_prune.assert_called_once_with("trino", "env-plugin1,env-plugin2")

    @patch("prune_plugins.prune_plugins")
    @patch("prune_plugins.os.environ.get")
    @patch("sys.argv", ["prune_plugins.py", "trino", "--keep-plugins", "ALL"])
    def test_main_with_all_arg(self, mock_env_get, mock_prune):
        """Test main with ALL as CLI argument."""
        mock_env_get.return_value = None

        main()

        mock_prune.assert_called_once_with("trino", "ALL")

    @patch("prune_plugins.prune_plugins")
    @patch("prune_plugins.os.environ.get")
    @patch("sys.argv", ["prune_plugins.py", "trino"])
    def test_main_with_all_env(self, mock_env_get, mock_prune):
        """Test main with ALL as env var."""
        mock_env_get.return_value = "ALL"

        main()

        mock_prune.assert_called_once_with("trino", "ALL")
