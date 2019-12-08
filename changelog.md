# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. 

## [0.4.1] -- 2019-12-XX
### Fixed
- relationship info not being updated during specific asset archivization; [#70](https://github.com/databio/refgenieserver/issues/70) 

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
- PyPi installation problem; [#59](https://github.com/databio/refgenieserver/issues/59)

## [0.3.2] -- 2019-10-23
### Added
- dynamic website URL rendering in the page banner

### Fixed
- `TypeError` in `refgenieserver archive`; [#55](https://github.com/databio/refgenieserver/issues/55)
- `AttributeError` which was raised when no subcommand was specified; [#54](https://github.com/databio/refgenieserver/issues/54)

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
- `AttributeError` in `refgenieserver archive`; [#35](https://github.com/databio/refgenieserver/issues/35)
- issue with asset attributes serving in API v1 after config format change


## [0.2.0] -- 2019-07-11

### Added
- Add an option to archive a specific genome:asset(s) bundle
- Update to use genome config version 0.2
- Added genome descriptions to web interface
- Some visual improvements to links and layout of web interface

## [0.1.0] -- 2019-06-21
- Initial project release
