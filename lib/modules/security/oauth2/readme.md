# OAuth2 Module

This module secures Trino with OAuth2 authentication.

## Usage

Prior to deploying this module, you must authenticate to the Github container
registry
[(docs)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
in order to pull the `ghcr.io/navikt/mock-oauth2-server` image. Additionally,
you must set this in the `/etc/hosts` file on your machine
[(docs)](https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host):

    127.0.0.1    host.docker.internal

The `hosts` file modification allows for all Docker services to be exposed on
your host at `host.docker.internal:${PORT}`. This is a requirement given the
nature of the redirects and callbacks that occur during the OAuth2 flow.

To provision this module, run:

    minitrino --env STARBURST_VER=<ver> provision --module oauth2

Once deployed, visit Starburst on `https://localhost:8443` and work through the
authentication process. You will be redirected to a service on
`https://host.docker.internal:8100` to facilitate the OAuth2 flow.

On each page, you will need to bypass your browser's security warnings since the
TLS certificates are self-signed. On Google Chrome, you can bypass this warning
by typing `thisisunsafe` with the browser window in focus.

## Development Notes

`host.docker.internal` allows the callbacks/redirects between SEP and OAuth2
services to take place over your host instead of within the container network.
The end result is that the redirect screen actually appears on your web browser.

As a result of the above, the DNS references within the Compose YAML refer to
two different hostnames for the OAuth2 server: `oauth2-server:8100` and
`host.docker.internal:8100`. SEP specifically needs its configuration to point
to `host.docker.internal` in order for the user-facing browser redirects to
work.

The `keytool` command used to generate the OAuth2 server certificate:

    keytool -genkeypair \
      -alias oauth2-server \
      -keyalg RSA \
      -keystore keystore.jks \
      -keypass changeit \
      -validity 9999 \
      -storepass changeit \
      -dname "CN=host.docker.internal" \
      -ext san=dns:host.docker.internal,dns:oauth2-server,dns:localhost
