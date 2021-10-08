.PHONY: help format install lint test

help:
	@grep '^\.PHONY' Makefile | cut -d' ' -f2- | tr ' ' '\n'

format:
	isort --profile black .
	black .

install:
	pip install -e ".[testing]"

lint:
	isort --profile black -c --diff .
	black --check .
	flake8 .

test:
	coverage run testmanage.py test --deprecation all
