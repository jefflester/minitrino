# This exists because of presto-cli mismatches between images. The Dockerfile
# will ensure that invoking `presto` from the shell brings up the Presto CLI all
# the way back to early 312-e versions. This Dockerfile also handles any
# commands that need to be executed as tbe root user, and then sets the default
# user back to presto.

# TODO: Check if presto user exists before doing presto-specific things
# TODO: How to handle older images that use root as default...

ARG STARBURST_VER
FROM starburstdata/presto:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}

ADD ./modules/resources/wait-for-it.sh /opt/minipresto/

USER root
RUN set -euxo pipefail \
    && yum install -y wget \
        sudo \
    && usermod -aG wheel presto \
    && echo presto | passwd presto --stdin \
    && echo "presto ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && cd /usr/lib/presto/lib/ || exit \
    && DIST=${STARBURST_VER:0:3} \
    && CLI_URL=https://repo1.maven.org/maven2/io/prestosql/presto-cli/"${DIST}"/presto-cli-"${DIST}"-executable.jar \
    && curl -fsSL "${CLI_URL}" -o presto-cli \
    && chmod -v +x presto-cli \
    && chown presto:presto presto-cli \
    && runuser -l presto -c 'echo alias presto="/usr/lib/presto/lib/presto-cli" >> ~/.bash_profile \
        && echo alias presto="/usr/lib/presto/lib/presto-cli" >> ~/.bashrc \
        && exec bash -l' \
    && echo OK

USER presto
WORKDIR /home/presto
