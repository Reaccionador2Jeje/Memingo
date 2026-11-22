# Memingo AI Studio — A2.5

A2.5 introduces a dependency-free local asset catalog and dataset persistence layer.
It is the first functional foundation for the graphical AI Studio workspace.

## Workspace catalog

Run:

```bash
memingo studio
memingo studio ./my-project
memingo studio --json
```

The command indexes:
- `.mgoai`: native sequential brains, validated through the model loader.
- `.mgochk`: resumable training checkpoints (size status only in this stage).
- `.mgodata`: validated datasets.

The catalog skips generated/dependency directories and symbolic links. It does not
execute project source code. Invalid models and datasets remain visible with an
error field instead of stopping the whole scan.

## Dataset files

Datasets use a versioned `.mgodata` JSON envelope. The loader validates its
format and all sample dimensions/values through the existing Dataset type.
Files are limited to 16 MB and paths must remain inside the project directory.
Writes use a temporary sibling file followed by an atomic replacement.

Memingo scripts can save, load and inspect datasets:

```mgo
vibe data = ai.dataset([[0, 0], [0, 1], [1, 0]], [[0], [1], [1]])
ai.save_dataset(data, "datasets/training.mgodata")

vibe restored = ai.load_dataset("datasets/training.mgodata")
spill ai.dataset_summary(restored).samples
```

## Python API

- `memingo.studio.workspace(project_directory=".")`
- `memingo.studio.inspect_brain(path, project_directory=".")`
- `memingo.studio.save_dataset(dataset, path, project_directory=".")`
- `memingo.studio.load_dataset(path, project_directory=".")`
- `memingo.studio.dataset_summary(dataset)`

The returned workspace is JSON-friendly and contains `models`, `checkpoints`,
`datasets`, and aggregate counts.

## Scope

A2.5 is the local data/model management foundation, not yet a full graphical
training dashboard. It does not execute arbitrary scripts, download datasets,
train models in the background, or render live charts. The next Studio stage
can build its UI on this stable catalog and dataset API. Training behavior and
existing `.mgoai` / `.mgochk` formats remain unchanged.
