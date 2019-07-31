# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. 

## [0.2.1] -- unreleased

### Added
- possibility to use `$REFGENIE` environment variable to provide config path in `refgenieserver archive` 

### Changed
- command order from `refgenieserver -c CONFIG -d archive/serve` to `refgenieserver archive/serve -c CONFIG -d`

### Fixed
- `AttributeError` in `refgenieserver archive`; [#35](https://github.com/databio/refgenieserver/issues/35) 
## [0.2.0] -- 2019-07-11

### Added
- Add an option to archive a specific genome:asset(s) bundle
- Update to use genome config version 0.2
- Added genome descriptions to web interface
- Some visual improvements to links and layout of web interface

## [0.1.0] -- 2019-06-21
- Initial project release
