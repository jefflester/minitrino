ARG STARBURST_VER
FROM starburstdata/starburst-enterprise:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}
ENV TRINO_CLI_PATH=/usr/local/bin/trino-cli

ADD ./dockerfile-resources/wait-for-it.sh /opt/minitrino/
ADD ./dockerfile-resources/configure.sh /opt/minitrino/

USER root
RUN set -euxo pipefail \
    && SHARED_SECRET=$(echo minitrinoRocks15 | base64) \
    && echo "internal-communication.shared-secret=${SHARED_SECRET}" >> /etc/starburst/config.properties \
    && chmod +x /opt/minitrino/configure.sh \
    && /opt/minitrino/configure.sh

USER starburst
WORKDIR /home/trino
