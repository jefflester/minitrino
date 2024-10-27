# -- Base layer --
ARG UBUNTU_VER
ARG STARBURST_VER
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
        zip unzip \
        iputils-ping \
        ldap-utils \
        apache2-utils \
        python3 \
        python-is-python3 \
        python3-pip && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/*

# -- Mid layer --
ARG STARBURST_VER
FROM starburstdata/starburst-enterprise:${STARBURST_VER} AS mid

# -- Final layer --
FROM base AS final

ARG STARBURST_VER
ARG USER=starburst
ARG UID=1000
ARG GROUP=root
ARG GID=0

ENV STARBURST_VER=${STARBURST_VER}
ENV SDKMAN_DIR="/home/${USER}/.sdkman"
ENV JAVA_HOME="/home/${USER}/.sdkman/candidates/java/current"
ENV PATH="/home/${USER}/.sdkman/candidates/java/current/bin:${PATH}"

COPY --from=mid /etc/starburst/jvm.config /tmp/
COPY --from=mid /usr/lib/starburst/bin/run-starburst /tmp/

ADD ./src/scripts/install.sh /tmp/
ADD ./src/scripts/run-minitrino.sh /tmp/
ADD ./src/etc/starburst /etc/starburst

RUN \
    chmod +x /tmp/install.sh && \
    bash /tmp/install.sh ${USER} ${GROUP} ${UID} ${GID}

ADD ./src/scripts/install-java.sh /tmp/

RUN chmod +x /tmp/install-java.sh

USER ${USER}:${GROUP}
RUN bash /tmp/install-java.sh ${USER} 

EXPOSE 8080
WORKDIR /etc/starburst/
ENV LANG=en_US.UTF-8
CMD ["/bin/sh", "-c", "/usr/lib/starburst/bin/run-minitrino.sh"]
