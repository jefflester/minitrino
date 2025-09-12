# TLS

Enable [HTTPS](https://trino.io/docs/current/security/tls.html) on the
coordinator using a self-signed certificate.

## Usage

Provision the module:

```sh
minitrino provision -m tls
```

{{ connect_trino_cli }}

Connect to the coordinator over HTTPS:

```sh
trino-cli --server https://minitrino:8443 \
  --truststore-path /etc/"${CLUSTER_DIST}"/tls/truststore.jks \
  --truststore-password changeit \
  --user bob --password
```

Confirm the TLS handshake succeeded by running a query:

```sql
SHOW SCHEMAS FROM tpch;
```

## Client Keystore and Truststore

The Java keystore and truststore required for clients and drivers are available
on the host machine at `~/.minitrino/tls/${CLUSTER_NAME}/`.

The truststore is also available in the container at
`/etc/${CLUSTER_DIST}/tls/truststore.jks`.

```sh
minitrino exec -i 'ls -l /etc/${CLUSTER_DIST}/tls/'
```

```text
-rw-rw-r-- 1 trino root 3454 Jun 19 22:02 keystore.jks
-rw-rw-r-- 1 trino root 1460 Jun 19 22:02 minitrino_cert.cer
-rw-rw-r-- 1 trino root 1414 Jun 19 22:02 truststore.jks
```

## Accessing the Coordinator Over HTTPS

### Using Docker

```sh
minitrino exec -i 'trino-cli \
  --server https://minitrino:8443 \
  --truststore-path /etc/${CLUSTER_DIST}/tls/truststore.jks \
  --truststore-password changeit'
```

Certificate trust can be bypassed by using the `--insecure` flag:

```sh
minitrino exec -i 'trino-cli \
  --server https://minitrino:8443 \
  --insecure'
```

### Using Host Machine

```sh
trino-cli-executable.jar \
  --server https://localhost:8443 \
  --truststore-path ~/.minitrino/${CLUSTER_NAME}/tls/truststore.jks \
  --truststore-password changeit
```

### Using the Web UI

Open a browser and navigate to `https://localhost:8443`.

```{table}
| Browser | How to Accept Self-Signed Certificate |
|:----------|:------------------------------------------------------|
| Chrome | Click anywhere and type `thisisunsafe` |
| Firefox | Click **Advanced** → **Accept the Risk and Continue** |
| Safari | Click **Show Details** → **visit this website** |
```
