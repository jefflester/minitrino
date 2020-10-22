#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
from setuptools import setup

setup(
    name="Minipresto",
    version="0.0.0",
    description=(
        f"A command line tool that makes it easy to run "
        f"modular Presto environments locally.",
    ),
    long_description=os.path.join(
        "..", os.path.dirname(os.path.abspath(__file__)), "readme.md"
    ),
    long_description_content_type="text/markdown",
    url="https://github.com/jefflester/minipresto",
    author="Jeff Lester",
    author_email="jeff.lester.dev@gmail.com",
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    packages=["minipresto", "minipresto.cmd"],
    include_package_data=True,
    install_requires=[
        "click",
        "colorama",
        "docker",
        "pyyaml",
    ],
    entry_points={"console_scripts": ["minipresto=minipresto.cli:cli"]},
)
