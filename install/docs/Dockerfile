ARG PYTHON_TAG
FROM ${PYTHON_TAG}

WORKDIR /docs

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy package files for installation
COPY pyproject.toml /tmp/minitrino/
COPY src/cli /tmp/minitrino/src/cli

# Install minitrino package with docs extras
# This provides all main dependencies (docker, click, etc.) + Sphinx packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir /tmp/minitrino[docs]

ENTRYPOINT ["bash"]
