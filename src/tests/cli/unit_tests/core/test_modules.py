"""Unit tests for the Modules class."""

from unittest.mock import MagicMock, patch

import pytest

from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.modules import Modules


class TestModules:
    """Test suite for Modules class."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MinitrinoContext."""
        ctx = MagicMock()
        ctx.lib_dir = "/usr/local/lib/minitrino"
        ctx.logger = MagicMock()
        ctx.docker_client = MagicMock()
        ctx.env = {
            "CLUSTER_VER": "443",
            "CLUSTER_DIST": "trino",
            "LIC_PATH": "",
        }
        ctx.cluster = MagicMock()
        ctx.cluster.resource = MagicMock()
        ctx.cluster.resource.resources.return_value.containers.return_value = []
        ctx.modules = None  # Will be set when Modules is created
        return ctx

    @patch.object(Modules, "_load_modules")
    def test_init(self, mock_load, mock_ctx):
        """Test Modules initialization."""
        modules = Modules(mock_ctx)

        assert modules._ctx == mock_ctx
        assert modules.data == {}
        mock_load.assert_called_once()

    @patch("minitrino.core.modules.utils")
    def test_running_modules_empty(self, mock_utils, mock_ctx):
        """Test getting running modules when none exist."""
        mock_ctx.cluster.resource.resources.return_value.containers.return_value = []

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}

        result = modules.running_modules()

        assert result == {}
        mock_utils.check_daemon.assert_called_once_with(mock_ctx.docker_client)

    @patch("minitrino.core.modules.utils")
    def test_running_modules_with_modules(self, mock_utils, mock_ctx):
        """Test getting running modules from containers."""
        # Create mock containers with module labels
        container1 = MagicMock()
        container1.name = "minitrino-minio"
        container1.cluster_name = "default"
        container1.labels = {
            "org.minitrino.module.admin.minio": "true",
            "com.docker.compose.project": "minitrino-default",
        }

        container2 = MagicMock()
        container2.name = "minitrino-hive"
        container2.cluster_name = "default"
        container2.labels = {
            "org.minitrino.module.catalog.hive": "true",
            "com.docker.compose.project": "minitrino-default",
        }

        mock_ctx.cluster.resource.resources.return_value.containers.return_value = [
            container1,
            container2,
        ]

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {}, "hive": {}}

        result = modules.running_modules()

        assert result == {"minio": "default", "hive": "default"}

    @patch("minitrino.core.modules.utils")
    def test_running_modules_missing_cluster_name(self, mock_utils, mock_ctx):
        """Test error when container is missing cluster name."""
        container = MagicMock()
        container.name = "minitrino-minio"
        container.cluster_name = None
        container.labels = {"org.minitrino.module.admin.minio": "true"}

        mock_ctx.cluster.resource.resources.return_value.containers.return_value = [
            container
        ]

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {}}

        with pytest.raises(UserError) as exc_info:
            modules.running_modules()
        assert "Unable to determine cluster name" in str(exc_info.value)

    @patch("minitrino.core.modules.utils")
    def test_running_modules_missing_labels(self, mock_utils, mock_ctx):
        """Test error when container is missing Minitrino labels."""
        container = MagicMock()
        container.name = "unknown-container"
        container.cluster_name = "default"
        container.labels = {}

        mock_ctx.cluster.resource.resources.return_value.containers.return_value = [
            container
        ]

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}

        with pytest.raises(UserError) as exc_info:
            modules.running_modules()
        assert "Missing Minitrino labels" in str(exc_info.value)

    @patch("minitrino.core.modules.utils")
    def test_running_modules_not_in_library(self, mock_utils, mock_ctx):
        """Test error when running module not found in library."""
        container = MagicMock()
        container.name = "minitrino-unknown"
        container.cluster_name = "default"
        container.labels = {"org.minitrino.module.admin.unknown": "true"}

        mock_ctx.cluster.resource.resources.return_value.containers.return_value = [
            container
        ]

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}  # Module not in data

        with pytest.raises(UserError) as exc_info:
            modules.running_modules()
        assert "not found in the library" in str(exc_info.value)

    @patch("minitrino.core.modules.utils")
    def test_validate_module_name_valid(self, mock_utils, mock_ctx):
        """Test validating a valid module name."""
        mock_utils.closest_match_or_error.return_value = "minio"

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {}, "hive": {}}

        result = modules.validate_module_name("minio")

        assert result == "minio"
        mock_utils.closest_match_or_error.assert_called_once_with(
            "minio", ["minio", "hive"], "module"
        )

    def test_check_dep_modules_no_deps(self, mock_ctx):
        """Test checking dependent modules when none exist."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {}}

        result = modules.check_dep_modules(["minio"])

        assert result == ["minio"]

    def test_check_dep_modules_with_deps(self, mock_ctx):
        """Test checking dependent modules with dependencies."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "iceberg": {"dependentModules": ["hive"]},
            "hive": {"dependentModules": ["postgres"]},
            "postgres": {},
        }

        result = modules.check_dep_modules(["iceberg"])

        # Should include iceberg, hive, and postgres
        assert set(result) == {"iceberg", "hive", "postgres"}

    def test_check_dep_modules_circular(self, mock_ctx):
        """Test checking dependent modules with circular dependencies."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "module1": {"dependentModules": ["module2"]},
            "module2": {"dependentModules": ["module1"]},
        }

        result = modules.check_dep_modules(["module1"])

        # Should handle circular deps gracefully
        assert set(result) == {"module1", "module2"}

    def test_check_module_version_requirements_no_versions(self, mock_ctx):
        """Test version requirements when no versions specified."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {}}

        # Should not raise
        modules.check_module_version_requirements(["minio"])

    def test_check_module_version_requirements_valid(self, mock_ctx):
        """Test version requirements with valid version."""
        mock_ctx.env["CLUSTER_VER"] = "443"

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {"versions": ["400", "500"]}}

        # Should not raise (443 is between 400 and 500)
        modules.check_module_version_requirements(["minio"])

    def test_check_module_version_requirements_too_old(self, mock_ctx):
        """Test version requirements with cluster version too old."""
        mock_ctx.env["CLUSTER_VER"] = "300"

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {"versions": ["400"]}}

        with pytest.raises(UserError) as exc_info:
            modules.check_module_version_requirements(["minio"])
        assert "minimum required cluster version" in str(exc_info.value)

    def test_check_module_version_requirements_too_new(self, mock_ctx):
        """Test version requirements with cluster version too new."""
        mock_ctx.env["CLUSTER_VER"] = "600"

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {"versions": ["400", "500"]}}

        with pytest.raises(UserError) as exc_info:
            modules.check_module_version_requirements(["minio"])
        assert "maximum required cluster version" in str(exc_info.value)

    def test_check_module_version_requirements_invalid_spec(self, mock_ctx):
        """Test version requirements with invalid specification."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {"versions": ["400", "500", "600"]}}

        with pytest.raises(UserError) as exc_info:
            modules.check_module_version_requirements(["minio"])
        assert "Invalid versions specification" in str(exc_info.value)

    def test_check_compatibility_no_conflicts(self, mock_ctx):
        """Test compatibility check with no conflicts."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "minio": {},
            "hive": {},
        }

        # Should not raise
        modules.check_compatibility(["minio", "hive"])

    def test_check_compatibility_with_conflicts(self, mock_ctx):
        """Test compatibility check with conflicting modules."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "ldap": {"incompatibleModules": ["oauth2"]},
            "oauth2": {},
        }

        with pytest.raises(UserError) as exc_info:
            modules.check_compatibility(["ldap", "oauth2"])
        assert "Incompatible modules detected" in str(exc_info.value)

    def test_check_compatibility_wildcard(self, mock_ctx):
        """Test compatibility check with wildcard incompatibility."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "exclusive": {"incompatibleModules": ["*"]},
            "other": {},
        }

        with pytest.raises(UserError) as exc_info:
            modules.check_compatibility(["exclusive", "other"])
        assert "Incompatible modules detected" in str(exc_info.value)

    def test_module_services_empty(self, mock_ctx):
        """Test getting module services with no modules."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}

        result = modules.module_services([])

        assert result == []

    def test_module_services_with_services(self, mock_ctx):
        """Test getting module services."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {
            "minio": {
                "yaml_file": "/path/to/minio.yaml",
                "yaml_dict": {
                    "services": {
                        "minio": {"image": "minio:latest"},
                        "mc": {"image": "minio/mc:latest"},
                    }
                },
            }
        }

        result = modules.module_services(["minio"])

        assert len(result) == 2
        assert result[0][0] == "minio"
        assert result[1][0] == "mc"

    def test_module_services_no_services_section(self, mock_ctx):
        """Test error when module has no services section."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"bad": {"yaml_file": "/path/to/bad.yaml", "yaml_dict": {}}}

        with pytest.raises(MinitrinoError) as exc_info:
            modules.module_services(["bad"])
        assert "no 'services' section found" in str(exc_info.value)

    def test_check_volumes_no_volumes(self, mock_ctx):
        """Test checking volumes when none exist."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"minio": {"yaml_dict": {}}}

        # Should not warn
        modules.check_volumes(["minio"])
        mock_ctx.logger.warn.assert_not_called()

    def test_check_volumes_with_volumes(self, mock_ctx):
        """Test checking volumes when they exist."""
        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {"postgres": {"yaml_dict": {"volumes": {"pgdata": {}}}}}

        modules.check_volumes(["postgres"])

        mock_ctx.logger.warn.assert_called_once()
        assert "persistent volumes" in mock_ctx.logger.warn.call_args[0][0]

    @patch("os.path.isdir")
    def test_load_modules_invalid_dir(self, mock_isdir, mock_ctx):
        """Test error when modules directory is invalid."""
        mock_isdir.return_value = False

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}

        with pytest.raises(MinitrinoError) as exc_info:
            modules._load_modules()
        assert "Path is not a directory" in str(exc_info.value)

    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_load_modules_missing_yaml(self, mock_listdir, mock_isdir, mock_ctx):
        """Test error when module is missing YAML file."""
        mock_isdir.return_value = True
        mock_listdir.side_effect = lambda p: (["bad-module"] if "admin" in p else [])

        modules = Modules.__new__(Modules)
        modules._ctx = mock_ctx
        modules.data = {}

        with pytest.raises(UserError) as exc_info:
            modules._load_modules()
        assert "Missing Docker Compose file" in str(exc_info.value)
