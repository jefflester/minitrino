#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
from minipresto.test.helpers import ModuleTest

from minipresto.settings import MODULE_CATALOG
from minipresto.settings import MODULE_SECURITY


def main():

    # Elasticsearch
    ModuleTest(
        {
            "command": "presto-cli --execute 'show catalogs'",
            "expected_output": ["elasticsearch"],
        },
        {
            "command": "presto-cli --execute 'show schemas from elasticsearch'",
            "expected_output": ["default"],
        },
        module_type=MODULE_CATALOG,
        module_name="elasticsearch",
    )

    # Hive-S3
    ModuleTest(
        {
            "command": "presto-cli --execute 'show catalogs'",
            "expected_output": ["hive_hms"],
        },
        {
            "command": "presto-cli --execute 'show schemas from hive_hms'",
            "expected_output": ["default"],
        },
        module_type=MODULE_CATALOG,
        module_name="hive-s3",
    )

    # Hive-Minio
    ModuleTest(
        {
            "command": "presto-cli --execute 'show catalogs'",
            "expected_output": ["hive_hms_minio"],
        },
        {
            "command": "presto-cli --execute 'show schemas from hive_hms_minio'",
            "expected_output": ["default"],
        },
        module_type=MODULE_CATALOG,
        module_name="hive-minio",
    )

    # MySQL
    ModuleTest(
        {
            "command": "presto-cli --execute 'show catalogs'",
            "expected_output": ["mysql"],
        },
        {
            "command": "presto-cli --execute 'show schemas from mysql'",
            "expected_output": ["performance_schema", "sys"],
        },
        module_type=MODULE_CATALOG,
        module_name="mysql",
    )


if __name__ == "__main__":
    main()
