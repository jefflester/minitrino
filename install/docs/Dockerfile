ARG PYTHON_TAG
FROM ${PYTHON_TAG}

WORKDIR /docs

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY docs/requirements.txt requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["bash"]
