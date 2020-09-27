#!usr/bin/env/python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="Minipresto",
    version="0.0",
    packages=["minipresto", "minipresto.commands"],
    include_package_data=True,
    install_requires=["click", "colorama", "docker", "pyyaml",],
    entry_points="""
        [console_scripts]
        minipresto=minipresto.cli:cli
    """,
)
