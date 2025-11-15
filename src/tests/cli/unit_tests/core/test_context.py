"""Unit tests for the MinitrinoContext class."""

import os
from unittest.mock import MagicMock, patch

import pytest
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.logging.levels import LogLevel


class TestMinitrinoContext:
    """Test suite for MinitrinoContext class."""

    def test_init(self):
        """Test MinitrinoContext initialization."""
        ctx = MinitrinoContext()

        # Check default values
        assert ctx.cluster_name == "default"
        assert ctx._user_env_args == []
        assert ctx._user_log_level == LogLevel.INFO
        assert ctx.all_clusters is False
        assert ctx.provisioned_clusters == []

        # Check paths
        assert ctx.user_home_dir == os.path.expanduser("~")
        assert ctx.minitrino_user_dir.endswith(".minitrino")
        assert ctx.config_file.endswith("minitrino.cfg")
        assert ctx.snapshot_dir.endswith("snapshots")

        # Check uninitialized state
        assert ctx._initialized is False
        assert ctx._lib_safe is False
        assert ctx.cluster is None
        assert ctx.env is None
        assert ctx.modules is None
        assert ctx.cmd_executor is None
        assert ctx.docker_client is None
        assert ctx.api_client is None

    @patch("minitrino.core.context.EnvironmentVariables")
    @patch("minitrino.core.context.Modules")
    @patch("minitrino.core.context.CommandExecutor")
    @patch("minitrino.core.context.Cluster")
    @patch("minitrino.core.context.resolve_docker_socket")
    @patch("minitrino.core.context.docker.DockerClient")
    @patch("minitrino.core.context.docker.APIClient")
    @patch("minitrino.core.context.utils")
    def test_initialize_normal(
        self,
        mock_utils,
        mock_api_client,
        mock_docker_client,
        mock_resolve_socket,
        mock_cluster_class,
        mock_cmd_executor_class,
        mock_modules_class,
        mock_env_vars_class,
    ):
        """Test normal initialization."""
        # Setup mocks
        mock_utils.cli_ver.return_value = "1.0.0"
        mock_utils.lib_ver.return_value = "1.0.0"
        mock_resolve_socket.return_value = "unix:///var/run/docker.sock"
        mock_env_instance = MagicMock()
        mock_env_instance.get.return_value = ""
        mock_env_instance.copy.return_value = {}
        mock_env_vars_class.return_value = mock_env_instance

        ctx = MinitrinoContext()

        with (
            patch.object(
                ctx, "_handle_minitrino_user_dir", return_value="/home/user/.minitrino"
            ),
            patch.object(ctx, "_validate_config_file"),
            patch.object(ctx, "_try_parse_library_env"),
            patch.object(ctx, "_compare_versions"),
            patch.object(ctx, "_get_lib_dir", return_value="/lib"),
        ):
            ctx.initialize(cluster_name="test-cluster")

        # Verify initialization
        assert ctx._initialized is True
        assert ctx._lib_safe is True
        assert ctx.env is not None
        assert ctx.modules is not None
        assert ctx.cmd_executor is not None
        assert ctx.cluster is not None
        assert ctx.docker_client is not None
        assert ctx.api_client is not None
        assert ctx.cluster_name == "test-cluster"

    def test_initialize_version_only(self):
        """Test initialization for version check only."""
        ctx = MinitrinoContext()

        with patch("minitrino.core.context.EnvironmentVariables") as mock_env_class:
            mock_env_instance = MagicMock()
            mock_env_class.return_value = mock_env_instance

            ctx.initialize(version_only=True)

            # Should only initialize env and set lib_safe
            assert ctx._lib_safe is True
            assert ctx.env is not None
            assert ctx._initialized is False  # Not fully initialized
            assert ctx.modules is None
            assert ctx.cmd_executor is None

    def test_initialize_already_initialized(self):
        """Test error when already initialized."""
        ctx = MinitrinoContext()
        ctx._initialized = True

        with pytest.raises(SystemExit) as exc_info:
            ctx.initialize()
        assert exc_info.value.code == 1

    def test_user_log_level_property(self):
        """Test user_log_level property."""
        ctx = MinitrinoContext()

        # Default value
        assert ctx.user_log_level == LogLevel.INFO

        # Set new value
        ctx.user_log_level = LogLevel.DEBUG
        assert ctx.user_log_level == LogLevel.DEBUG

        # Try to set again (should raise)
        with pytest.raises(MinitrinoError) as exc_info:
            ctx.user_log_level = LogLevel.ERROR
        assert "user_log_level is immutable once set" in str(exc_info.value)

    def test_lib_dir_property_not_safe(self):
        """Test lib_dir property before initialization."""
        ctx = MinitrinoContext()
        ctx._lib_safe = False

        with pytest.raises(MinitrinoError) as exc_info:
            _ = ctx.lib_dir
        assert "lib_dir accessed before initialization" in str(exc_info.value)

    def test_lib_dir_property_safe(self):
        """Test lib_dir property after initialization."""
        ctx = MinitrinoContext()
        ctx._lib_safe = True

        with patch.object(ctx, "_get_lib_dir", return_value="/path/to/lib"):
            assert ctx.lib_dir == "/path/to/lib"
            # Should cache the value
            assert ctx._lib_dir == "/path/to/lib"

    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_get_lib_dir_from_env(self, mock_isfile, mock_isdir):
        """Test getting lib directory from environment."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = "/custom/lib"
        mock_isdir.return_value = True
        mock_isfile.return_value = True

        result = ctx._get_lib_dir()

        assert result == "/custom/lib"
        ctx.env.get.assert_called_with("LIB_PATH", "")

    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_get_lib_dir_from_user_dir(self, mock_isfile, mock_isdir):
        """Test getting lib directory from user directory."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = ""
        ctx.minitrino_user_dir = "/home/user/.minitrino"

        def isdir_side_effect(path):
            return path == "/home/user/.minitrino/lib"

        mock_isdir.side_effect = isdir_side_effect
        mock_isfile.return_value = True

        result = ctx._get_lib_dir()

        assert result == "/home/user/.minitrino/lib"

    @patch("os.path.isdir")
    def test_get_lib_dir_not_found(self, mock_isdir):
        """Test error when lib directory not found."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = ""
        mock_isdir.return_value = False

        with pytest.raises(UserError) as exc_info:
            ctx._get_lib_dir()
        assert "requires a library to be installed" in str(exc_info.value)

    @patch("os.path.isdir")
    @patch("os.mkdir")
    def test_handle_minitrino_user_dir_create(self, mock_mkdir, mock_isdir):
        """Test creating minitrino user directory."""
        ctx = MinitrinoContext()
        ctx.user_home_dir = "/home/user"
        mock_isdir.return_value = False

        result = ctx._handle_minitrino_user_dir()

        assert result == "/home/user/.minitrino"
        mock_mkdir.assert_called_once_with("/home/user/.minitrino")

    @patch("os.path.isdir")
    def test_handle_minitrino_user_dir_exists(self, mock_isdir):
        """Test when minitrino user directory exists."""
        ctx = MinitrinoContext()
        ctx.user_home_dir = "/home/user"
        mock_isdir.return_value = True

        result = ctx._handle_minitrino_user_dir()

        assert result == "/home/user/.minitrino"

    @patch("os.path.isdir")
    @patch("os.mkdir")
    def test_handle_minitrino_user_dir_create_fails(self, mock_mkdir, mock_isdir):
        """Test error when creating directory fails."""
        ctx = MinitrinoContext()
        ctx.user_home_dir = "/home/user"
        mock_isdir.return_value = False
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(UserError) as exc_info:
            ctx._handle_minitrino_user_dir()
        assert "Failed to create the minitrino user directory" in str(exc_info.value)

    @patch("os.path.isfile")
    def test_validate_config_file_missing(self, mock_isfile):
        """Test validation when config file is missing."""
        ctx = MinitrinoContext()
        ctx.minitrino_user_dir = "/home/user/.minitrino"
        ctx.logger = MagicMock()
        mock_isfile.return_value = False

        ctx._validate_config_file()

        ctx.logger.warn.assert_called_once()
        assert "No minitrino.cfg file found" in ctx.logger.warn.call_args[0][0]
        assert ctx._logged_config_file_missing is True

    @patch("os.path.isfile")
    def test_validate_config_file_exists(self, mock_isfile):
        """Test validation when config file exists."""
        ctx = MinitrinoContext()
        ctx.minitrino_user_dir = "/home/user/.minitrino"
        ctx.logger = MagicMock()
        mock_isfile.return_value = True

        ctx._validate_config_file()

        ctx.logger.warn.assert_not_called()

    def test_config_file(self):
        """Test getting config file path."""
        ctx = MinitrinoContext()
        ctx.minitrino_user_dir = "/home/user/.minitrino"

        result = ctx._config_file()

        assert result == "/home/user/.minitrino/minitrino.cfg"

    def test_try_parse_library_env_success(self):
        """Test parsing library environment successfully."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()

        ctx._try_parse_library_env()

        ctx.env._parse_library_env.assert_called_once()

    def test_try_parse_library_env_failure(self):
        """Test parsing library environment with error."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env._parse_library_env.side_effect = Exception("Parse error")

        # Should not raise
        ctx._try_parse_library_env()

    @patch("minitrino.core.context.utils")
    def test_compare_versions_match(self, mock_utils):
        """Test version comparison when versions match."""
        ctx = MinitrinoContext()
        ctx.logger = MagicMock()
        ctx._lib_safe = True
        ctx._lib_dir = "/lib"

        mock_utils.cli_ver.return_value = "1.0.0"
        mock_utils.lib_ver.return_value = "1.0.0"

        ctx._compare_versions()

        ctx.logger.warn.assert_not_called()

    @patch("minitrino.core.context.utils")
    def test_compare_versions_mismatch(self, mock_utils):
        """Test version comparison when versions differ."""
        ctx = MinitrinoContext()
        ctx.logger = MagicMock()
        ctx._lib_safe = True
        ctx._lib_dir = "/lib"

        mock_utils.cli_ver.return_value = "1.0.0"
        mock_utils.lib_ver.return_value = "2.0.0"

        ctx._compare_versions()

        ctx.logger.warn.assert_called_once()
        assert "do not match" in ctx.logger.warn.call_args[0][0]

    @patch("minitrino.core.context.Cluster")
    def test_set_cluster_attrs(self, mock_cluster_class):
        """Test setting cluster attributes."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        mock_cluster = MagicMock()
        mock_cluster.resource.compose_project_name.return_value = "test_project"
        mock_cluster_class.return_value = mock_cluster

        with patch.object(ctx, "_set_cluster_name"):
            ctx._set_cluster_attrs("test-cluster")

        assert ctx.cluster == mock_cluster
        ctx.env.update.assert_called_with({"COMPOSE_PROJECT_NAME": "test_project"})

    def test_set_cluster_name_from_arg(self):
        """Test setting cluster name from argument."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = ""
        ctx.logger = MagicMock()
        ctx.cluster = MagicMock()

        ctx._set_cluster_name("my-cluster")

        assert ctx.cluster_name == "my-cluster"
        ctx.env.update.assert_called_with({"CLUSTER_NAME": "my-cluster"})
        ctx.cluster.validator.check_cluster_name.assert_called_once()

    def test_set_cluster_name_from_env(self):
        """Test setting cluster name from environment."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = "env-cluster"
        ctx.logger = MagicMock()
        ctx.cluster = MagicMock()

        ctx._set_cluster_name("")

        assert ctx.cluster_name == "env-cluster"

    def test_set_cluster_name_default(self):
        """Test setting default cluster name."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.env.get.return_value = ""
        ctx.logger = MagicMock()
        ctx.cluster = MagicMock()

        ctx._set_cluster_name("")

        assert ctx.cluster_name == "default"

    def test_set_cluster_name_all(self):
        """Test setting cluster name to 'all'."""
        ctx = MinitrinoContext()
        ctx.env = MagicMock()
        ctx.logger = MagicMock()
        ctx.cluster = MagicMock()

        ctx._set_cluster_name("all")

        assert ctx.cluster_name == "all"
        assert ctx.all_clusters is True

    @patch("minitrino.core.context.resolve_docker_socket")
    @patch("minitrino.core.context.docker.DockerClient")
    @patch("minitrino.core.context.docker.APIClient")
    def test_set_docker_clients_success(
        self, mock_api_client, mock_docker_client, mock_resolve_socket
    ):
        """Test setting Docker clients successfully."""
        ctx = MinitrinoContext()
        ctx.logger = MagicMock()

        mock_resolve_socket.return_value = "unix:///var/run/docker.sock"
        mock_docker_instance = MagicMock()
        mock_api_instance = MagicMock()
        mock_docker_client.return_value = mock_docker_instance
        mock_api_client.return_value = mock_api_instance

        ctx._set_docker_clients(env={})

        assert ctx.docker_client == mock_docker_instance
        assert ctx.api_client == mock_api_instance
        mock_resolve_socket.assert_called_once_with(ctx, {})

    @patch("minitrino.core.context.resolve_docker_socket")
    @patch("minitrino.core.context.cast")
    def test_set_docker_clients_failure(self, mock_cast, mock_resolve_socket):
        """Test setting Docker clients with failure."""
        ctx = MinitrinoContext()
        ctx.logger = MagicMock()

        mock_resolve_socket.side_effect = Exception("Socket error")
        mock_cast.return_value = object()

        ctx._set_docker_clients(env={})

        # Should set to empty objects
        assert ctx.docker_client is not None
        assert ctx.api_client is not None

    @patch("minitrino.core.context.EnvironmentVariables")
    @patch("minitrino.core.context.Modules")
    @patch("minitrino.core.context.CommandExecutor")
    @patch("minitrino.core.context.Cluster")
    @patch("minitrino.core.context.resolve_docker_socket")
    @patch("minitrino.core.context.docker")
    @patch("minitrino.core.context.utils")
    def test_initialize_with_log_level(
        self,
        mock_utils,
        mock_docker,
        mock_resolve_socket,
        mock_cluster_class,
        mock_cmd_executor_class,
        mock_modules_class,
        mock_env_vars_class,
    ):
        """Test initialization with custom log level."""
        # Setup mocks
        mock_utils.cli_ver.return_value = "1.0.0"
        mock_utils.lib_ver.return_value = "1.0.0"
        mock_resolve_socket.return_value = "unix:///var/run/docker.sock"
        mock_env_instance = MagicMock()
        mock_env_instance.get.return_value = ""
        mock_env_instance.copy.return_value = {}
        mock_env_vars_class.return_value = mock_env_instance

        ctx = MinitrinoContext()
        ctx.logger = MagicMock()

        with (
            patch.object(
                ctx, "_handle_minitrino_user_dir", return_value="/home/user/.minitrino"
            ),
            patch.object(ctx, "_validate_config_file"),
            patch.object(ctx, "_try_parse_library_env"),
            patch.object(ctx, "_compare_versions"),
            patch.object(ctx, "_get_lib_dir", return_value="/lib"),
        ):
            ctx.initialize(log_level=LogLevel.DEBUG)

        ctx.logger.set_level.assert_called_once_with(LogLevel.DEBUG)

    @patch("os.path.expanduser")
    def test_init_with_custom_home(self, mock_expanduser):
        """Test initialization with custom home directory."""
        mock_expanduser.return_value = "/custom/home"

        with patch.object(
            MinitrinoContext,
            "_handle_minitrino_user_dir",
            return_value="/custom/home/.minitrino",
        ):
            ctx = MinitrinoContext()

        assert ctx.user_home_dir == "/custom/home"
        assert ctx.minitrino_user_dir == "/custom/home/.minitrino"

    def test_logger_attribute(self):
        """Test logger attribute is properly set."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            ctx = MinitrinoContext()

            assert ctx.logger == mock_logger
            mock_get_logger.assert_called_once_with("minitrino")
