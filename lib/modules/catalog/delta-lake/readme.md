# Delta-Lake Module
This module uses the Delta Lake connector. There is no Spark backend, so tables
need to be created via CTAS queries from Trino. Example:

```
CREATE TABLE delta.default.customer 
WITH (
    location = 's3a://sample-bucket/default/'
)
AS SELECT * FROM tpch.tiny.customer;
```

This will create the table `delta.default.customer` and a corresponding
`_delta_log` directory in the backing MinIO object storage.
