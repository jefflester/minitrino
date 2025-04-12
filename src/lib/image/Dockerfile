ARG UBUNTU_VER
ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG BUILD_USER

FROM ubuntu:${UBUNTU_VER} AS base

ARG BUILD_USER

ENV SDKMAN_DIR="/home/${BUILD_USER}/.sdkman"
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
    chmod +x \
        /tmp/install.sh \
        /tmp/install-java.sh \
        /tmp/run-minitrino.sh

FROM base 

ARG CLUSTER_VER
ARG CLUSTER_DIST
ARG BUILD_USER
ARG UID=1000
ARG GROUP=root
ARG GID=0

ENV CLUSTER_VER=${CLUSTER_VER}
ENV CLUSTER_DIST=${CLUSTER_DIST}

COPY ./src/etc/app-config /etc/${CLUSTER_DIST}

RUN /tmp/install.sh ${BUILD_USER} ${GROUP} ${UID} ${GID}

EXPOSE 8080
WORKDIR /etc/${CLUSTER_DIST}
ENV LANG=en_US.UTF-8

USER ${BUILD_USER}:${GROUP}
ENTRYPOINT bash -c "/usr/lib/${CLUSTER_DIST}/bin/run-minitrino.sh"
