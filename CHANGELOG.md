# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-11-26
### Added
- `NGlobe-Setup.exe`: custom installer (per-user, no admin), Start-menu/Desktop shortcuts, Settings > Apps entry.
- `unins.exe`: removes everything (program, history, logs, certificate, settings, shortcuts) and restores the proxy.
- All-apps capture via mitmproxy local mode (one UAC prompt); falls back to browsers only if declined.
- Each install generates its own "NGlobe" certificate; HTTPS details can be turned on and off from the top bar.
- History size shown in the top bar, with one-click clearing.
- Byte counts for connections that aren't decrypted; hostnames for non-browser apps from DNS and TLS SNI.
- docs/HOW-IT-WORKS.md.

### Changed
- The app is installed as a folder instead of a single exe: starts in about 2 s instead of about 10 s.
- Release workflow builds the installer on GitHub and attaches it to the release (PyPI publishing removed).

## [0.2.0] - 2026-11-26
### Added
- Single double-click app, crash-safe proxy restore, optional certificate, auto-detected location.
### Fixed
- Globe freezing after 1,000 events, header rate/status, many startup and packaging bugs.

## [0.1.0] - 2026-07-12
### Added
- Particle laser beam visualization replacing static arcs.
- React frontend event batching to eliminate lag under heavy traffic.
- Initial release of NetworkGlobe prototype.
