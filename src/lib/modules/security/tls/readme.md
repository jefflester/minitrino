# Password File Authentication Module

This module configures server TLS for the Trino container using a self-signed
certificate.

## Client Keystore and Truststore

The Java keystore and truststore needed for clients and drivers to securely
connect to Trino are located in a volume mount `~/.minitrino/tls-mnt`. These two
files are transient and will be automatically replaced whenever Minitrino is
provisioned with a security module that enables SSL.

## Accessing Trino with the CLI

Via Docker:

    docker exec -it trino trino-cli \
        --server https://trino:8443 \
        --truststore-path /etc/starburst/tls-mnt/truststore.jks \
        --truststore-password changeit

Via Host Machine:

    trino-cli-xxx-executable.jar \
        --server https://localhost:8443 \
        --truststore-path ~/.minitrino/tls-mnt/truststore.jks 
        --truststore-password changeit

## Accessing the Trino Web UI

Open a web browser and go to <https://localhost:8443>. To have the browser
accept the self-signed certificate, do the following:

**Chrome**: Click anywhere on the page and type `thisisunsafe`.

**Firefox**: Click on the **Advanced** button and then click on **Accept the
Risk and Continue**.

**Safari**: Click on the button **Show Details** and then click the link **visit
this website**.
