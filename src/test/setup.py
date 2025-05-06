#!/usr/bin/env python3

from setuptools import setup

setup(
    name="minitrino-tests",
    version="0.0",
    packages=["src", "src/cli", "src/lib"],
    install_requires=["minitrino", "jsonschema", "PyYAML", "requests>=2.32.2"],
)
