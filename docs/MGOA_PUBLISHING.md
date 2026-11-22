# MGOA public package publishing

MGOA uses the Memingo GitHub Pages site as its public package mirror:

- Registry index: `https://reaccionador2jeje.github.io/Memingo/mgoa/index.json`
- Package archives: `https://reaccionador2jeje.github.io/Memingo/mgoa/packages/`
- Repository source directory: `site/mgoa/`

The official package catalog remains in the curated `approved.packages` section. Community publications are added to the separate top-level `packages` table and are **not automatically approved**. Publishing cannot overwrite an official package name.

## Publish a project or package

A publishable directory contains `memingo.toml` (or `package.toml`) with a `[package]` section, a valid name and version, and an existing entry file:

```toml
[package]
name = "cool-kit"
version = "1.2.0"
entry = "main.mgo"
description = "A useful Memingo package"
license = "MIT"
```

Create a GitHub token with **Contents: read and write** permission for `Reaccionador2Jeje/Memingo`. Keep it private and expose it only in the publishing shell:

```bash
export MGOA_PUBLISH_TOKEN="YOUR_GITHUB_TOKEN"
mgoa publish .
```

MGOA also accepts:

- `MGOA_PUBLISH_REPOSITORY` (default: `Reaccionador2Jeje/Memingo`)
- `MGOA_PUBLISH_BRANCH` (default: `main`)

Or pass `--repository owner/name` and `--branch branch-name` to the publish command. The token is never stored in the project manifest, package archive, lockfile, or repository.

## What publication does

1. Validates the project manifest and entry point.
2. Builds a ZIP archive and SHA-256 checksum locally.
3. Reads the current Pages index from the configured repository branch.
4. Adds the release to the community package table, preserving the curated catalog.
5. Creates one Git commit containing the archive, checksum and updated index.
6. Advances the configured branch without force-pushing.

The files are committed under `site/mgoa/packages/` and `site/mgoa/index.json`. The repository's GitHub Pages deployment must publish the `site/` directory for the new release to become public. The package manager never claims a release is live merely because the Git commit was created; the Pages deployment is a separate GitHub Actions step.

A version is immutable: attempting to publish the same name and version with a different archive checksum is rejected. Publish a new version instead.

## Install

After GitHub Pages has deployed the commit, users can install the release normally:

```bash
mgoa add cool-kit
```

The installer resolves the archive through the public index and verifies its SHA-256 digest.
