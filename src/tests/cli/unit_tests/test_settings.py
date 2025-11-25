"""Unit tests for settings module.

Tests configuration constants and templates.
"""

from minitrino import settings


class TestDockerLabels:
    """Test suite for Docker label constants."""

    def test_root_label(self):
        """Test ROOT_LABEL constant."""
        assert settings.ROOT_LABEL == "org.minitrino.root=true"

    def test_module_label_key(self):
        """Test MODULE_LABEL_KEY constant."""
        assert settings.MODULE_LABEL_KEY == "org.minitrino.module"

    def test_compose_label_key(self):
        """Test COMPOSE_LABEL_KEY constant."""
        assert settings.COMPOSE_LABEL_KEY == "com.docker.compose.project"


class TestGenericConstants:
    """Test suite for generic constants."""

    def test_lib_constant(self):
        """Test LIB constant."""
        assert settings.LIB == "lib"

    def test_module_constants(self):
        """Test module-related constants."""
        assert settings.MODULE_ROOT == "modules"
        assert settings.MODULE_ADMIN == "admin"
        assert settings.MODULE_CATALOG == "catalog"
        assert settings.MODULE_SECURITY == "security"
        assert settings.MODULE_RESOURCES == "resources"

    def test_cluster_version_constants(self):
        """Test cluster version constants."""
        assert settings.MIN_CLUSTER_VER == 443
        assert settings.DEFAULT_CLUSTER_VER == 476
        assert isinstance(settings.MIN_CLUSTER_VER, int)
        assert isinstance(settings.DEFAULT_CLUSTER_VER, int)
        assert settings.MIN_CLUSTER_VER < settings.DEFAULT_CLUSTER_VER

    def test_directory_constants(self):
        """Test directory path constants."""
        assert settings.ETC_DIR == "/etc/${CLUSTER_DIST}"
        assert "${CLUSTER_DIST}" in settings.ETC_DIR

    def test_license_constants(self):
        """Test license-related constants."""
        assert "LIC_PATH" in settings.LIC_VOLUME_MOUNT
        assert "LIC_MOUNT_PATH" in settings.LIC_VOLUME_MOUNT
        assert settings.LIC_MOUNT_PATH == "/mnt/etc/starburstdata.license:ro"
        assert ":ro" in settings.LIC_MOUNT_PATH  # Read-only mount

    def test_config_file_constants(self):
        """Test configuration file constants."""
        assert settings.CLUSTER_CONFIG == "config.properties"
        assert settings.CLUSTER_JVM_CONFIG == "jvm.config"


class TestSnapshotConstants:
    """Test suite for snapshot-related constants."""

    def test_snapshot_root_files(self):
        """Test SNAPSHOT_ROOT_FILES list."""
        expected_files = [
            "docker-compose.yaml",
            "minitrino.env",
            "version",
            "image",
        ]
        assert expected_files == settings.SNAPSHOT_ROOT_FILES
        assert len(settings.SNAPSHOT_ROOT_FILES) == 4
        assert isinstance(settings.SNAPSHOT_ROOT_FILES, list)


class TestScrubbingConstants:
    """Test suite for scrubbing/security constants."""

    def test_scrubbed_constant(self):
        """Test SCRUBBED masking string."""
        assert settings.SCRUBBED == "*" * 8
        assert len(settings.SCRUBBED) == 8

    def test_scrub_keys(self):
        """Test SCRUB_KEYS list for sensitive data."""
        assert "password" in settings.SCRUB_KEYS
        assert "key" in settings.SCRUB_KEYS
        assert "token" in settings.SCRUB_KEYS

        # Check variations
        assert "-password" in settings.SCRUB_KEYS
        assert "_password" in settings.SCRUB_KEYS
        assert "-key" in settings.SCRUB_KEYS
        assert "_key" in settings.SCRUB_KEYS
        assert "-token" in settings.SCRUB_KEYS
        assert "_token" in settings.SCRUB_KEYS

    def test_scrub_keys_is_list(self):
        """Test that SCRUB_KEYS is a list."""
        assert isinstance(settings.SCRUB_KEYS, list)
        assert len(settings.SCRUB_KEYS) == 9  # 3 base keys * 3 variations each


class TestTemplates:
    """Test suite for template strings."""

    def test_config_template(self):
        """Test CONFIG_TEMPLATE multiline string."""
        assert "[config]" in settings.CONFIG_TEMPLATE
        assert "LIB_PATH=" in settings.CONFIG_TEMPLATE
        assert "IMAGE=" in settings.CONFIG_TEMPLATE
        assert "CLUSTER_NAME=" in settings.CONFIG_TEMPLATE
        assert "LIC_PATH=" in settings.CONFIG_TEMPLATE
        assert "CLUSTER_VER=" in settings.CONFIG_TEMPLATE
        assert "TEXT_EDITOR=" in settings.CONFIG_TEMPLATE

        # Check comments
        assert "# defaults to ~/.minitrino/lib" in settings.CONFIG_TEMPLATE
        assert "# 'trino' or 'starburst'" in settings.CONFIG_TEMPLATE
        assert "# defaults to 'default'" in settings.CONFIG_TEMPLATE

    def test_provision_snapshot_template(self):
        """Test PROVISION_SNAPSHOT_TEMPLATE multiline string."""
        assert "#!/usr/bin/env bash" in settings.PROVISION_SNAPSHOT_TEMPLATE
        assert "minitrino.cfg" in settings.PROVISION_SNAPSHOT_TEMPLATE

        # Check it has the shebang line
        lines = settings.PROVISION_SNAPSHOT_TEMPLATE.strip().split("\n")
        assert lines[0] == "#!/usr/bin/env bash"

    def test_templates_are_strings(self):
        """Test that templates are string types."""
        assert isinstance(settings.CONFIG_TEMPLATE, str)
        assert isinstance(settings.PROVISION_SNAPSHOT_TEMPLATE, str)


class TestConstantTypes:
    """Test data types of various constants."""

    def test_string_constants(self):
        """Test that string constants are strings."""
        string_constants = [
            settings.ROOT_LABEL,
            settings.MODULE_LABEL_KEY,
            settings.COMPOSE_LABEL_KEY,
            settings.LIB,
            settings.MODULE_ROOT,
            settings.MODULE_ADMIN,
            settings.MODULE_CATALOG,
            settings.MODULE_SECURITY,
            settings.MODULE_RESOURCES,
            settings.ETC_DIR,
            settings.LIC_VOLUME_MOUNT,
            settings.LIC_MOUNT_PATH,
            settings.CLUSTER_CONFIG,
            settings.CLUSTER_JVM_CONFIG,
            settings.SCRUBBED,
        ]

        for constant in string_constants:
            assert isinstance(constant, str)

    def test_integer_constants(self):
        """Test that integer constants are integers."""
        integer_constants = [
            settings.MIN_CLUSTER_VER,
            settings.DEFAULT_CLUSTER_VER,
        ]

        for constant in integer_constants:
            assert isinstance(constant, int)

    def test_list_constants(self):
        """Test that list constants are lists."""
        list_constants = [
            settings.SNAPSHOT_ROOT_FILES,
            settings.SCRUB_KEYS,
        ]

        for constant in list_constants:
            assert isinstance(constant, list)
