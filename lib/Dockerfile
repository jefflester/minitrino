ARG STARBURST_VER
FROM starburstdata/starburst-enterprise:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}
ENV TRINO_CLI_PATH=/usr/local/bin/trino-cli

ADD ./modules/resources/wait-for-it.sh /opt/minitrino/

USER root
RUN set -euxo pipefail \
    && yum install -y wget \
        sudo \
    && usermod -aG wheel starburst \
    && echo starburst | passwd starburst --stdin \
    && echo "starburst ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && DIST=${STARBURST_VER:0:3} \
    && CLI_URL=https://repo1.maven.org/maven2/io/trino/trino-cli/"${DIST}"/trino-cli-"${DIST}"-executable.jar \
    && curl -fsSL "${CLI_URL}" > "${TRINO_CLI_PATH}" \
    && chmod -v +x "${TRINO_CLI_PATH}" \
    && chown --reference=/etc/starburst/config.properties "${TRINO_CLI_PATH}" \
    && ln -vs "${TRINO_CLI_PATH}" \
    && echo OK

USER starburst
WORKDIR /home/trino
