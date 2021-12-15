# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4] - 2021-12-15

### Added

- Import target files as soon as they become available
- Start LanguageCloud projects once all source files have been uploaded to LanguageCloud
- Complete LanguageCloud projects once all target files have been imported into wagtail

### Fixed

- Allow migrations to cleanly apply to empty DB

## [0.3] - 2021-12-06

### Added

- Ability to change the default project settings.
  This introduces a new `LanguageCloudProjectSettings` model to store the provided settings, and is
  only created when an editor chooses to send a translation to RWS.
  To create missing settings from your existing projects run `./manage.py create_missing_rws_project_settings`.
- LanguageCloud translation report
- Email notifications when translations are ready for review. This is configured using the new setting `SEND_EMAILS`
  ```py
  WAGTAILLOCALIZE_RWS_LANGUAGECLOUD = {
      # (optional) Send an email to uers with any of the following permissions:
      # - wagtail_localize.add_translation
      # - wagtail_localize.change_translation
      # - wagtail_localize.delete_translation
      # - wagtail_localize.submit_translation
      # when new translations are ready for review.
      # Defaults to False if not specified
      "SEND_EMAILS": True,
  }
  ```

### Fixed

- Archived projects are no longer retried

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
