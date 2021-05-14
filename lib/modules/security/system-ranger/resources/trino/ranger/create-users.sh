#!/usr/bin/env bash

set -ex 

starburst-ranger-cli user create \
    --from-file=/tmp/ranger/usr/alice.json \
    --properties=/etc/starburst/access-control.properties

starburst-ranger-cli user create \
    --from-file=/tmp/ranger/usr/bob.json \
    --properties=/etc/starburst/access-control.properties
