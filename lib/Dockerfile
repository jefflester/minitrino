ARG STARBURST_VER
FROM starburstdata/presto:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}
ENV PRESTO_CLI_PATH=/usr/local/bin/presto-cli

ADD ./modules/resources/wait-for-it.sh /opt/minipresto/

USER root
RUN set -euxo pipefail \
    && yum install -y wget \
        sudo \
    && usermod -aG wheel presto \
    && echo presto | passwd presto --stdin \
    && echo "presto ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && DIST=${STARBURST_VER:0:3} \
    && CLI_URL=https://repo1.maven.org/maven2/io/prestosql/presto-cli/"${DIST}"/presto-cli-"${DIST}"-executable.jar \
    && curl -fsSL "${CLI_URL}" > "${PRESTO_CLI_PATH}" \
    && chmod -v +x "${PRESTO_CLI_PATH}" \
    && chown presto:presto "${PRESTO_CLI_PATH}" \
    && ln -vs "${PRESTO_CLI_PATH}" \
    && echo OK

USER presto
WORKDIR /home/presto
