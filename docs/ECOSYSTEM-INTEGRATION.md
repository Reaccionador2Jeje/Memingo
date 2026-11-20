# Memingo — Ecosystem Integration

Status: coordination plan for consumers of the Memingo language and tooling.

## Stable integration surfaces
Prefer the documented CLI, formatter, project commands and Language Server Protocol interface. Downstream tools should not import private interpreter internals unless a versioned library interface is established.

## Consumers
- Memingo IDE: run files and communicate with the language server.
- MemeCode: use the documented Memingo core and host bridge.
- Node.mgo: preserve upstream Memingo behavior while implementing its separately documented compatibility target.
- Gold & Diamond Browser: consume Memingo through explicit application modules.

## Compatibility policy
- Pin the Memingo version used by downstream repositories.
- Record the upstream commit or release tag for vendored code.
- Add shared conformance fixtures for parsing, evaluation, standard-library behavior and CLI exit codes.
- Treat syntax, built-in and package-format changes as compatibility changes.
- Do not claim Node.mgo compatibility beyond APIs that are tested.

## Next tasks
1. Publish a concise CLI contract and exit-code table.
2. Add an LSP smoke test.
3. Add language conformance fixtures for downstream projects.
4. Document the version-upgrade procedure for vendored consumers.