# This exists because of presto-cli mismatches between images. The Dockerfile
# will ensure that invoking `presto` from the shell brings up the Presto CLI all
# the way back to early 312-e versions.

ARG STARBURST_VER
FROM starburstdata/presto:${STARBURST_VER}

ARG STARBURST_VER
ENV STARBURST_VER=${STARBURST_VER}

RUN set -euxo pipefail \
    && cd /usr/lib/presto/lib/ || exit \
    && DIST=${STARBURST_VER:0:3}e \
    && S3_URL=https://s3.us-east-2.amazonaws.com/software.starburstdata.net \
    && curl -fsSL "${S3_URL}"/"${DIST}"/"${STARBURST_VER}"/presto-cli-"${STARBURST_VER}"-executable.jar -o presto-cli \
    && chmod -v +x presto-cli \
    && echo 'alias presto="/usr/lib/presto/lib/presto-cli"' >> ~/.bash_profile \
    && echo 'alias presto="/usr/lib/presto/lib/presto-cli"' >> ~/.bashrc \
    && exec bash -l \
    && echo OK

WORKDIR /home/presto
