ARG STARBURST_VER
FROM starburstdata/trino:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}
ENV TRINO_CLI_PATH=/usr/local/bin/trino-cli

ADD ./modules/resources/wait-for-it.sh /opt/minitrino/

USER root
RUN set -euxo pipefail \
    && yum install -y wget \
        sudo \
    && usermod -aG wheel trino \
    && echo trino | passwd trino --stdin \
    && echo "trino ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && DIST=${STARBURST_VER:0:3} \
    && CLI_URL=https://repo1.maven.org/maven2/io/trinodb/trino-cli/"${DIST}"/trino-cli-"${DIST}"-executable.jar \
    && curl -fsSL "${CLI_URL}" > "${TRINO_CLI_PATH}" \
    && chmod -v +x "${TRINO_CLI_PATH}" \
    && chown --reference=/usr/lib/trino/etc/config.properties "${TRINO_CLI_PATH}" \
    && ln -vs "${TRINO_CLI_PATH}" \
    && echo OK

USER trino
WORKDIR /home/trino
