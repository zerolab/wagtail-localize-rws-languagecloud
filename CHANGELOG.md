# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.1] - 2022-05-17

### Fixed

Fixed bug with 'ready for review' and 'published' status values in the
LanguageCloud Report View. Note this fix depends on attaching a revision to
the `LanguageCloudFile` object at the point translations are imported.
This fix will apply to any new objects but any `LanguageCloudFile` objects
created using version <= 0.8.0 will be shown as a generic 'received' status
rather than 'ready for review' or 'published'.

## [0.8.0] - 2022-04-19

### Changed

- `wagtail_localize_rws_languagecloud` must now appear in `INSTALLED_APPS`
  ahead of `wagtail.admin` and `wagtail_localize`:

  ```py
  INSTALLED_APPS = [
      # ...
      "wagtail_localize_rws_languagecloud",
      "wagtail.admin",
      "wagtail_localize",
  ]
  ```

### Added

- Add new `update_translated_pages` management command
- Display translation status in locale selector
- Show custom comment for translations imported from LanguageCloud
- Documentation improvements

## [0.7.2] - 2022-03-24

### Added

- Add warning when trying to "sync translations" pages that have ongoing
  LanguageCloud projects

### Fixed

- Fix an issue where a special line break character in PO files caused polib to
  crash.
- Strip special characters in LangageCloud file names

## [0.7.1] - 2022-03-16

### Fixed

- Strip special characters in LanguageCloud project names
- Handle invalid language cloud project statuses

## [0.7] - 2022-03-01

### Added

- Add `translation_imported` signal that is triggered when a translation is
  successfully imported from RWS LanguageCloud.

## [0.6] - 2022-02-17

### Added

- Add "Translate this page" action button on the page edit screen.
- Add "Translate this snippet" action button on the snippet edit screen.
- Add "Sync translated pages" action button on the page edit screen.
- Add "Sync translated snippets" action button on the snippet edit screen.

### Fixed

- Mark `LanguageCloud` project status as completed when all its files are imported.

## [0.5] - 2022-01-31

### Added

- Wagtail content language to RWS language code mapper
  This introduces a new `LANGUAGE_CODE_MAP` setting
  ```py
  WAGTAILLOCALIZE_RWS_LANGUAGECLOUD = {
      # (optional) Provide a WAGTAIL_CONTENT_LANGUAGE code to RWS language code map
      # RWS expects region codes (e.g. "en-US", "de-DE") whereas Wagtail will happily
      # accept two letter lanugage code ("en", "de"). You can also use this mapping
      # to map dialect language codes to the main supported language
      "LANGUAGE_CODE_MAP": {
          "en": "en-US",
          "ja": "ja-JP",
          "es-mx": "es-ES",
      },
  }
  ```

### Changed

- Projects are now created in RWS with language directions, matching the selected target locales.

## [0.4] - 2021-12-15

### Added

- Import target files as soon as they become available
- Start LanguageCloud projects once all source files have been uploaded to LanguageCloud
- Complete LanguageCloud projects once all target files have been imported into Wagtail

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
