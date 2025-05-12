#!/usr/bin/env python3

SPECS = {
    "query": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "sql": {"type": "string"},
            "trinoCliArgs": {"type": "array"},
            "contains": {"type": "array"},
            "rowCount": {"type": "number"},
            "env": {"type": "object"},
        },
        "required": ["type", "name", "sql"],
    },
    "shell": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "command": {"type": "string"},
            "container": {"type": "string"},
            "contains": {"type": "array"},
            "exitCode": {"type": "number"},
            "env": {"type": "object"},
            "healthCheck": {
                "type": "object",
                "properties": {
                    "retries": {"type": "number"},
                    "command": {"type": "string"},
                    "container": {"type": "string"},
                    "contains": {"type": "array"},
                    "exitCode": {"type": "number"},
                },
                "required": ["command"],
            },
            "subCommands": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "retries": {"type": "number"},
                        "command": {"type": "string"},
                        "container": {"type": "string"},
                        "contains": {"type": "array"},
                        "exitCode": {"type": "number"},
                        "env": {"type": "object"},
                    },
                    "required": ["command"],
                },
            },
        },
        "required": ["type", "name", "command"],
    },
    "logs": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "container": {"type": "string"},
            "contains": {"type": "array"},
            "timeout": {"type": "number"},
        },
        "required": ["type", "name", "container", "contains"],
    },
}
