ARG STARBURST_VER
ARG UBUNTU_VER

FROM ubuntu:${UBUNTU_VER} AS base

RUN \
    apt-get update && apt-get install -y \
        curl \
        wget \
        telnet \
        sudo \
        vim \
        jq \
        tree \
        less \
        iputils-ping \
        ldap-utils \
        apache2-utils \
        python3 \
        python-is-python3 \
        python3-pip

ARG STARBURST_VER
FROM starburstdata/starburst-enterprise:${STARBURST_VER} AS mid

FROM base AS final

ARG USER=starburst
ARG UID=1000
ARG GROUP=root
ARG GID=0

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}

COPY --from=mid /usr/lib/starburst/bin/run-starburst /tmp/

ADD ./src/scripts/install.sh /tmp/
ADD ./src/scripts/install-java.sh /tmp/
ADD ./src/scripts/run-minitrino.sh /tmp/
ADD ./src/etc/starburst /etc/starburst

RUN \
    chmod +x /tmp/install.sh /tmp/install-java.sh  && \
    bash /tmp/install-java.sh ${USER} ${GROUP} ${UID} ${GID} && \
    bash /tmp/install.sh ${USER} ${GROUP} ${UID} ${GID}

EXPOSE 8080
USER ${USER}:${GROUP}
WORKDIR /etc/starburst/
ENV LANG=en_US.UTF-8
CMD ["/bin/sh", "-c", "/usr/lib/starburst/bin/run-minitrino.sh"]
