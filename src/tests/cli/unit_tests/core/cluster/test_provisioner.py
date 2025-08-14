"""Unit tests for the ClusterProvisioner class."""

import threading
from unittest.mock import MagicMock, mock_open, patch

import pytest
from docker.errors import NotFound

from minitrino.core.cluster.provisioner import ClusterProvisioner
from minitrino.core.errors import MinitrinoError, UserError


class TestClusterProvisioner:
    """Test suite for ClusterProvisioner class."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MinitrinoContext."""
        ctx = MagicMock()
        ctx.all_clusters = False
        ctx.cluster_name = "test-cluster"
        ctx.provisioned_clusters = []
        ctx.minitrino_user_dir = "/home/user/.minitrino"
        ctx.lib_dir = "/usr/local/lib/minitrino"
        ctx.env = {
            "CLUSTER_DIST": "trino",
            "CLUSTER_VER": "443",
            "IMAGE": "trino",
            "LIC_PATH": "",
        }
        ctx.logger = MagicMock()
        ctx.logger._log_sink = MagicMock()
        ctx.logger._log_sink.buffer = []
        ctx.logger.spinner = MagicMock()
        ctx.docker_client = MagicMock()
        ctx.modules = MagicMock()
        ctx.modules.data = {}
        ctx.modules.running_modules.return_value = {}
        ctx.modules.check_dep_modules.side_effect = lambda x: x
        ctx.cluster = MagicMock()
        ctx.cluster.validator = MagicMock()
        ctx.cluster.validator.check_dependent_clusters.return_value = []
        ctx.cluster.ports = MagicMock()
        ctx.cluster.ops = MagicMock()
        ctx.cluster.resource = MagicMock()
        ctx.cluster.resource.compose_project_name.return_value = "test_project"
        ctx.cluster.resource.fq_container_name.return_value = "test-cluster-minitrino"
        ctx.cmd_executor = MagicMock()
        ctx.cmd_executor.stream_execute.return_value = iter(["line1", "line2"])
        return ctx

    @pytest.fixture
    def mock_cluster(self):
        """Create a mock Cluster."""
        return MagicMock()

    @pytest.fixture
    def provisioner(self, mock_ctx, mock_cluster):
        """Create a ClusterProvisioner instance."""
        return ClusterProvisioner(mock_ctx, mock_cluster)

    def test_init(self, mock_ctx, mock_cluster):
        """Test ClusterProvisioner initialization."""
        provisioner = ClusterProvisioner(mock_ctx, mock_cluster)
        assert provisioner._ctx == mock_ctx
        assert provisioner._cluster == mock_cluster
        assert provisioner.modules == []
        assert provisioner.image == "trino"
        assert provisioner.workers == 0
        assert provisioner.no_rollback is False
        assert provisioner.build is False
        assert isinstance(provisioner._worker_safe_event, threading.Event)
        assert provisioner._dep_cluster_env == {}

    @patch("minitrino.core.cluster.provisioner.utils")
    def test_provision_success(self, mock_utils, provisioner, mock_ctx):
        """Test successful provisioning."""
        # Mock dependencies
        provisioner._set_license = MagicMock()
        provisioner._set_distribution = MagicMock()
        provisioner._determine_build = MagicMock(return_value=False)
        provisioner._append_running_modules = MagicMock(return_value=["module1"])
        provisioner._ensure_shared_network = MagicMock()
        provisioner._runner = MagicMock()
        provisioner._record_image_src_checksum = MagicMock()

        # Call provision
        provisioner.provision(
            modules=["module1"], image="trino", workers=2, no_rollback=False
        )

        # Verify calls
        mock_utils.check_daemon.assert_called_once_with(mock_ctx.docker_client)
        mock_utils.check_lib.assert_called_once_with(mock_ctx)
        provisioner._set_license.assert_called_once()
        provisioner._set_distribution.assert_called_once()
        provisioner._determine_build.assert_called_once()
        provisioner._ensure_shared_network.assert_called_once()
        provisioner._runner.assert_called()
        provisioner._record_image_src_checksum.assert_called_once()
        mock_ctx.logger.info.assert_any_call("Environment provisioning complete.")

    def test_provision_all_clusters_error(self, provisioner, mock_ctx):
        """Test provision raises error for all_clusters."""
        mock_ctx.all_clusters = True

        with pytest.raises(UserError) as exc_info:
            provisioner.provision([], "trino", 0, False)
        assert "cannot interact with multiple/all clusters" in str(exc_info.value)

    @patch("minitrino.core.cluster.provisioner.utils")
    def test_provision_with_dependent_clusters(self, mock_utils, provisioner, mock_ctx):
        """Test provisioning with dependent clusters."""
        # Setup
        dependent_cluster = {"name": "dep-cluster", "modules": ["dep-module"]}
        mock_ctx.cluster.validator.check_dependent_clusters.return_value = [
            dependent_cluster
        ]
        provisioner._set_license = MagicMock()
        provisioner._set_distribution = MagicMock()
        provisioner._determine_build = MagicMock(return_value=False)
        provisioner._append_running_modules = MagicMock(return_value=[])
        provisioner._ensure_shared_network = MagicMock()
        provisioner._runner = MagicMock()
        provisioner._record_image_src_checksum = MagicMock()

        # Call provision
        provisioner.provision([], "trino", 0, False)

        # Verify _runner called for main and dependent cluster
        assert provisioner._runner.call_count == 2
        provisioner._runner.assert_any_call()  # Main cluster
        provisioner._runner.assert_any_call(cluster=dependent_cluster)

    @patch("minitrino.core.cluster.provisioner.utils")
    def test_provision_rollback_on_error(self, mock_utils, provisioner, mock_ctx):
        """Test rollback on provisioning error."""
        # Setup error
        provisioner._set_license = MagicMock()
        provisioner._set_distribution = MagicMock()
        provisioner._determine_build = MagicMock(return_value=False)
        provisioner._append_running_modules = MagicMock(return_value=[])
        provisioner._ensure_shared_network = MagicMock()
        provisioner._runner = MagicMock(side_effect=Exception("Test error"))
        provisioner._rollback = MagicMock()

        # Call provision
        with pytest.raises(MinitrinoError):
            provisioner.provision([], "trino", 0, False)

        # Verify rollback was called
        provisioner._rollback.assert_called_once()
        mock_ctx.logger.error.assert_any_call(
            "Provisioning failed. Rolling back all provisioned clusters..."
        )

    def test_set_distribution_valid(self, provisioner, mock_ctx):
        """Test setting valid distribution."""
        provisioner.image = "starburst"
        provisioner._set_distribution()

        assert mock_ctx.env["CLUSTER_DIST"] == "starburst"
        assert mock_ctx.env["SERVICE_USER"] == "starburst"
        assert mock_ctx.env["ETC"] == "/etc/starburst"

    def test_set_distribution_invalid(self, provisioner):
        """Test setting invalid distribution raises error."""
        provisioner.image = "invalid"

        with pytest.raises(UserError) as exc_info:
            provisioner._set_distribution()
        assert "Invalid image type 'invalid'" in str(exc_info.value)

    def test_ensure_shared_network_exists(self, provisioner, mock_ctx):
        """Test ensuring shared network when it exists."""
        mock_network = MagicMock()
        mock_ctx.docker_client.networks.get.return_value = mock_network

        provisioner._ensure_shared_network()

        mock_ctx.docker_client.networks.get.assert_called_once_with("cluster_shared")
        mock_ctx.docker_client.networks.create.assert_not_called()

    def test_ensure_shared_network_creates(self, provisioner, mock_ctx):
        """Test creating shared network when it doesn't exist."""
        mock_ctx.docker_client.networks.get.side_effect = NotFound("Not found")

        provisioner._ensure_shared_network()

        mock_ctx.docker_client.networks.create.assert_called_once_with(
            name="cluster_shared",
            driver="bridge",
            labels={
                "org.minitrino.root": "true",
                "org.minitrino.module.minitrino": "true",
                "com.docker.compose.project": "minitrino-system",
            },
        )

    def test_append_running_modules(self, provisioner, mock_ctx):
        """Test appending running modules."""
        mock_ctx.modules.running_modules.return_value = {
            "running1": {},
            "running2": {},
        }

        result = provisioner._append_running_modules(["new1", "new2"])

        assert set(result) == {"new1", "new2", "running1", "running2"}

    def test_module_yaml_paths(self, provisioner, mock_ctx):
        """Test getting module YAML paths."""
        provisioner.modules = ["module1", "module2"]
        mock_ctx.modules.data = {
            "module1": {"yaml_file": "/path/to/module1.yaml"},
            "module2": {"yaml_file": "/path/to/module2.yaml"},
        }

        paths = provisioner._module_yaml_paths()

        expected = [
            "/usr/local/lib/minitrino/docker-compose.yaml",
            "/path/to/module1.yaml",
            "/path/to/module2.yaml",
        ]
        assert paths == expected

    @patch("shutil.which")
    def test_resolve_compose_bin_docker(self, mock_which):
        """Test resolving Docker Compose with docker binary."""
        mock_which.side_effect = lambda x: "/usr/bin/docker" if x == "docker" else None

        provisioner = ClusterProvisioner(MagicMock(), MagicMock())
        bin_path, args = provisioner._resolve_compose_bin()

        assert bin_path == "/usr/bin/docker"
        assert args == ["compose"]

    @patch("shutil.which")
    def test_resolve_compose_bin_docker_compose(self, mock_which):
        """Test resolving Docker Compose with docker-compose binary."""
        mock_which.side_effect = lambda x: (
            "/usr/bin/docker-compose" if x == "docker-compose" else None
        )

        provisioner = ClusterProvisioner(MagicMock(), MagicMock())
        bin_path, args = provisioner._resolve_compose_bin()

        assert bin_path == "/usr/bin/docker-compose"
        assert args == []

    @patch("shutil.which")
    def test_resolve_compose_bin_not_found(self, mock_which):
        """Test error when neither docker nor docker-compose found."""
        mock_which.return_value = None

        provisioner = ClusterProvisioner(MagicMock(), MagicMock())
        with pytest.raises(MinitrinoError) as exc_info:
            provisioner._resolve_compose_bin()
        assert "Neither 'docker' nor 'docker-compose' was found" in str(exc_info.value)

    def test_build_compose_command(self, provisioner):
        """Test building Docker Compose command."""
        provisioner._resolve_compose_bin = MagicMock(
            return_value=("/usr/bin/docker", ["compose"])
        )
        provisioner.build = True

        cmd = provisioner._build_compose_command(["/path/module1.yaml"])

        expected = [
            "/usr/bin/docker",
            "compose",
            "-f",
            "/path/module1.yaml",
            "up",
            "-d",
            "--force-recreate",
            "--build",
        ]
        assert cmd == expected

    def test_module_string(self, provisioner):
        """Test getting comma-separated module string."""
        provisioner.modules = ["module1", "module2", "module3"]
        assert provisioner._module_string() == "module1,module2,module3"

    def test_set_env_vars(self, provisioner, mock_ctx):
        """Test setting environment variables."""
        provisioner.workers = 3
        provisioner.modules = ["module1", "module2"]

        provisioner._set_env_vars()

        assert mock_ctx.env["WORKERS"] == "3"
        assert mock_ctx.env["CLUSTER_NAME"] == "test-cluster"
        assert mock_ctx.env["MINITRINO_MODULES"] == "module1,module2"
        assert mock_ctx.env["COMPOSE_PROJECT_NAME"] == "test_project"

    def test_set_license_valid_path(self, provisioner, mock_ctx):
        """Test setting valid license path."""
        mock_ctx.env["LIC_PATH"] = "~/license.txt"

        with patch("os.path.isfile", return_value=True):
            with patch("os.path.expanduser", return_value="/home/user/license.txt"):
                with patch("os.path.abspath", return_value="/home/user/license.txt"):
                    provisioner._set_license()

        assert mock_ctx.env["LIC_PATH"] == "/home/user/license.txt"

    def test_set_license_invalid_path(self, provisioner, mock_ctx):
        """Test setting invalid license path raises error."""
        mock_ctx.env["LIC_PATH"] = "invalid/path"

        with patch("os.path.isfile", return_value=False):
            with pytest.raises(UserError) as exc_info:
                provisioner._set_license()
            assert "Failed to resolve valid license path" in str(exc_info.value)

    @patch("os.walk")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test content")
    def test_get_image_src_checksum(self, mock_file, mock_walk, provisioner, mock_ctx):
        """Test getting image source checksum."""
        mock_walk.return_value = [
            ("/usr/local/lib/minitrino/image", [], ["Dockerfile", "script.sh"])
        ]

        with patch("os.path.isfile", return_value=True):
            with patch("os.path.islink", return_value=False):
                checksum = provisioner._get_image_src_checksum()

        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex digest length

    def test_image_src_changed_no_file(self, provisioner, mock_ctx):
        """Test image source changed when no checksum file exists."""
        provisioner._image_src_checksum = "abc123"

        with patch("os.path.isdir", return_value=True):
            with patch("os.path.isfile", return_value=False):
                result = provisioner._image_src_changed()

        assert result is True

    def test_image_src_changed_different_checksum(self, provisioner, mock_ctx):
        """Test image source changed when checksum differs."""
        provisioner._image_src_checksum = "abc123"

        with patch("os.path.isdir", return_value=True):
            with patch("os.path.isfile", return_value=True):
                with patch("builtins.open", mock_open(read_data="def456")):
                    result = provisioner._image_src_changed()

        assert result is True

    def test_image_src_changed_same_checksum(self, provisioner, mock_ctx):
        """Test image source not changed when checksum matches."""
        provisioner._image_src_checksum = "abc123"

        with patch("os.path.isdir", return_value=True):
            with patch("os.path.isfile", return_value=True):
                with patch("builtins.open", mock_open(read_data="abc123")):
                    result = provisioner._image_src_changed()

        assert result is False

    def test_record_image_src_checksum(self, provisioner, mock_ctx):
        """Test recording image source checksum."""
        provisioner._image_src_checksum = "abc123"
        provisioner.checksum_file = "/path/to/checksum"

        with patch("builtins.open", mock_open()) as mock_file:
            provisioner._record_image_src_checksum()

        mock_file.assert_called_once_with("/path/to/checksum", "w")
        mock_file().write.assert_called_once_with("abc123")

    def test_rollback_enabled(self, provisioner, mock_ctx):
        """Test rollback when enabled."""
        provisioner.no_rollback = False
        mock_ctx.provisioned_clusters = ["cluster1", "cluster2"]

        provisioner._rollback()

        assert mock_ctx.cluster.ops.rollback.call_count == 2

    def test_rollback_disabled(self, provisioner, mock_ctx):
        """Test rollback when disabled."""
        provisioner.no_rollback = True

        provisioner._rollback()

        mock_ctx.cluster.ops.rollback.assert_not_called()
        mock_ctx.logger.warn.assert_called_once()

    def test_provision_workers_when_safe(self, provisioner, mock_ctx):
        """Test provisioning workers when safe."""
        provisioner.workers = 3
        provisioner._worker_safe_event.set()

        # Run in thread and wait
        thread = threading.Thread(target=provisioner._provision_workers_when_safe)
        thread.start()
        thread.join(timeout=1)

        mock_ctx.cluster.ops.reconcile_workers.assert_called_once_with(3)

    def test_wait_for_coordinator_container_success(self, provisioner, mock_ctx):
        """Test waiting for coordinator container successfully."""
        mock_container = MagicMock()
        mock_container.id = "container123"
        mock_container.status = "running"
        mock_container.logs.return_value = b"- CLUSTER IS READY -"
        mock_ctx.cluster.resource.container.return_value = mock_container

        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False

        provisioner._wait_for_coordinator_container(None, mock_thread, timeout=5)

        # Should complete without error
        assert provisioner._worker_safe_event.is_set() is False

    def test_wait_for_coordinator_container_timeout(self, provisioner, mock_ctx):
        """Test timeout waiting for coordinator container."""
        mock_ctx.cluster.resource.container.side_effect = NotFound("Not found")

        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True

        with pytest.raises(MinitrinoError) as exc_info:
            provisioner._wait_for_coordinator_container(None, mock_thread, timeout=1)
        assert "Timed out after" in str(exc_info.value)

    def test_wait_for_coordinator_container_exited(self, provisioner, mock_ctx):
        """Test container exited with error."""
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_container.attrs = {"State": {"ExitCode": 1}}
        mock_ctx.cluster.resource.container.return_value = mock_container

        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False

        with pytest.raises(MinitrinoError) as exc_info:
            provisioner._wait_for_coordinator_container(None, mock_thread, timeout=5)
        assert "Coordinator container exited with code 1" in str(exc_info.value)

    @patch("minitrino.core.cluster.provisioner.shutdown_event")
    def test_wait_for_coordinator_container_shutdown(
        self, mock_shutdown, provisioner, mock_ctx
    ):
        """Test shutdown event during wait."""
        mock_shutdown.is_set.return_value = True

        mock_thread = MagicMock()

        # Should return without error
        provisioner._wait_for_coordinator_container(None, mock_thread, timeout=5)
        mock_ctx.logger.warn.assert_called_with(
            "Shutdown event detected, aborting compose wait."
        )

    def test_run_compose_and_wait_success(self, provisioner, mock_ctx):
        """Test successful compose run and wait."""
        provisioner.build = False
        provisioner._wait_for_coordinator_container = MagicMock()

        mock_container = MagicMock()
        mock_container.id = "original_id"
        mock_ctx.cluster.resource.container.return_value = mock_container

        compose_cmd = ["docker", "compose", "up"]
        provisioner._run_compose_and_wait(compose_cmd)

        # Verify stream_execute was called
        mock_ctx.cmd_executor.stream_execute.assert_called_once()
        provisioner._wait_for_coordinator_container.assert_called_once()

    def test_run_compose_and_wait_compose_failure(self, provisioner, mock_ctx):
        """Test compose command failure."""
        provisioner.build = False
        mock_ctx.cmd_executor.stream_execute.side_effect = Exception("Compose failed")

        compose_cmd = ["docker", "compose", "up"]

        with pytest.raises(MinitrinoError) as exc_info:
            provisioner._run_compose_and_wait(compose_cmd)
        assert "Docker Compose command failed" in str(exc_info.value)

    def test_runner_main_cluster(self, provisioner, mock_ctx):
        """Test _runner for main cluster."""
        provisioner.modules = ["module1"]
        provisioner.workers = 2
        provisioner._set_env_vars = MagicMock()
        provisioner._module_yaml_paths = MagicMock(return_value=[])
        provisioner._build_compose_command = MagicMock(return_value=["docker", "up"])
        provisioner._run_compose_and_wait = MagicMock()
        provisioner._provision_workers_when_safe = MagicMock()

        provisioner._runner()

        # Verify cluster name added to provisioned list
        assert "test-cluster" in mock_ctx.provisioned_clusters
        # Verify various checks were called
        mock_ctx.modules.check_enterprise.assert_called_once()
        mock_ctx.modules.check_compatibility.assert_called_once()
        mock_ctx.modules.check_volumes.assert_called_once()
        mock_ctx.cluster.ports.set_external_ports.assert_called_once_with(["module1"])

    def test_runner_dependent_cluster(self, provisioner, mock_ctx):
        """Test _runner for dependent cluster."""
        dependent_cluster = {
            "name": "dep-cluster",
            "modules": ["dep-module"],
            "workers": 1,
            "env": {"KEY": "VALUE"},
        }

        provisioner._set_env_vars = MagicMock()
        provisioner._module_yaml_paths = MagicMock(return_value=[])
        provisioner._build_compose_command = MagicMock(return_value=["docker", "up"])
        provisioner._run_compose_and_wait = MagicMock()

        provisioner._runner(cluster=dependent_cluster)

        # Verify context was updated
        assert mock_ctx.cluster_name == "dep-cluster"
        assert provisioner._dep_cluster_env == {"KEY": "VALUE"}
        # Verify dependent cluster added to provisioned list
        assert "dep-cluster" in mock_ctx.provisioned_clusters

    def test_runner_with_workers(self, provisioner, mock_ctx):
        """Test _runner with worker provisioning."""
        provisioner.workers = 3
        provisioner._set_env_vars = MagicMock()
        provisioner._module_yaml_paths = MagicMock(return_value=[])
        provisioner._build_compose_command = MagicMock(return_value=["docker", "up"])
        provisioner._run_compose_and_wait = MagicMock()

        # Mock the thread to complete quickly
        with patch("threading.Thread") as mock_thread_class:
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            provisioner._runner()

            # Verify worker thread was started
            mock_thread_class.assert_called_once()
            mock_thread.start.assert_called_once()
            mock_thread.join.assert_called_once()

    def test_runner_rollback_on_error(self, provisioner, mock_ctx):
        """Test _runner rollback on error."""
        provisioner._set_env_vars = MagicMock()
        provisioner._module_yaml_paths = MagicMock()
        provisioner._build_compose_command = MagicMock()
        provisioner._run_compose_and_wait = MagicMock(
            side_effect=Exception("Test error")
        )
        provisioner._rollback = MagicMock()

        with pytest.raises(MinitrinoError) as exc_info:
            provisioner._runner()

        assert "Failed to provision cluster" in str(exc_info.value)
        provisioner._rollback.assert_called_once()

    def test_determine_build_true(self, provisioner):
        """Test determining build is needed."""
        provisioner._image_src_changed = MagicMock(return_value=True)

        result = provisioner._determine_build()

        assert result is True

    def test_determine_build_false(self, provisioner):
        """Test determining build is not needed."""
        provisioner._image_src_changed = MagicMock(return_value=False)

        result = provisioner._determine_build()

        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    def test_provision_crashdump(self, mock_file, provisioner, mock_ctx):
        """Test crashdump file creation on error."""
        # Setup log buffer
        mock_ctx.logger._log_sink.buffer = [
            ("Error message 1", None, False),
            ("Spinner message", None, True),
            ("Error message 2", None, False),
        ]

        # Setup to raise a non-UserError
        provisioner._set_license = MagicMock()
        provisioner._set_distribution = MagicMock(side_effect=Exception("Test crash"))

        with pytest.raises(MinitrinoError) as exc_info:
            provisioner.provision([], "trino", 0, False)

        # Verify crashdump was written
        assert "Full provision log written to" in str(exc_info.value)
        mock_file.assert_called()
        # Verify only non-spinner messages written
        written_content = "".join(c[0][0] for c in mock_file().write.call_args_list)
        assert "Error message 1" in written_content
        assert "Error message 2" in written_content
        assert "Spinner message" not in written_content
