# Local MGOA source modules

MGOA can install a single local Memingo source file as a project dependency. This is useful for reusable functions or constants that do not need a public package release.

From the project directory:

```bash
mgoa add ./utils.mgo
```

MGOA wraps the source file as a local module named after its filename (the name is normalized to letters, digits, dots, dashes and underscores), installs it under `.memingo/packages/<module-name>/main.mgo`, and records its absolute source path in `memingo.lock.json`.

Use it in Memingo source:

```memingo
borrow "utils"
```

The source file remains where it was; MGOA copies its current contents into the project installation. Running `mgoa install` later reads the lockfile and refreshes the installed copy from that same local file. If the source file is moved, run `mgoa add` again with its new path.

Local source modules use the internal version label `0.0.0-local`. They are not uploaded to the public registry by `mgoa add`. To publish a reusable package for other people, create a package directory with a `memingo.toml` manifest and use `mgoa publish`.
