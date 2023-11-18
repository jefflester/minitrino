#!usr/bin/env/python3
# -*- coding: utf-8 -*-

SPECS = {
    "query": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "successCriteria": {
                "type": "object",
                "properties": {
                    "contains": {"type": "array"},
                    "rowCount": {"type": "number"},
                },
            },
            "sql": {"type": "string"},
            "trinoCliArgs": {"type": "array"},
            "env": {"type": "object"},
        },
        "required": ["type", "successCriteria"],
    },
    "shell": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "successCriteria": {
                "type": "object",
                "properties": {
                    "contains": {"type": "array"},
                    "exitCode": {"type": "number"},
                },
            },
            "command": {"type": "string"},
            "container": {"type": "string"},
            "healthCheck": {
                "type": "object",
                "properties": {
                    "retries": {"type": "number"},
                    "command": {"type": "string"},
                    "contains": {"type": "array"},
                    "container": {"type": "string"},
                },
                "required": ["retries", "command", "contains"],
            },
        },
        "required": ["type", "successCriteria"],
    },
    "logs": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "successCriteria": {
                "type": "object",
                "properties": {
                    "contains": {"type": "array"},
                },
                "required": ["contains"],
            },
            "container": {"type": "string"},
            "timeout": {"type": "number"},
        },
        "required": ["type", "successCriteria", "container"],
    },
}
