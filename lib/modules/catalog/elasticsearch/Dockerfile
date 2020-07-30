ARG ELASTICSEARCH_VER

FROM elasticsearch:"${ELASTICSEARCH_VER}"

ADD bootstrap.sh .

ENV discovery.type single-node
ENV bootstrap.memory_lock true
ENV network.host 0.0.0.0
ENV network.bind_host 0.0.0.0
ENV ES_JAVA_OPTS -Xms256m -Xmx256m

RUN /usr/local/bin/docker-entrypoint.sh elasticsearch -d \
    && while ! curl http://127.0.0.1:9200 ; do sleep 1 ; done \
    && ./bootstrap.sh
