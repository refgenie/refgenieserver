# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [0.8.0] -- unreleased
### Added
- asset class and recipe-related endpoints
- asset class and recipe-related files to be archived

## [0.7.0] -- 2021-04-27
### Added
- `remotes` section in the refgenieserver config, which supersedes `remote_url_base`. It can be used to define multiple remote data providers.
- new endpoints:
  - `/remotes/dict` to get `remotes` dictionary
  - `/assets/dir_contents/{genome}/{asset}` to get a JSON object (array of strings) listing all files in the asset directory
  - `/assets/file_path/{genome}/{asset}/{seek_key}` to get a *remote* path to the specified file
- direct *unarchived* asset file downloads from asset splash page, both for seek_keys and other asset files

### Changed
- endpoints that return digests return plain text instead of JSON objects for easier parsing; [#67](https://github.com/refgenie/refgenieserver/issues/67)

## [0.6.1] -- 2021-03-18
### Added
- private endpoint serving genomes dict to openAPI schema; [#105](https://github.com/refgenie/refgenieserver/issues/105)

## [0.6.0] -- 2021-03-11
### Added
- API v3, which is a complete redesign and extension of the previous version
- in `refgenieserver archive`, when a `archive_checksum` is missing for a previously archived asset it will be recalculated.
- response models to API endpoints
- API version tags in the openAPI specification
- a `legacy_archive_digest` to the tag attributes

### Changed
- split the user interface into: index, genome and asset pages
- grouped endpoints by API version in the swagger docs
- the archives created with `refgenieserver archive` are now named after digests

## [0.5.1] -- 2020-07-10
### Changed
- in `refgenieserver archive`:
    - implement safer way of asset archive creation
    - follow symlinks

## [0.5.0] -- 2020-07-06
### Added
- support for external asset sources via `remote_url_base` key in the config
### Changed
- path specified in `genome_archive_config` is considered relative to the refgenie genome config file, unless absolute.
- non-servable assets purging is now performed prior to serving rather than after each archive job completion
- dropped Python 2 support
### Removed
- support for old `genome_archive` key; use `genome_archive_folder` and `genome_archive_config` from now on.


## [0.4.4] -- 2020-03-17
### Changed
- `refgenieserver archive` requires all assets to be complete prior to archiving

## [0.4.3] -- 2020-01-16
### Added
- a possibility to decouple genome archive directory and genome archive config file. `refgenieserver archive` uses new key (`genome_archive_config`) from `refgenconf`
- a genome archive config file writability check

### Changed
- key `genome_archive` to `genome_archive_folder`. Backwards compatiblity is preserved (both are currently supported)

## [0.4.2] -- 2020-01-08
### Fixed
- undefined variable referencing issue; [#73](https://github.com/refgenie/refgenieserver/issues/73)

## [0.4.1] -- 2019-12-13
### Fixed
- relationship info not being updated during specific asset archivization; [#70](https://github.com/refgenie/refgenieserver/issues/70)

### Changed
- order of the assets adn tags in the table in the index page: sorted alphabetically instead of oldest to newest

## [0.4.0] -- 2019-12-06
### Added
- asset splash pages presenting all the asset attributes and related API endpoint links. Available at: `/asset/{genome}/{asset}/splash`
- archive digest API endpoint. Available at `/asset/{genome}/{asset}/{tag}/archive_digest`

### Changed
- recipes are served as JSON objects, not files
- `refgenieserver archive` enhancements; related to config file locking

## [0.3.4] -- 2019-11-06
### Added
- distribute the license file with the package
- test script
- API endpoints for serving asset build logs and asset build recipes. Available at `/asset/{genome}/{asset}/log` and `/asset/{genome}/{asset}/recipe`, respectively


### Fixed
- `fastapi` - `starlette` dependency issue

## [0.3.3] -- 2019-10-24
### Fixed
- PyPi installation problem; [#59](https://github.com/refgenie/refgenieserver/issues/59)

## [0.3.2] -- 2019-10-23
### Added
- dynamic website URL rendering in the page banner

### Fixed
- `TypeError` in `refgenieserver archive`; [#55](https://github.com/refgenie/refgenieserver/issues/55)
- `AttributeError` which was raised when no subcommand was specified; [#54](https://github.com/refgenie/refgenieserver/issues/54)

## [0.3.1] -- 2019-10-21

### Fixed
- `refgenconf` not being installed

## [0.3.0] -- 2019-10-21

### Added
- possibility to use `$REFGENIE` environment variable to provide config path in `refgenieserver archive`
- new API endpoints:
    - `/genome/{genome}` -- returns a dictionary with genome attributes (`contents`, `checksum`, `genome_description`)
    - `/genome/{genome}/genome_digest` -- returns just the genome digest
    - `/asset/{genome}/{asset}/{tag}/asset_digest` -- returns just the asset digest
    - `/asset/{genome}/{asset}/default_tag` -- returns the default tag of an asset
- `tag` query parameter to the endpoints: `/asset/{genome}/{asset}/archive`, `/asset/{genome}/{asset}` to retrieve the archive/metadata associated with tagged asset
- API versioning support
- API versions: `v1` (accessible with a `v1/` prefix and without any) and `v2` (accessible with `v2/` prefix)
- `pigz` support. If the command is callable, it will be used for archiving
- incomplete assets skipping in `refgenieserver archive`
- config manipulation support in multi-process contexts, it's racefree, uses file locks
- archive removal support (added `-r` option in `refgenieserver archive`)
- asset registry path support in `refgenieserver archive`

### Changed
- command order from `refgenieserver -c CONFIG -d archive/serve` to `refgenieserver archive/serve -c CONFIG -d`
- the genome tarballs are not produced
- config v0.3 is required
- `-g` and `-a` flags to asset registry path

### Fixed
- `AttributeError` in `refgenieserver archive`; [#35](https://github.com/refgenie/refgenieserver/issues/35)
- issue with asset attributes serving in API v1 after config format change


## [0.2.0] -- 2019-07-11

### Added
- Add an option to archive a specific genome:asset(s) bundle
- Update to use genome config version 0.2
- Added genome descriptions to web interface
- Some visual improvements to links and layout of web interface

## [0.1.0] -- 2019-06-21
- Initial project release
