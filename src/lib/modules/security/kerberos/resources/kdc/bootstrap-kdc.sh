#!/bin/sh
set -e

REALM="MINITRINO.COM"
: "${WORKERS:=0}"

# ──────────────────────────────────────────────────────────────────────────────
# 1.  Coordinator HTTP principal
# ──────────────────────────────────────────────────────────────────────────────
COORD_HOST="minitrino-${CLUSTER_NAME}"
kadmin.local -q "addprinc -randkey HTTP/${COORD_HOST}@${REALM}" 2>/dev/null || true
kadmin.local -q "ktadd  -k /keytabs/cluster.keytab HTTP/${COORD_HOST}@${REALM}"

# ──────────────────────────────────────────────────────────────────────────────
# 2.  Worker HTTP principals (WORKERS = count OR list)
# ──────────────────────────────────────────────────────────────────────────────
case "${WORKERS}" in
  *[!0-9]* )
    for host in $(printf '%s\n' "${WORKERS}" | tr ', ' '\n' | sed '/^$/d'); do
        princ="HTTP/${host}@${REALM}"
        kadmin.local -q "addprinc -randkey ${princ}" 2>/dev/null || true
        kadmin.local -q "ktadd -k /keytabs/cluster.keytab ${princ}"
    done
    ;;
  * )
    if [ "${WORKERS}" -gt 0 ] 2>/dev/null; then
        for i in $(seq 1 "${WORKERS}"); do
            host="minitrino-worker-${i}-${CLUSTER_NAME}"
            princ="HTTP/${host}@${REALM}"
            kadmin.local -q "addprinc -randkey ${princ}" 2>/dev/null || true
            kadmin.local -q "ktadd -k /keytabs/cluster.keytab ${princ}"
        done
    fi
    ;;
esac

# ──────────────────────────────────────────────────────────────────────────────
# 3.  Human & service users  (each gets its **own** keytab)
# ──────────────────────────────────────────────────────────────────────────────
for upn in admin cachesvc bob alice metadata-user platform-user test; do
    full="${upn}@${REALM}"
    # create principal with demo password if not present
    kadmin.local -q "addprinc -pw changeit ${full}" 2>/dev/null || true
    # export a dedicated keytab for that single principal
    kadmin.local -q "ktadd -k /keytabs/${upn}.keytab ${full}"
done

chmod 0640 /keytabs/*.keytab
echo "Kerberos bootstrap complete."

tail -f /dev/null
