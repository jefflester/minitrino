ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG SERVICE_USER
ARG UBUNTU_VER=22.04

FROM ubuntu:${UBUNTU_VER} AS tarball

ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG KEEP_PLUGINS=""

ENV KEEP_PLUGINS=${KEEP_PLUGINS}

COPY ./src/scripts/download-tarball.py /tmp/
RUN apt-get -y update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python3 && \
    KEEP_PLUGINS="${KEEP_PLUGINS}" \
        python3 /tmp/download-tarball.py ${CLUSTER_VER} ${CLUSTER_DIST}

FROM ubuntu:${UBUNTU_VER} AS base

ARG SERVICE_USER

ENV SDKMAN_DIR="/home/${SERVICE_USER}/.sdkman"
ENV JAVA_HOME="${SDKMAN_DIR}/candidates/java/current"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY ./src/scripts /tmp/

RUN \
    apt-get -y update && \
    apt-get -y upgrade && apt-get install -y --no-install-recommends \
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
        apache2-utils \
        python3 python-is-python3 python3-pip && \
    locale-gen en_US.UTF-8 && \
    chmod +x /tmp/*.sh

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

COPY --from=tarball /usr/lib/${CLUSTER_DIST} /usr/lib/${CLUSTER_DIST}
COPY ./src/etc/app-config /etc/${CLUSTER_DIST}

RUN /tmp/install.sh ${SERVICE_USER} ${SERVICE_GROUP} ${SERVICE_UID} ${SERVICE_GID}

EXPOSE 8080
WORKDIR /etc/${CLUSTER_DIST}
ENV LANG=en_US.UTF-8

ENTRYPOINT ["bash", "-c", "/usr/lib/${CLUSTER_DIST}/bin/run-minitrino.sh"]