# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Ability to change the default project settings.
  This introduces a new `LanguageCloudProjectSettings` model to store the provided settings, and is
  only created when an editor chooses to send a translation to RWS.
  To create missing settings from your existing projects run `./manage.py create_missing_rws_project_settings`.
- LanguageCloud translation report

### Fixed

- Archive projects are no longer retried

## [0.2] - 2021-11-12

### Added

- Support for Wagtail 2.15
- Allow developers to configure the wait time between API calls
- [pre-commit](https://pre-commit.com/) support
- Developer docs

### Fixed

- Improved exception handling in cron

### Changed

- Multiple target languages are grouped into one project.
  This is a compatibility breaking change.

## [0.1] - 2021-10-01

Initial release
