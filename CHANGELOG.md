# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* **Device-less playback support** – The integration can now generate direct
  stream URLs for any Emby library item allowing you to cast movies, music or
  shows to *non-Emby* targets such as Chromecast, Sonos or the browser media
  player.  Browse tree leaf nodes expose `media-source://emby/<ItemId>` when
  you open them on a non-Emby entity and the new *media source* provider
  negotiates the best audio/video variant with your server. *(epic #217 –
  closes tasks #218–#223)*

* **Play media support** – Home Assistant’s `media_player.play_media` service is
  now fully implemented.  Call the service with `media_type` / `media_id` (and
  optional `enqueue`, `position`) to start playback or queue items on any Emby
  client.  See the updated README for usage examples.  *(epic #3 – closes
  issue #12)*

* **Virtual directories – Continue Watching & Favorites** – The media browser
  now surfaces two convenient shortcuts at the root level so you can resume
  unfinished movies/episodes or jump straight into items you starred in Emby.
  Both virtual folders fully support pagination and artwork just like physical
  libraries. *(epic #129 – closes issue #135)*

* **Media browsing** – Navigate your Emby libraries directly inside Home
  Assistant via the **Browse Media** dialog.  Libraries, collections, seasons
  and items are represented with full artwork and metadata.  Delegates to the
  built-in `media_source` integration for TTS and local files. *(epic #24 –
  closes issues #25–#29)*

### Fixed

* **Missing transport & browse controls** – A breaking change in Emby 4.9
  moved the *remote control* permission flag to a new location which caused
  Home Assistant to hide **all** playback buttons and the *Browse media*
  dialog.  The integration now detects both the legacy *flat* flag and the
  new nested structure so feature support is restored across all server
  versions.  *(task #227 – closes regression epic #225)*

* **Connection regression on default ports** – The integration again honours
  Emby’s *native* defaults (`8096`/`8920`) when the **port** field is left
  blank during setup.  Custom host/port/SSL combinations now work reliably
  across both YAML and UI configuration. *(task #181)*

### Changed

* **Browse Media now enabled by default** – Surfacing the capability flag on
  every player means you can start using the media browser without manual
  `supported_features` overrides. *(task #183)*
