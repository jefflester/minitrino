# OAuth2 Module

This module secures Trino with OAuth2 authentication.

~ Temporary development notes ~

Prior to running:

- Authenticate to the Github container registry (ghcr) -
  [(docs)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- **Must** set this in `/etc/hosts` file on your machine: `127.0.0.1
  host.docker.internal`
  [(docs)](https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host).
  This allows the callbacks/redirects between SEP and OAuth2 services to take
  place over your host instead of within the container network. The end result
  is that the redirect screen actually appears on your web browser.
  - As a result of the above, the DNS references within the Compose YAML refer
    to two different hostnames for the OAuth2 server: `oauth2-server:8100` and
    `host.docker.internal:8100`. SEP specifically needs its configuration to
    point to `host.docker.internal` in order for the user-facing browser
    redirects to work.
- Needed to implement a healthcheck to ensure that the OAuth2 server is running
  before trying to pull the OAuth2 server's certificate in SEP

JKS command to generate OAuth2 server certificate:

    keytool -genkeypair \
      -alias oauth2-server \
      -keyalg RSA \
      -keystore keystore.jks \
      -keypass changeit \
      -validity 9999 \
      -storepass changeit \
      -dname "CN=host.docker.internal" \
      -ext san=dns:host.docker.internal,dns:oauth2-server,dns:localhost
