#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from setuptools import setup

HERE = Path(os.path.abspath(__file__)).resolve().parents[1]
README = (HERE / "readme.md").read_text()

setup(
    name="minitrino",
    version="2.0.0",
    description="A command line tool that makes it easy to run modular Trino environments locally.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/jefflester/minitrino",
    author="Jeff Lester",
    author_email="jeff.lester.dev@gmail.com",
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    keyword="trino, docker, minitrino",
    python_requires=">=3.8",
    packages=["minitrino", "minitrino.cmd"],
    include_package_data=True,
    install_requires=[
        "click==7.1.2",
        "colorama",
        "docker==5.0.0",
        "PyYAML",
    ],
    entry_points={"console_scripts": ["minitrino=minitrino.cli:cli"]},
)
