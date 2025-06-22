# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* **Play media support** – Home Assistant’s `media_player.play_media` service is
  now fully implemented.  Call the service with `media_type` / `media_id` (and
  optional `enqueue`, `position`) to start playback or queue items on any Emby
  client.  See the updated README for usage examples.  *(epic #3 – closes
  issue #12)*
