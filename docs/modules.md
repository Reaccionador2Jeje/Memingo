# Memingo modules

Memingo supports project-local source modules with explicit aliases.

## Importing a module

Example:

    import "maths.mgo" as maths
    spill maths.answer
    spill maths.double(21)

A module is a normal `.mgo` file. Its top-level variables and rituals become members of the imported namespace. Access them through the alias with dot notation (`maths.answer`, `maths.double(...)`).

## Resolution and safety

- Paths are resolved from the project directory.
- Imports must use the `.mgo` extension.
- Resolved paths must remain inside the project directory; parent-directory traversal and symlink escapes are rejected.
- Each resolved module is evaluated once per interpreter. Repeated imports share the same namespace.
- Circular imports are detected and reported rather than recursing forever.
- Module code executes in its own environment with access to Memingo's standard built-ins. Its top-level names do not leak into the importing file.

Third-party packages continue to use the existing `borrow` statement and the package manager; `import` is for source files in the current project.
