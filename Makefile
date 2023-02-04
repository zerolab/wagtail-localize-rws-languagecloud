.PHONY: help format install lint test

help:
	@grep '^\.PHONY' Makefile | cut -d' ' -f2- | tr ' ' '\n'

install:
	python -m pip install -e ".[testing]"
	python -m pip install -U pre-commit
	pre-commit install

lint:
	git ls-files --others --cached --exclude-standard | xargs pre-commit run --files

test:
	coverage run testmanage.py test --deprecation all
