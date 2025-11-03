ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG SERVICE_USER
ARG UBUNTU_VER=22.04

FROM ubuntu:${UBUNTU_VER} AS tarball

ARG CLUSTER_VER
ARG CLUSTER_DIST

COPY ./src/scripts/downloader.py /tmp/
RUN apt-get -y update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python3 && \
    python3 /tmp/downloader.py ${CLUSTER_VER} ${CLUSTER_DIST}

FROM tarball AS pruned

ARG CLUSTER_DIST
ARG KEEP_PLUGINS=""
ENV KEEP_PLUGINS=${KEEP_PLUGINS}
COPY ./src/scripts/prune_plugins.py /tmp/
RUN python3 /tmp/prune_plugins.py ${CLUSTER_DIST}

FROM ubuntu:${UBUNTU_VER} AS base

RUN \
    apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y upgrade && \
      apt-get install -y --no-install-recommends \
        curl \
        wget \
        telnet \
        sudo \
        gosu \
        vim \
        jq \
        tree \
        less \
        locales \
        zip unzip \
        iputils-ping \
        ldap-utils \
        krb5-user \
        apache2-utils \
        python3 python-is-python3 python3-pip && \
    locale-gen en_US.UTF-8

FROM base AS java-builder

ARG CLUSTER_VER
ARG SERVICE_USER

RUN useradd -m ${SERVICE_USER}

COPY ./src/scripts/install-java-builder.sh /tmp/
RUN chmod +x /tmp/install-java-builder.sh && \
    /tmp/install-java-builder.sh ${SERVICE_USER} ${CLUSTER_VER}

FROM base AS final

ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG SERVICE_USER
ARG SERVICE_UID=1000
ARG SERVICE_GROUP=root
ARG SERVICE_GID=0

ENV SERVICE_USER=${SERVICE_USER}
ENV CLUSTER_VER=${CLUSTER_VER}
ENV CLUSTER_DIST=${CLUSTER_DIST}

COPY --from=java-builder /home/${SERVICE_USER}/.sdkman/candidates/java/current /opt/java
COPY --from=java-builder --chown=${SERVICE_USER}:${SERVICE_GROUP} /tmp/tls-jvm /etc/${CLUSTER_DIST}/tls-jvm
ENV JAVA_HOME="/opt/java"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY ./src/scripts /tmp/
# Use --chown to set ownership during copy, avoiding duplication in RUN layer
COPY --chown=${SERVICE_USER}:${SERVICE_GROUP} ./src/etc/app-config /etc/${CLUSTER_DIST}
COPY --from=pruned --chown=${SERVICE_USER}:${SERVICE_GROUP} /usr/lib/${CLUSTER_DIST} /usr/lib/${CLUSTER_DIST}

RUN chmod +x /tmp/*.sh && \
    /tmp/install.sh ${SERVICE_USER} ${SERVICE_GROUP} ${SERVICE_UID} ${SERVICE_GID}

EXPOSE 8080
WORKDIR /etc/${CLUSTER_DIST}
ENV LANG=en_US.UTF-8

ENTRYPOINT ["bash", "-c", "/usr/lib/${CLUSTER_DIST}/bin/run-minitrino.sh"]
