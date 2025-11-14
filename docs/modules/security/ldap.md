# LDAP Authentication

Enable
[LDAP password authentication](https://trino.io/docs/current/security/ldap.html)
on the coordinator.

## Usage

Provision the module:

```sh
minitrino provision -m ldap
```

{{ connect_trino_cli }}

Authenticate to the coordinator using the Trino CLI:

```sh
trino-cli --server https://minitrino:8443 \
  --truststore-path /etc/"${CLUSTER_DIST}"/tls/truststore.jks \
  --truststore-password changeit \
  --user bob --password
```

Confirm authentication by running a query:

```sql
SHOW SCHEMAS FROM tpch;
```

Access the web UI at `https://localhost:8443` and authenticate with one of the
sets of credentials listed below.

## Default Usernames and Passwords

```{table}
| Username | Password |
|:-----------------|:---------------|
| `admin` | `trinoRocks15` |
| `cachesvc` | `trinoRocks15` |
| `bob` | `trinoRocks15` |
| `alice` | `trinoRocks15` |
| `metadata-user` | `trinoRocks15` |
| `platform-user` | `trinoRocks15` |
| `test` | `trinoRocks15` |
```

## Add a New LDAP User

Open a shell to the coordinator:

```sh
minitrino exec -i
```

Create an LDIF file with the new user information:

```sh
cat << EOF > foo.ldif
# foo, minitrino.com
dn: uid=foo,dc=minitrino,dc=com
changetype: add
uid: foo
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
objectClass: top
cn: foo
sn: foo
mail: foo@minitrino.com
userPassword: trinoRocks15
EOF
```

Use the `ldapmodify` tool to add the new user:

```sh
ldapmodify -x -D "cn=admin,dc=minitrino,dc=com" \
  -w trinoRocks15 -H ldaps://ldap:636 -f foo.ldif
```

## Add a User to a Group

You can add a user to a group by creating an LDIF file and using `ldapmodify` to
apply the change.

Open a shell to the coordinator:

```sh
minitrino exec -i
```

Create an LDIF file to add the user to the group:

```sh
cat << EOF > add-foo-to-group.ldif
dn: cn=clusteradmins,ou=groups,dc=minitrino,dc=com
changetype: modify
add: member
member: uid=foo,dc=minitrino,dc=com
EOF
```

Apply the change using `ldapmodify`:

```sh
ldapmodify -x -D "cn=admin,dc=minitrino,dc=com" \
  -w trinoRocks15 -H ldaps://ldap:636 -f add-foo-to-group.ldif
```

This will add `uid=foo,dc=minitrino,dc=com` as a `member` of the `clusteradmins`
group.

## Dependent Modules

- [`tls`](tls.md#tls): Required for securing credentials in transit.
