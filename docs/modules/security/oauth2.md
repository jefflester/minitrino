# OAuth2 Authentication

Enable [OAuth2
authentication](https://trino.io/docs/current/security/oauth2.html) on the
coordinator.

## Usage

Provision the module:

```sh
minitrino provision -m oauth2
```

Once deployed, visit the UI on `https://localhost:8443` and work through the
authentication process. You will be redirected to a service on
`https://host.docker.internal:8100` to facilitate the OAuth2 flow.

## Prerequisites

Prior to deploying this module, you must:

- Authenticate to the Github container registry
  [(docs)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
  in order to pull the `ghcr.io/navikt/mock-oauth2-server` image.
- Add this DNS entry in the `/etc/hosts` file on your machine
  [(docs)](https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host):

```text
127.0.0.1    host.docker.internal
```

The `hosts` file modification allows for all Docker services to be exposed on
your host at `host.docker.internal:${PORT}`. This is a requirement given the
nature of the redirects and callbacks that occur during the OAuth2 credential
flow.

## Default OAuth2 Principals

The following OAuth2 principals are listed below, along with the usernames that
are mapped to them:

```{table}
| Email | Mapped User |
|:-----------------|:---------------|
| `admin@minitrino.com` | `admin` |
| `cachesvc@minitrino.com` | `cachesvc` |
| `bob@minitrino.com` | `bob` |
| `alice@minitrino.com` | `alice` |
| `metadata-user@minitrino.com` | `metadata-user` |
| `platform-user@minitrino.com` | `platform-user` |
| `test@minitrino.com` | `test` |
```

Using an email other than the ones listed above will result in a failed
authentication attempt.

## Dependent Modules

- [`tls`](tls.md#tls): Required for securing credentials in transit.
