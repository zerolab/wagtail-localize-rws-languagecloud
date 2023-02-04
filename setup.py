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
    description="Translate and localize Wagtail CMS content with RWS LanguageCloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Wagtail",
        "Framework :: Wagtail :: 2",
        "Framework :: Wagtail :: 3",
        "Framework :: Wagtail :: 4",
    ],
    install_requires=[
        "Django>=3.2,<4.2",
        "Wagtail>=2.15",
        "wagtail-localize>=1.0.1",
    ],
    extras_require={
        "testing": [
            "dj-database-url==1.2.0",
            "freezegun==1.2.2",
            "responses==0.22.0",
        ]
    },
    zip_safe=False,
)
