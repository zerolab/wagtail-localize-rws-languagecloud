.PHONY: help format install lint test

help:
	@grep '^\.PHONY' Makefile | cut -d' ' -f2- | tr ' ' '\n'

format:
	isort .
	black .
	npm run format

install:
	pip install -e ".[testing]"
	npm ci

lint:
	isort -c --diff .
	black --check .
	flake8 .
	npm run lint

test:
	coverage run testmanage.py test --deprecation all
