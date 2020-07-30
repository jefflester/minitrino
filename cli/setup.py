#!usr/bin/env/python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="minipresto",
    version="1.0",
    packages=["minipresto", "minipresto.commands"],
    include_package_data=True,
    install_requires=["click", "colorama", "docker",],
    entry_points="""
        [console_scripts]
        minipresto=minipresto.cli:cli
    """,
)
