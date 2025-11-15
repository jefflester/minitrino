#!/usr/bin/env python3
"""Generate cluster config files from environment variables."""

import os
import re
from pathlib import Path

LOG_PREFIX = "[gen_config]"
ETC_DIR = f"/etc/{os.environ.get('CLUSTER_DIST', 'trino')}"

WORKER_CONFIG_PROPS = """coordinator=false
http-server.http.port=8080
discovery.uri=http://minitrino-${ENV:CLUSTER_NAME}:8080
internal-communication.shared-secret=bWluaXRyaW5vUm9ja3MxNQo="""


def get_java_version() -> int:
    """Get the Java major version based on the Trino/Starburst version.

    Uses the same version mapping as install-java.sh:
    - >= 436 <= 446: Java 21
    - >= 447 <= 463: Java 22
    - >= 464 <= 467: Java 23
    - >= 468: Java 24

    Returns
    -------
    int
        Java major version number (e.g., 21, 22, 23, 24).
    """
    cluster_ver = os.environ.get("CLUSTER_VER", "")
    if not cluster_ver:
        return 21  # Default to Java 21 if version not available
    trino_ver = int(cluster_ver[:3])
    if 436 <= trino_ver <= 446:
        return 21
    elif 447 <= trino_ver <= 463:
        return 22
    elif 464 <= trino_ver <= 467:
        return 23
    elif trino_ver >= 468:
        return 24
    else:
        return 21  # Default for older versions


def is_security_manager_option(jvm_flag: str) -> bool:
    """Check if a JVM flag is related to Security Manager.

    The Security Manager was deprecated in Java 17 and removed in Java 21+.
    This function identifies JVM options that attempt to enable or configure
    the Security Manager.

    Parameters
    ----------
    jvm_flag : str
        The JVM flag to check (e.g., "-Djava.security.manager=allow").

    Returns
    -------
    bool
        True if the flag is Security Manager-related, False otherwise.
    """
    flag = jvm_flag.strip()
    # Check for Security Manager options
    security_manager_patterns = [
        "-Djava.security.manager=",
        "-Djava.security.manager",
    ]
    return any(flag.startswith(pattern) for pattern in security_manager_patterns)


def split_config(content: str) -> list[tuple]:
    """Split config file content into tuples for merging.

    For JVM flags:
      - Lines like '-Xmx1G' become ('key_value', '-Xmx', '1G')
      - Lines like '-server' become ('key_value', '-server', '')
      - Lines like '-XX:G1HeapRegionSize=32M' become ('key_value',
        '-XX:G1HeapRegionSize', '32M')
      - Lines like '-Dlog.enable-console=true' become ('key_value',
        '-Dlog.enable-console', 'true')
    - Comments and blank lines are ('unified', line, '')
    """
    result = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            result.append(("unified", line, ""))
        elif "=" in stripped:
            key, val = stripped.split("=", 1)
            result.append(("key_value", key.strip(), val.strip()))
        else:
            # Try to split -X* flags into prefix and value
            match = re.match(r"^(-X[a-zA-Z]+)(.*)$", stripped)
            if match:
                result.append(("key_value", match.group(1), match.group(2)))
            else:
                result.append(("key_value", stripped, ""))
    return result


