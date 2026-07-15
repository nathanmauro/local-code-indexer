# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog, and this project uses the `[Unreleased]` section
until a release version is cut. Do not infer a package version from this file; the
current package metadata is still `0.1.0.dev0`.

## [Unreleased]

### Added

- Added compact human-readable output for read-side CLI commands while preserving the
  JSON contract behind the global `--json` flag. This covered search, status,
  symbols, file listing, repo listing, and indexed file reads from PR #1.
- Added human-readable setup and mutation output for init, index, watch, reindex-all,
  and remove flows from PR #2, while keeping `mcp-config` JSON-only for copy-paste
  client configuration.
- Added service-level unknown-repo validation for read-side commands in PR #3 so
  requests for missing repo names explain which repos are indexed instead of returning
  ambiguous empty results.
- Added first-run empty-index guidance in PR #4 so empty human-readable search,
  symbol, file-list, and repo-list output points users toward
  `local-code-indexer index <repo_path>`.
- Added CLI-only guidance for empty `--lang` and `--kind` filter results in PR #5 so
  users can distinguish an empty index, an unknown filter value, and a known filter
  with no matches.
- Added CLI-only empty vector-search guidance in PR #6 so `search --mode vector`
  explains when vector search did not run because embeddings were disabled, query
  embedding failed, or no indexed chunks have embeddings.
- Added a top-level `local-code-indexer --version` flag and status version field so
  CLI users and MCP clients can confirm the installed package version.
- Added README installation guidance with the `pip install local-code-indexer`
  command and Python version requirement.

### Changed

- Corrected README installation instructions to install from GitHub
  (`pip install git+...` or `uv tool install git+...`), since the package is not yet
  published to PyPI.
- Positioned the CLI defaults around local coding model usability: human-readable
  output is the default for people at a terminal, while JSON and MCP retrieval payloads
  remain stable for local agents and scripts.
