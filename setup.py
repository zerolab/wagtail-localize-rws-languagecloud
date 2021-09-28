#!/usr/bin/env python

from os import path

from setuptools import find_packages, setup

from wagtail_localize_rws_languagecloud import __version__


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wagtail-localize-rws-languagecloud",
    version=__version__,
    description="Python Boilerplate contains all the boilerplate you need to create a Python package.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Chris Shaw",
    author_email="chris.shaw@torchbox.com",
    url="",
    packages=find_packages(),
    include_package_data=True,
    license="BSD",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Framework :: Wagtail",
        "Framework :: Wagtail :: 2",
    ],
    install_requires=[
        "Django>=2.2,<3.3",
        "Wagtail>=2.11,<2.15",
        "wagtail-localize>=1.0rc2",
    ],
    extras_require={
        "testing": [
            "dj-database-url==0.5.0",
            "freezegun==0.3.15",
            "responses==0.13.4"
        ],
    },
    zip_safe=False,
)