def extract_jvm_flag_key(line: str) -> str:
    """Extract the deduplication key for a JVM flag line.

    - For -Xmx2G, returns -Xmx
    - For -Xms1G, returns -Xms
    - For -XX:Foo=Bar, returns -XX:Foo
    - For -Dfoo=bar, returns -Dfoo
    - For unified/comment lines, returns the whole line
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return line
    if line.startswith("-XX:") or line.startswith("-D"):
        if "=" in line:
            return line.split("=", 1)[0]
        else:
            return line
    # -Xmx2G, -Xms1G, etc.
    match = re.match(r"^(-X[a-zA-Z]+)", line)
    if match:
        return match.group(1)
    return line


def merge_password_authenticators(cfgs: list[tuple]) -> list[tuple]:
    """Merge multiple password authenticators."""
    merge = [
        i
        for i, cfg in enumerate(cfgs)
        if cfg[0] == "key_value" and cfg[1] == "http-server.authentication.type"
    ]
    if not merge:
        return cfgs
    values = [cfgs[i][2].upper() for i in merge]
    auth_property = ("key_value", "http-server.authentication.type", ",".join(values))
    new_cfgs = [x for i, x in enumerate(cfgs) if i not in merge]
    new_cfgs.append(auth_property)
    print(
        f"{LOG_PREFIX} Merged password authenticators: {values} -> {auth_property[2]}"
    )
    return new_cfgs


def read_existing_config(filename: str) -> list[tuple]:
    """Read an existing config file and return parsed entries."""
    if not Path(filename).exists():
        return []
    content = Path(filename).read_text()
    return split_config(content)


def merge_configs(
    base_cfgs: list[tuple], user_cfgs: list[tuple], is_jvm: bool = False
) -> list[tuple]:
    """Merge default and user configs.

    For each config (config.properties or jvm.config):

        - Preserves the order of default configs.
        - If a user override exists for a key/flag, replaces the default
          value in-place.
        - Appends any user-supplied keys/flags not present in defaults
          to the end.
        - Retains comments and unified lines in their original
          positions.

    Parameters
    ----------
    base_cfgs : list[tuple]
        Parsed config tuples from the base/default config file.
    user_cfgs : list[tuple]
        Parsed config tuples from user/module/environment overrides.
    is_jvm : bool
        If True, use JVM flag key extraction for deduplication.

    Returns
    -------
    list[tuple]
        Merged, deduplicated, and order-preserving config tuples.
    """
    # Filter out Security Manager options for Java 21+ when processing JVM configs
    if is_jvm:
        java_version = get_java_version()
        if java_version >= 21:
            # Filter base configs
            filtered_base = []
            for entry in base_cfgs:
                if entry[0] == "key_value":
                    flag = entry[1]
                    if is_security_manager_option(flag):
                        print(
                            f"{LOG_PREFIX} Filtering Security Manager option "
                            f"(incompatible with Java {java_version}): {flag}"
                        )
                        continue
                filtered_base.append(entry)
            base_cfgs = filtered_base

            # Filter user configs
            filtered_user = []
            for entry in user_cfgs:
                if entry[0] == "key_value":
                    flag = entry[1]
                    if is_security_manager_option(flag):
                        print(
                            f"{LOG_PREFIX} Filtering Security Manager option "
                            f"(incompatible with Java {java_version}): {flag}"
                        )
                        continue
                filtered_user.append(entry)
            user_cfgs = filtered_user

    key_fn = extract_jvm_flag_key if is_jvm else (lambda k: k)
    # Build user overrides map
    user_kv = {}
    for entry in user_cfgs:
        if entry[0] == "key_value":
            user_kv[key_fn(entry[1])] = entry[2]

    seen_keys = set()
    merged = []
    for entry in base_cfgs:
        if entry[0] == "key_value":
            key = key_fn(entry[1])
            if key in user_kv:
                merged.append(("key_value", entry[1], user_kv[key]))
                seen_keys.add(key)
            else:
                merged.append(entry)
                seen_keys.add(key)
        else:
            merged.append(entry)
    # Append user entries not already seen
    for entry in user_cfgs:
        if entry[0] == "key_value":
            key = key_fn(entry[1])
            if key not in seen_keys:
                merged.append(entry)
                seen_keys.add(key)
        else:
            # Only append comments/unified lines if not already present
            if entry not in merged:
                merged.append(entry)
    return merged


def collect_configs(
    modules: list[str], worker: bool = False
) -> tuple[list[tuple], list[tuple]]:
    """Collect config and JVM config fragments from env.

    For each module, if a config env var exists, use it; otherwise, skip. Modules that
    do not supply config envs (e.g., POSTGRES) are ignored.
    """
    role = "worker" if worker else "coordinator"
    print(f"{LOG_PREFIX} Collecting configs for role: {role}")
    cfgs = []
    jvm_cfg = []

    if worker:
        jvm_env_var = "WORKER_JVM_CONFIG"
        config_env_var = "WORKER_CONFIG_PROPERTIES"
    else:
        jvm_env_var = "JVM_CONFIG"
        config_env_var = "CONFIG_PROPERTIES"

    # User-supplied overrides
    env_usr_cfgs = os.environ.get(config_env_var, "")
    env_user_jvm_cfg = os.environ.get(jvm_env_var, "")
    if env_usr_cfgs:
        print(f"{LOG_PREFIX} Found user {config_env_var} override.")
        cfgs.extend(split_config(env_usr_cfgs))
    if env_user_jvm_cfg:
        print(f"{LOG_PREFIX} Found user {jvm_env_var} override.")
        jvm_cfg.extend(split_config(env_user_jvm_cfg))

    for module in modules:
        mod_env_prefix = module.replace("-", "_").upper()
        mod_cfg_env = f"{mod_env_prefix}_{config_env_var}"
        mod_jvm_env = f"{mod_env_prefix}_{jvm_env_var}"
        mod_cfg = os.environ.get(mod_cfg_env)
        mod_jvm = os.environ.get(mod_jvm_env)
        if mod_cfg:
            print(f"{LOG_PREFIX} Found {mod_cfg_env} for module {module}.")
            cfgs.extend(split_config(mod_cfg))
        if mod_jvm:
            print(f"{LOG_PREFIX} Found {mod_jvm_env} for module {module}.")
            jvm_cfg.extend(split_config(mod_jvm))
        if not (mod_cfg or mod_jvm):
            print(f"{LOG_PREFIX} No config envs for module {module}, skipping.")
    print(
        f"{LOG_PREFIX} Collected {len(cfgs)} config "
        f"and {len(jvm_cfg)} JVM entries for {role}."
    )
    return cfgs, jvm_cfg


def write_config_file(filename: str, cfgs: list[tuple]) -> None:
    """Write config lines to a file."""
    print(f"{LOG_PREFIX} Writing {len(cfgs)} entries to {filename}...")
    lines = []
    for entry in cfgs:
        if entry[0] == "key_value":
            _, k, v = entry
            if v:
                # For -X* flags, concatenate without '='
                if re.match(r"^-X[a-zA-Z]+$", k):
                    lines.append(f"{k}{v}")
                else:
                    lines.append(f"{k}={v}")
            else:
                lines.append(k)
        elif entry[0] == "unified":
            _, unified_line, _ = entry
            lines.append(unified_line)
    Path(filename).write_text("\n".join(lines) + "\n")
    preview = "\n".join(lines[:5])
    print(
        f"{LOG_PREFIX} {filename} preview:\n"
        f"{preview}\n{'...' if len(lines) > 5 else ''}"
    )


def get_modules_and_roles() -> tuple[list[str], int, bool, bool]:
    """Parse modules and determine node roles from environment variables.

    Returns: modules, workers, is_coordinator, is_worker
    """
    modules_env = os.environ.get("MINITRINO_MODULES", "")
    modules = [m.strip() for m in modules_env.split(",") if m.strip()]
    print(f"{LOG_PREFIX} MINITRINO_MODULES: {modules}")
    if "minitrino" not in modules:
        modules.append("minitrino")
        print(f"{LOG_PREFIX} Added 'minitrino' to modules list.")
    workers = int(os.environ.get("WORKERS", "0"))
    is_coordinator = os.environ.get("COORDINATOR", "false").lower() == "true"
    is_worker = os.environ.get("WORKER", "false").lower() == "true"
    print(
        f"{LOG_PREFIX} COORDINATOR={is_coordinator}, "
        f"WORKER={is_worker}, WORKERS={workers}"
    )
    return modules, workers, is_coordinator, is_worker


def generate_coordinator_config(modules: list[str], workers: int) -> None:
    """Generate coordinator configs."""
    print(f"{LOG_PREFIX} Generating coordinator configs...")
    base_cfgs = read_existing_config(f"{ETC_DIR}/config.properties")
    base_jvm_cfgs = read_existing_config(f"{ETC_DIR}/jvm.config")
    user_cfgs, user_jvm_cfg = collect_configs(modules, worker=False)
    # Special-case: node-scheduler.include-coordinator
    if workers > 0:
        user_env_cfg = os.environ.get("CONFIG_PROPERTIES", "")
        user_explicit_true = any(
            line.strip() == "node-scheduler.include-coordinator=true"
            for line in user_env_cfg.splitlines()
        )
        if not user_explicit_true:
            print(
                f"{LOG_PREFIX} Setting node-scheduler.include-coordinator=false "
                f"(workers present, not overridden by user)"
            )
            user_cfgs = [
                c
                for c in user_cfgs
                if not (
                    c[0] == "key_value" and c[1] == "node-scheduler.include-coordinator"
                )
            ]
            user_cfgs.append(
                ("key_value", "node-scheduler.include-coordinator", "false")
            )
    user_cfgs = merge_password_authenticators(user_cfgs)
    final_cfgs = merge_configs(base_cfgs, user_cfgs)
    final_jvm_cfgs = merge_configs(base_jvm_cfgs, user_jvm_cfg, is_jvm=True)
    write_config_file(f"{ETC_DIR}/config.properties", final_cfgs)
    write_config_file(f"{ETC_DIR}/jvm.config", final_jvm_cfgs)
    print(f"{LOG_PREFIX} Coordinator config generation complete.")


def generate_worker_config(modules: list[str]) -> None:
    """Generate worker configs."""
    print(f"{LOG_PREFIX} Generating worker configs...")
    with open(f"{ETC_DIR}/config.properties", "w") as f:
        f.write(WORKER_CONFIG_PROPS)
    base_cfgs = read_existing_config(f"{ETC_DIR}/config.properties")
    base_jvm_cfgs = read_existing_config(f"{ETC_DIR}/jvm.config")
    user_cfgs, user_jvm_cfg = collect_configs(modules, worker=True)
    user_cfgs = merge_password_authenticators(user_cfgs)
    final_cfgs = merge_configs(base_cfgs, user_cfgs)
    final_jvm_cfgs = merge_configs(base_jvm_cfgs, user_jvm_cfg, is_jvm=True)
    write_config_file(f"{ETC_DIR}/config.properties", final_cfgs)
    write_config_file(f"{ETC_DIR}/jvm.config", final_jvm_cfgs)
    print(f"{LOG_PREFIX} Worker config generation complete.")


def main():
    """Run config generation."""
    print(f"{LOG_PREFIX} Starting config generation...")
    modules, workers, is_coordinator, is_worker = get_modules_and_roles()
    if is_coordinator:
        generate_coordinator_config(modules, workers)
    if is_worker:
        generate_worker_config(modules)
    print(f"{LOG_PREFIX} Config generation finished.")


if __name__ == "__main__":
    main()
