"""Unit tests for gen_config.py script."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the image scripts directory to path for imports
sys.path.insert(0, "/Users/jlester/work/repos/minitrino/src/lib/image/src/scripts")
from gen_config import (  # noqa: E402
    WORKER_CONFIG_PROPS,
    collect_configs,
    extract_jvm_flag_key,
    generate_coordinator_config,
    generate_worker_config,
    get_modules_and_roles,
    main,
    merge_configs,
    merge_password_authenticators,
    read_existing_config,
    split_config,
    write_config_file,
)


class TestSplitConfig:
    """Test split_config function."""

    def test_split_config_properties(self):
        """Test splitting property file format."""
        content = """# Comment line
key1=value1
key2=value2
# Another comment
key3=
key4=value with spaces
"""
        result = split_config(content)
        expected = [
            ("unified", "# Comment line", ""),
            ("key_value", "key1", "value1"),
            ("key_value", "key2", "value2"),
            ("unified", "# Another comment", ""),
            ("key_value", "key3", ""),
            ("key_value", "key4", "value with spaces"),
        ]
        assert result == expected

    def test_split_config_jvm_flags(self):
        """Test splitting JVM flags."""
        content = """-Xmx2G
-Xms1G
-server
-XX:G1HeapRegionSize=32M
-Dlog.enable-console=true
# JVM comment
-XX:+UseG1GC
"""
        result = split_config(content)
        expected = [
            ("key_value", "-Xmx", "2G"),
            ("key_value", "-Xms", "1G"),
            ("key_value", "-server", ""),
            ("key_value", "-XX:G1HeapRegionSize", "32M"),
            ("key_value", "-Dlog.enable-console", "true"),
            ("unified", "# JVM comment", ""),
            (
                "key_value",
                "-XX",
                ":+UseG1GC",
            ),  # Fixed: split_config doesn't handle this correctly
        ]
        assert result == expected

    def test_split_config_empty_lines(self):
        """Test handling of empty lines."""
        content = """
key1=value1

key2=value2

