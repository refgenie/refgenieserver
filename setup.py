#! /usr/bin/env python

import sys

from setuptools import setup

PACKAGE = "refgenieserver"

# Additional keyword arguments for setup().
extra = {}

# Ordinary dependencies
DEPENDENCIES = []
with open("requirements/requirements-all.txt", "r") as reqs_file:
    for line in reqs_file:
        print(line)
        if not line.strip():
            continue
        DEPENDENCIES.append(line)

extra["install_requires"] = DEPENDENCIES


with open("{}/_version.py".format(PACKAGE), "r") as versionfile:
    version = versionfile.readline().split()[-1].strip("\"'\n")

with open('README.md') as f:
    long_description = f.read()

setup(
    name=PACKAGE,
    packages=[PACKAGE],
    version=version,
    description="This server provides both a web interface and a RESTful API. Users may explore and download archived "
    "indexes from the web interface or develop tools that programmatically query the API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    keywords="project, bioinformatics, sequencing, ngs, workflow, GUI, genomes, server",
    url="https://refgenie.databio.org/",
    author=u"Michal Stolarczyk, Vince Reuter, Nathan Sheffield",
    license="BSD2",
    entry_points={
        "console_scripts": [
            "{p} = {p}.__main__:main".format(p=PACKAGE),
        ],
    },
    include_package_data=True,
    **extra
)
