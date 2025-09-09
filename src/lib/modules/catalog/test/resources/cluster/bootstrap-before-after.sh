#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    echo "hello world" > /tmp/bootstrap-before.txt
}

after_start() {
    echo "hello world" > /tmp/bootstrap-after.txt
}