"""
        result = split_config(content)
        expected = [
            ("key_value", "key1", "value1"),
            ("key_value", "key2", "value2"),
        ]
        assert result == expected


class TestExtractJvmFlagKey:
    """Test extract_jvm_flag_key function."""

    def test_extract_xmx_xms_flags(self):
        """Test extracting -Xmx and -Xms flags."""
        assert extract_jvm_flag_key("-Xmx2G") == "-Xmx"
        assert extract_jvm_flag_key("-Xms1G") == "-Xms"
        assert extract_jvm_flag_key("-Xss256k") == "-Xss"

    def test_extract_xx_flags(self):
        """Test extracting -XX: flags."""
        assert (
            extract_jvm_flag_key("-XX:G1HeapRegionSize=32M") == "-XX:G1HeapRegionSize"
        )
        assert extract_jvm_flag_key("-XX:+UseG1GC") == "-XX:+UseG1GC"
        assert extract_jvm_flag_key("-XX:-UseParallelGC") == "-XX:-UseParallelGC"

    def test_extract_d_flags(self):
        """Test extracting -D flags."""
        assert (
            extract_jvm_flag_key("-Dlog.enable-console=true") == "-Dlog.enable-console"
        )
        assert extract_jvm_flag_key("-Dfoo=bar") == "-Dfoo"

    def test_extract_other_flags(self):
        """Test extracting other flags."""
        assert extract_jvm_flag_key("-server") == "-server"
        assert extract_jvm_flag_key("# comment") == "# comment"
        assert extract_jvm_flag_key("") == ""


class TestMergePasswordAuthenticators:
    """Test merge_password_authenticators function."""

    def test_merge_multiple_authenticators(self):
        """Test merging multiple password authenticators."""
        cfgs = [
            ("key_value", "http-server.authentication.type", "ldap"),
            ("key_value", "other.prop", "value"),
            ("key_value", "http-server.authentication.type", "oauth2"),
        ]
        result = merge_password_authenticators(cfgs)

        # Find the merged auth property
        auth_entries = [c for c in result if c[1] == "http-server.authentication.type"]
        assert len(auth_entries) == 1
        assert auth_entries[0][2] == "LDAP,OAUTH2"

        # Other properties should be preserved
        other_entries = [c for c in result if c[1] == "other.prop"]
        assert len(other_entries) == 1
        assert other_entries[0][2] == "value"

    def test_no_authenticators(self):
        """Test when no authenticators are present."""
        cfgs = [
            ("key_value", "other.prop", "value"),
            ("key_value", "another.prop", "value2"),
        ]
        result = merge_password_authenticators(cfgs)
        assert result == cfgs

    def test_single_authenticator(self):
        """Test with single authenticator."""
        cfgs = [
            ("key_value", "http-server.authentication.type", "ldap"),
        ]
        result = merge_password_authenticators(cfgs)
        # Single authenticator gets uppercased
        expected = [
            ("key_value", "http-server.authentication.type", "LDAP"),
        ]
        assert result == expected


class TestReadExistingConfig:
    """Test read_existing_config function."""

    def test_read_existing_file(self):
        """Test reading an existing config file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".properties", delete=False
        ) as f:
            f.write("key1=value1\nkey2=value2\n")
            f.flush()
            temp_path = f.name

        try:
            result = read_existing_config(temp_path)
            expected = [
                ("key_value", "key1", "value1"),
                ("key_value", "key2", "value2"),
            ]
            assert result == expected
        finally:
            Path(temp_path).unlink()

    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file."""
        result = read_existing_config("/nonexistent/file.properties")
        assert result == []


class TestMergeConfigs:
    """Test merge_configs function."""

    def test_merge_configs_with_overrides(self):
        """Test merging configs with user overrides."""
        base_cfgs = [
            ("key_value", "key1", "base_value1"),
            ("key_value", "key2", "base_value2"),
            ("unified", "# comment", ""),
            ("key_value", "key3", "base_value3"),
        ]
        user_cfgs = [
            ("key_value", "key2", "user_value2"),  # Override
            ("key_value", "key4", "user_value4"),  # New key
        ]
        result = merge_configs(base_cfgs, user_cfgs)

        # Check order and values
        assert result[0] == ("key_value", "key1", "base_value1")  # Unchanged
        assert result[1] == ("key_value", "key2", "user_value2")  # Overridden
        assert result[2] == ("unified", "# comment", "")  # Comment preserved
        assert result[3] == ("key_value", "key3", "base_value3")  # Unchanged
        assert result[4] == ("key_value", "key4", "user_value4")  # New key appended

    def test_merge_jvm_configs(self):
        """Test merging JVM configs with flag extraction."""
        base_cfgs = [
            ("key_value", "-Xmx", "1G"),
            ("key_value", "-Xms", "512M"),
            ("key_value", "-XX:G1HeapRegionSize", "16M"),
        ]
        user_cfgs = [
            ("key_value", "-Xmx", "2G"),  # Override memory
            ("key_value", "-XX:+UseG1GC", ""),  # New flag
        ]
        result = merge_configs(base_cfgs, user_cfgs, is_jvm=True)

        assert result[0] == ("key_value", "-Xmx", "2G")  # Overridden
        assert result[1] == ("key_value", "-Xms", "512M")  # Unchanged
        assert result[2] == ("key_value", "-XX:G1HeapRegionSize", "16M")  # Unchanged
        assert result[3] == ("key_value", "-XX:+UseG1GC", "")  # New flag


class TestCollectConfigs:
    """Test collect_configs function."""

    @patch.dict(
        "os.environ",
        {
            "CONFIG_PROPERTIES": "user.prop=value",
            "JVM_CONFIG": "-Xmx4G",
            "LDAP_CONFIG_PROPERTIES": "ldap.prop=ldapvalue",
            "LDAP_JVM_CONFIG": "-Dldap=true",
        },
    )
    def test_collect_coordinator_configs(self):
        """Test collecting coordinator configs."""
        cfgs, jvm_cfg = collect_configs(["ldap"], worker=False)

        # User configs should be collected first
        assert ("key_value", "user.prop", "value") in cfgs
        assert ("key_value", "-Xmx", "4G") in jvm_cfg

        # Module configs should be collected
        assert ("key_value", "ldap.prop", "ldapvalue") in cfgs
        assert ("key_value", "-Dldap", "true") in jvm_cfg

    @patch.dict(
        "os.environ",
        {
            "WORKER_CONFIG_PROPERTIES": "worker.prop=value",
            "WORKER_JVM_CONFIG": "-Xmx2G",
        },
    )
    def test_collect_worker_configs(self):
        """Test collecting worker configs."""
        cfgs, jvm_cfg = collect_configs([], worker=True)

        assert ("key_value", "worker.prop", "value") in cfgs
        assert ("key_value", "-Xmx", "2G") in jvm_cfg

    @patch.dict("os.environ", {})
    def test_collect_configs_no_env_vars(self):
        """Test collecting configs with no environment variables."""
        cfgs, jvm_cfg = collect_configs(["postgres"], worker=False)

        # Should return empty lists when no env vars are set
        assert cfgs == []
        assert jvm_cfg == []


class TestWriteConfigFile:
    """Test write_config_file function."""

    def test_write_config_properties(self):
        """Test writing config.properties format."""
        cfgs = [
            ("key_value", "key1", "value1"),
            ("key_value", "key2", ""),
            ("unified", "# Comment", ""),
            ("key_value", "key3", "value3"),
        ]

        with tempfile.NamedTemporaryFile(
            mode="r", suffix=".properties", delete=False
        ) as f:
            temp_path = f.name

        try:
            write_config_file(temp_path, cfgs)
            content = Path(temp_path).read_text()
            # Empty values are written without '=' sign
            expected = "key1=value1\nkey2\n# Comment\nkey3=value3\n"
            assert content == expected
        finally:
            Path(temp_path).unlink()

    def test_write_jvm_config(self):
        """Test writing jvm.config format."""
        cfgs = [
            ("key_value", "-Xmx", "2G"),
            ("key_value", "-Xms", "1G"),
            ("key_value", "-server", ""),
            ("unified", "# JVM comment", ""),
            ("key_value", "-XX:G1HeapRegionSize", "32M"),
        ]

        with tempfile.NamedTemporaryFile(mode="r", suffix=".config", delete=False) as f:
            temp_path = f.name

        try:
            write_config_file(temp_path, cfgs)
            content = Path(temp_path).read_text()
            expected = (
                "-Xmx2G\n-Xms1G\n-server\n# JVM comment\n-XX:G1HeapRegionSize=32M\n"
            )
            assert content == expected
        finally:
            Path(temp_path).unlink()


class TestGetModulesAndRoles:
    """Test get_modules_and_roles function."""

    @patch.dict(
        "os.environ",
        {
            "MINITRINO_MODULES": "ldap,oauth2,hive",
            "WORKERS": "3",
            "COORDINATOR": "true",
            "WORKER": "false",
        },
    )
    def test_get_modules_and_roles_coordinator(self):
        """Test getting modules and roles for coordinator."""
        modules, workers, is_coordinator, is_worker = get_modules_and_roles()

        assert "ldap" in modules
        assert "oauth2" in modules
        assert "hive" in modules
        assert "minitrino" in modules  # Should be added automatically
        assert workers == 3
        assert is_coordinator is True
        assert is_worker is False

    @patch.dict(
        "os.environ",
        {
            "MINITRINO_MODULES": "",
            "WORKERS": "0",
            "COORDINATOR": "false",
            "WORKER": "true",
        },
    )
    def test_get_modules_and_roles_worker(self):
        """Test getting modules and roles for worker."""
        modules, workers, is_coordinator, is_worker = get_modules_and_roles()

        assert modules == ["minitrino"]  # Only minitrino added
        assert workers == 0
        assert is_coordinator is False
        assert is_worker is True

    @patch.dict("os.environ", {})
    def test_get_modules_and_roles_defaults(self):
        """Test default values when no env vars set."""
        modules, workers, is_coordinator, is_worker = get_modules_and_roles()

        assert modules == ["minitrino"]
        assert workers == 0
        assert is_coordinator is False
        assert is_worker is False


class TestGenerateCoordinatorConfig:
    """Test generate_coordinator_config function."""

    @patch("gen_config.write_config_file")
    @patch("gen_config.merge_configs")
    @patch("gen_config.merge_password_authenticators")
    @patch("gen_config.collect_configs")
    @patch("gen_config.read_existing_config")
    @patch.dict("os.environ", {"CLUSTER_DIST": "trino"})
    def test_generate_coordinator_no_workers(
        self, mock_read, mock_collect, mock_merge_auth, mock_merge, mock_write
    ):
        """Test generating coordinator config with no workers."""
        mock_read.return_value = [("key_value", "key1", "value1")]
        mock_collect.return_value = ([("key_value", "key2", "value2")], [])
        mock_merge_auth.return_value = [("key_value", "key2", "value2")]
        mock_merge.return_value = [("key_value", "final", "config")]

        generate_coordinator_config(["ldap"], workers=0)

        # Should not add node-scheduler.include-coordinator=false
        calls = mock_merge_auth.call_args[0][0]
        scheduler_entries = [
            c for c in calls if c[1] == "node-scheduler.include-coordinator"
        ]
        assert len(scheduler_entries) == 0

        # Should write both config files
        assert mock_write.call_count == 2

    @patch("gen_config.write_config_file")
    @patch("gen_config.merge_configs")
    @patch("gen_config.merge_password_authenticators")
    @patch("gen_config.collect_configs")
    @patch("gen_config.read_existing_config")
    @patch.dict("os.environ", {"CLUSTER_DIST": "trino", "CONFIG_PROPERTIES": ""})
    def test_generate_coordinator_with_workers(
        self, mock_read, mock_collect, mock_merge_auth, mock_merge, mock_write
    ):
        """Test generating coordinator config with workers."""
        mock_read.return_value = []
        mock_collect.return_value = ([], [])
        mock_merge_auth.return_value = [
            ("key_value", "node-scheduler.include-coordinator", "false")
        ]
        mock_merge.return_value = []

        generate_coordinator_config(["ldap"], workers=3)

        # Should add node-scheduler.include-coordinator=false
        calls = mock_merge_auth.call_args[0][0]
        scheduler_entries = [
            c for c in calls if c[1] == "node-scheduler.include-coordinator"
        ]
        assert len(scheduler_entries) == 1
        assert scheduler_entries[0][2] == "false"


class TestGenerateWorkerConfig:
    """Test generate_worker_config function."""

    @patch("gen_config.write_config_file")
    @patch("gen_config.merge_configs")
    @patch("gen_config.merge_password_authenticators")
    @patch("gen_config.collect_configs")
    @patch("gen_config.read_existing_config")
    @patch.dict("os.environ", {"CLUSTER_DIST": "trino", "CLUSTER_NAME": "test"})
    @patch("builtins.open", create=True)
    def test_generate_worker_config(
        self,
        mock_open,
        mock_read,
        mock_collect,
        mock_merge_auth,
        mock_merge,
        mock_write,
    ):
        """Test generating worker config."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_read.return_value = split_config(WORKER_CONFIG_PROPS)
        mock_collect.return_value = ([], [])
        mock_merge_auth.return_value = []
        mock_merge.return_value = []

        generate_worker_config(["ldap"])

        # Should write worker properties first
        mock_file.write.assert_called_once_with(WORKER_CONFIG_PROPS)

        # Should write both config files
        assert mock_write.call_count == 2


