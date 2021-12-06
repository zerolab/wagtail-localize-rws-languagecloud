# Wagtail Localize RWS LanguageCloud

This allows users of [RWS LanguageCloud](https://www.rws.com/translation/language-cloud/) to translate and localize Wagtail CMS content.

## Requirements

- Python >= 3.7
- Django >= 3.0
- Wagtail >= 2.12
- wagtail-localize >= 1.0.1

## Setup

1. `pip install wagtail-localize-rws-languagecloud`
2. Add to `INSTALLED_APPS` in Django settings:

   ```python
   INSTALLED_APPS = [
       # ...
       "wagtail_localize_rws_languagecloud",
   ]
   ```

3. Configure the plugin in Django settings:

   ```python
   import datetime

   WAGTAILLOCALIZE_RWS_LANGUAGECLOUD = {
       # (required) Authentication details to connect to the LanguageCloud API.
       # For info on how to obtain these credentials see https://languagecloud.sdl.com/lc/api-docs/authenticate
       "CLIENT_ID": "<client id>",
       "CLIENT_SECRET": "<client secret>",
       "ACCOUNT_ID": "<account id>",

       # (required) Identifier of a LanguageCloud template to create projects from
       "TEMPLATE_ID": "<template id>",

       # (required) Identifier of a LanguageCloud location to store project files in
       "LOCATION_ID": "<location id>",

       # (optional) Prefix for project names. Defaults to '' if not specified
       "PROJECT_PREFIX": "foobar_",

       # (optional) A timedelta object used to set the project 'due by' date.
       # Defaults to datetime.timedelta(days=7) if not specified
       "DUE_BY_DELTA": datetime.timedelta(days=30),

       # (optional) Number of a seconds to sleep between each API request.
       # Defaults to 0 if not specified
       "API_SLEEP_SECONDS": 5,

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

4. Apply migrations:

   ```
   ./manage.py migrate
   ```

## Synchronisation

This plugin uses a background job to:

- Identify text in wagtail which is pending localization and export it to LanguageCloud
- Identify completed projects in LanguageCloud and import the localized content back into Wagtail

This is done using a management command `./manage.py sync_rws`.

This can be run on a regular basis using a scheduler like cron. We recommend an interval of about every 10 minutes. It is desirable to prevent more than one copy of the sync command from running at the same time.

- If using cron as a scheduler, [lockrun](http://unixwiz.net/tools/lockrun.html) can be used to prevent multiple instance of the same job running simultaneously.
- If using a queue-based scheduler like Celery Beat, the `SyncManager` class contains `is_queued` and `is_running` extension points which could be used to implement a lock strategy.

## How it works

This plugin uses `wagtail-localize` to convert pages into segments and build new pages from translated segments. `wagtail-localize` provides a web interface for translating these segments in Wagtail itself and this plugin plays nicely with that (translations can be made from the Wagtail side too).

Pages/snippets are submitted to LanguageCloud when they are submitted for translation from the default locale. Pages authored in other locales are not supported yet.

## Contributing

All contributions are welcome!

### Install

To make changes to this project, first clone this repository,
then with your preferred virtualenv activated, install testing dependencies:

```shell
make install
```

### pre-commit

Note that this project uses [pre-commit](https://github.com/pre-commit/pre-commit). To set up locally:

```shell
# if you don't have it yet, globally
$ pip install pre-commit
# go to the project directory
$ cd wagtail-localize-rws-languagecloud
# initialize pre-commit
$ pre-commit install

# Optional, run all checks once for this, then the checks will run only on the changed files
$ pre-commit run --all-files
```
