# Troubleshooting

This guide covers common issues you may encounter when using Minitrino and their
solutions.

## Quick Diagnostics

Before diving into specific issues, try these general diagnostic steps:

**Run with verbose output:**

```sh
minitrino -v --log-level DEBUG <command>
```

**Check Docker status:**

```sh
docker info
docker ps -a
```

**Check Minitrino version:**

```sh
minitrino version
```

**View container logs:**

```sh
docker logs minitrino-default
docker logs <container-name>
```

---

## Common Issues and Solutions

### Port Conflicts

**Symptom:** Error message indicating port already in use, or services fail to
start.

**Detection:**

```sh
# Check if a port is in use
lsof -i :8080
# or
netstat -an | grep 8080
```

**Solution:** Override default ports using environment variables:

```sh
# Override a single port
minitrino -v -e __PORT_MINITRINO=8081 provision

# Override multiple ports
minitrino -v \
  -e __PORT_MINITRINO=8081 \
  -e __PORT_POSTGRES=5433 \
  provision -m postgres
```

**Available Port Variables:** All port variables follow the pattern
`__PORT_<SERVICE>`. See the
[environment variables documentation](environment-variables-and-config.md#port-variables)
for the complete list:

- `__PORT_MINITRINO` (default: 8080)
- `__PORT_MINITRINO_TLS` (default: 8443)
- `__PORT_POSTGRES` (default: 5432)
- `__PORT_MYSQL` (default: 3306)
- `__PORT_MINIO` (default: 9000)
- And more...

---

### Docker Out of Memory (OOM) Errors

**Symptom:** Container exits unexpectedly with status 137, or Docker logs show
"OOMKilled".

**Detection:**

```sh
# Check if container was OOM killed
docker inspect minitrino-default | grep OOMKilled

# View container exit code
docker ps -a --filter name=minitrino
```

**Solution:** Increase Docker's memory allocation:

**Docker Desktop (Mac/Windows):**

1. Docker Desktop → Settings → Resources
1. Increase Memory to 8GB+ (recommended for multiple modules)
1. Click "Apply & Restart"

**Linux:** Docker uses host memory directly. Check available memory:

```sh
free -h
```

For problematic containers, you may need to reduce JVM heap:

```sh
minitrino -v -e JVM_CONFIG='-Xmx2G' provision
```

**Trino JVM Memory Settings:** Default JVM settings in `jvm.config` may be too
high. Override with:

```sh
minitrino -v -e JVM_CONFIG=$'-Xmx4G\n-Xms2G' provision
```

---

### Module Version Incompatibility

**Symptom:** Module fails to start, or configuration errors appear in logs.

**Detection:** Check module version requirements:

```sh
minitrino modules -m <module> --json | jq '.<module>.versions'
```

**Cause:** Some modules have version constraints (e.g., `spooling-protocol`
requires Trino 466+).

**Solution:**

1. **Check module compatibility:**

   ```sh
   # View your current Trino/Starburst version
   minitrino version

   # Check module's version requirements
   cat ~/.minitrino/lib/modules/<type>/<module>/metadata.json
   ```

1. **Use a compatible version:**

   ```sh
   minitrino -v -e CLUSTER_VER=476 provision -m <module>
   ```

1. **Override module configuration** (advanced): Edit the module's YAML or
   properties files in `~/.minitrino/lib/modules/<type>/<module>/`.

---

### ARM64 Mac Issues (Apple Silicon)

**Symptom:** Container fails to start with "exec format error" or platform
mismatch warnings.

**Affected Modules:**

- `sqlserver` - SQL Server requires x86_64 emulation
- `db2` - Db2 requires x86_64 emulation
- Some Java-based modules may have ARM64 compatibility issues

**Detection:**

```sh
# Check your architecture
uname -m  # Should show "arm64" on Apple Silicon

# Check Docker platform support
docker info | grep -i architecture
```

**Solutions:**

**1. Enable Rosetta 2 Emulation (Recommended):**

- Docker Desktop → Settings → General
- Enable "Use Virtualization Framework"
- Enable "VirtioFS" file sharing
- Restart Docker Desktop

**2. Force x86_64 Platform:** Set platform environment variable:

```sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
minitrino -v provision -m db2
```

**3. Use Alternative Modules:**

- Instead of `sqlserver`, consider `postgres` or `mysql`
- Instead of `db2`, consider `postgres` or other OSS databases

---

### Container Startup Failures

**Symptom:** Container starts but immediately exits, or never reaches "healthy"
state.

**Diagnosis Steps:**

1. **Check container logs:**

   ```sh
   # View logs for the coordinator
   docker logs minitrino-default

   # View logs for a specific module service
   docker logs <container-name>

   # Follow logs in real-time
   docker logs -f minitrino-default
   ```

1. **Check container status:**

   ```sh
   # View all containers
   minitrino resources --container

   # Inspect container details
   docker inspect minitrino-default
   ```

1. **Check health check status:**

   ```sh
   docker inspect minitrino-default | jq '.[0].State.Health'
   ```

**Common Causes:**

- **Configuration errors:** Check `/etc/trino/` or `/etc/starburst/` config
  files
- **Bootstrap script failures:** Check bootstrap logs in container
- **Port conflicts:** See [Port Conflicts](#port-conflicts) section
- **Memory issues:** See [Docker OOM](#docker-out-of-memory-oom-errors) section
- **Missing dependencies:** Check module's `dependentModules` in metadata.json

**Log Locations Inside Container:**

```sh
docker exec -it minitrino-default bash

# Trino/Starburst logs
cat /data/trino/var/log/server.log
cat /data/starburst/var/log/server.log

# Bootstrap script logs (if bootstrap failed)
ls /tmp/minitrino/bootstrap/
```

---

### Bootstrap Script Failures

**Symptom:** Container starts but module functionality doesn't work, or
provisioning hangs during bootstrap.

**Detection:**

```sh
# Check container logs for bootstrap execution
docker logs minitrino-default 2>&1 | grep -i bootstrap

# Look for "PRE START BOOTSTRAPS COMPLETED" and "POST START BOOTSTRAPS COMPLETED"
docker logs minitrino-default 2>&1 | grep "BOOTSTRAP"
```

**Common Causes:**

1. **Script syntax errors:** Check bootstrap script for bash errors
1. **External service unavailable:** Bootstrap may wait for services (e.g.,
   Elasticsearch, databases)
1. **Permission issues:** Bootstrap runs as root initially, then ownership
   changes
1. **Network issues:** Bootstrap may need to download resources

**Debugging:**

1. **Check bootstrap script exists:**

   ```sh
   docker exec minitrino-default ls -la /mnt/bootstrap/
   ```

1. **Manually run bootstrap:**

   ```sh
   docker exec -it minitrino-default bash
   bash -x /tmp/minitrino/bootstrap/<module>/<script>.sh
   ```

1. **Force re-execution:** Minitrino tracks bootstrap execution via checksums.
   Force re-execution by removing checksum:

   ```sh
   docker exec minitrino-default rm /etc/trino/.minitrino/bootstrap_checksums.json
   docker restart minitrino-default
   ```

1. **Review bootstrap script:** Check the script at
   `~/.minitrino/lib/modules/<type>/<module>/resources/bootstrap/`

**Note:** Bootstrap scripts are only re-executed if their content changes. After
modifying a bootstrap script, destroy and re-provision the environment.

---

### License File Issues (Enterprise Modules)

**Symptom:** Enterprise module fails with "License not found" or validation
errors.

**Solutions:**

1. **Verify license path:**

   ```sh
   # Check if LIC_PATH is set
   echo $LIC_PATH

   # Verify file exists and is readable
   ls -la $LIC_PATH
   ```

1. **Set license path:**

   ```sh
   # Method 1: Environment variable
   export LIC_PATH=/path/to/starburstdata.license
   minitrino provision -m insights

   # Method 2: Config file
   minitrino config
   # Add: LIC_PATH=/path/to/starburstdata.license

   # Method 3: Command line
   minitrino -e LIC_PATH=/path/to/starburstdata.license provision -m insights
   ```

1. **Verify license validity:**
   - Check expiration date
   - Ensure license supports the features you're using
   - Contact Starburst support if license appears invalid

1. **Check license mount:**

   ```sh
   # Verify license is mounted in container
   docker exec minitrino-default ls -la /mnt/etc/lic/starburstdata.license
   ```

---

### Network and Docker Context Issues

**Symptom:** Cannot connect to services, DNS resolution failures, or Docker
commands hang.

**Docker Context Issues:**

1. **Check active context:**

   ```sh
   docker context ls
   docker context show
   ```

1. **Switch contexts:**

   ```sh
   # Use default Docker Desktop
   docker context use default

   # Use Colima
   docker context use colima

   # Use OrbStack
   docker context use orbstack
   ```

1. **Set DOCKER_HOST explicitly:**

   ```sh
   export DOCKER_HOST="unix://${HOME}/.docker/run/docker.sock"
   minitrino -v provision
   ```

**Network Connectivity:**

1. **Check Docker network:**

   ```sh
   docker network ls | grep minitrino
   docker network inspect minitrino-network
   ```

1. **Test container connectivity:**

   ```sh
   # From host to container
   curl http://localhost:8080

   # From container to container
   docker exec minitrino-default ping postgres
   ```

1. **DNS resolution:**

   ```sh
   # Check if containers can resolve each other
   docker exec minitrino-default nslookup postgres
   ```

**Firewall Issues:**

- Check macOS firewall settings (System Preferences → Security)
- Check corporate VPN interference
- Try disabling firewall temporarily to isolate issue

---

### Cluster Resource Cleanup Issues

**Symptom:** Old containers/volumes interfere with new deployments, or disk
space fills up.

**Solutions:**

1. **Clean shutdown and removal:**

   ```sh
   # Stop cluster
   minitrino down

   # Remove all Minitrino resources
   minitrino remove --volumes --images
   ```

1. **Remove specific module volumes:**

   ```sh
   # Remove volumes for a specific module
   minitrino remove --volumes --label org.minitrino.module.catalog.hive=true
   ```

1. **Force cleanup:**

   ```sh
   # Kill all Minitrino containers
   docker ps -a | grep minitrino | awk '{print $1}' | xargs docker rm -f

   # Remove all Minitrino volumes
   docker volume ls | grep minitrino | awk '{print $2}' | xargs docker volume rm
   ```

1. **Docker system prune (use with caution):**

   ```sh
   # Clean up all unused Docker resources
   docker system prune -a --volumes
   ```

---

### Library Version Mismatch

**Symptom:** Error message "Library version mismatch" or commands fail with
version errors.

**Detection:**

```sh
minitrino version
# CLI Version: 3.0.0
# Library Version: 2.2.4  ← Mismatch!
```

**Solution:** Install the matching library version:

```sh
minitrino -v lib-install
```

**Note:** CLI and library versions must match. Always run `lib-install` after
upgrading the CLI.

---

### Module Not Found After Upgrade

**Symptom:** Previously working module is not recognized after upgrade.

**Causes:**

1. Module was removed in new version
1. Module was renamed
1. Custom module was overwritten during library upgrade

**Solutions:**

1. **Check release notes:** Visit
   [github.com/jefflester/minitrino/releases](https://github.com/jefflester/minitrino/releases)
   to see if module was removed or renamed

1. **List available modules:**

   ```sh
   minitrino modules
   ```

1. **Restore custom module from backup:**

   ```sh
   # If you backed up before upgrading
   cp -r ~/backups/my-custom-module ~/.minitrino/lib/modules/catalog/
   ```

1. **Check module directory:**

   ```sh
   ls ~/.minitrino/lib/modules/catalog/
   ls ~/.minitrino/lib/modules/admin/
   ls ~/.minitrino/lib/modules/security/
   ```

---

## Still Having Issues?

If none of these troubleshooting tips resolve your issue:

1. **Run with verbose output:**

   ```sh
   minitrino -v --log-level DEBUG provision ...
   ```

1. **Collect diagnostic information:**

   ```sh
   # Docker info
   docker info > docker-info.txt

   # Container status
   minitrino resources > resources.txt

   # Container logs
   docker logs minitrino-default > coordinator-logs.txt 2>&1
   ```

1. **File a GitHub issue** with:
   - Minitrino version (`minitrino version`)
   - Docker version (`docker --version`)
   - OS and architecture (`uname -a`)
   - Full error output
   - Module(s) being used
   - Diagnostic information collected above

See [Reporting Bugs](reporting-bugs-and-contributing) for more information.

---

## Additional Resources

- [Installation and Upgrades](installation-and-upgrades) - Setup and upgrade
  procedures
- [Environment Variables](environment-variables-and-config) - Configuration
  options
- [CLI Reference](cli-reference) - Complete command documentation
- [GitHub Issues](https://github.com/jefflester/minitrino/issues) - Search
  existing issues