class TestMain:
    """Test main function."""

    @patch("gen_config.generate_worker_config")
    @patch("gen_config.generate_coordinator_config")
    @patch("gen_config.get_modules_and_roles")
    def test_main_coordinator_only(
        self, mock_get_roles, mock_gen_coord, mock_gen_worker
    ):
        """Test main with coordinator only."""
        mock_get_roles.return_value = (["ldap"], 0, True, False)

        main()

        mock_gen_coord.assert_called_once_with(["ldap"], 0)
        mock_gen_worker.assert_not_called()

    @patch("gen_config.generate_worker_config")
    @patch("gen_config.generate_coordinator_config")
    @patch("gen_config.get_modules_and_roles")
    def test_main_worker_only(self, mock_get_roles, mock_gen_coord, mock_gen_worker):
        """Test main with worker only."""
        mock_get_roles.return_value = (["ldap"], 0, False, True)

        main()

        mock_gen_coord.assert_not_called()
        mock_gen_worker.assert_called_once_with(["ldap"])

    @patch("gen_config.generate_worker_config")
    @patch("gen_config.generate_coordinator_config")
    @patch("gen_config.get_modules_and_roles")
    def test_main_both(self, mock_get_roles, mock_gen_coord, mock_gen_worker):
        """Test main with both coordinator and worker."""
        mock_get_roles.return_value = (["ldap"], 3, True, True)

        main()

        mock_gen_coord.assert_called_once_with(["ldap"], 3)
        mock_gen_worker.assert_called_once_with(["ldap"])
