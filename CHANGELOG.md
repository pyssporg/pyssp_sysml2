# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-11-09

### Added

- Accept definition roots and merge the core definitions when loading a model.

### Changed

- Handle parameter `base_index` across the SSP artifacts and the CLI.
- Remove the vendored `experimental_pyssp_standard` submodule; consume it as a
  release wheel.
- Add a `CHANGELOG.md`, split `requirements-dev.txt`, and refresh the docs.

