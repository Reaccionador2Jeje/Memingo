"""Workspace catalog and dataset persistence for Memingo AI Studio.

AI Studio is intentionally dependency-free. It indexes local model, checkpoint,
and dataset files without executing project code or following paths outside the
selected workspace.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import ai, nn

DATASET_FORMAT = "memingo.dataset"
DATASET_VERSION = 1
MAX_DATASET_BYTES = 16 * 1024 * 1024
IGNORED_DIRECTORIES = {
    ".git", ".memingo", "__pycache__", "node_modules", ".venv", "dist"
}


def _safe_path(path, project_directory="."):
    if not isinstance(path, str) or not path.strip():
        raise ai.AIError("AI Studio path must be a non-empty string")
    root = Path(project_directory).resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ai.AIError("AI Studio path must stay inside the project directory")
    return root, target


def dataset_summary(dataset):
    """Return shape and sample metadata for a validated Dataset."""
    if not isinstance(dataset, ai.Dataset):
        raise ai.AIError("dataset_summary expects an ai.dataset value")
    return {
        "type": "dataset",
        "samples": len(dataset),
        "input_features": len(dataset.inputs[0]),
        "output_features": len(dataset.outputs[0]),
        "input_shape": [len(dataset), len(dataset.inputs[0])],
        "output_shape": [len(dataset), len(dataset.outputs[0])],
    }


def save_dataset(dataset, path, project_directory="."):
    """Persist a validated dataset as a bounded, versioned .mgodata file."""
    if not isinstance(dataset, ai.Dataset):
        raise ai.AIError("save_dataset expects an ai.dataset value")
    _, target = _safe_path(path, project_directory)
    payload = {
        "format": DATASET_FORMAT,
        "version": DATASET_VERSION,
        "inputs": dataset.inputs,
        "outputs": dataset.outputs,
    }
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":"))
    raw = encoded.encode("utf-8")
    if len(raw) > MAX_DATASET_BYTES:
        raise ai.AIError("dataset file exceeds the 16 MB limit")
    temporary = target.with_name("." + target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(raw)
        temporary.replace(target)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ai.AIError(f"could not save dataset: {error}") from error
    return str(target)


def load_dataset(path, project_directory="."):
    """Load and validate a versioned .mgodata dataset inside the workspace."""
    _, target = _safe_path(path, project_directory)
    try:
        if target.stat().st_size > MAX_DATASET_BYTES:
            raise ai.AIError("dataset file exceeds the 16 MB limit")
        payload = json.loads(target.read_text(encoding="utf-8"))
    except ai.AIError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ai.AIError(f"could not load dataset: {error}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("format") != DATASET_FORMAT
        or payload.get("version") != DATASET_VERSION
        or set(payload) != {"format", "version", "inputs", "outputs"}
    ):
        raise ai.AIError("unsupported or invalid Memingo dataset file")
    try:
        return ai.dataset(payload["inputs"], payload["outputs"])
    except (KeyError, TypeError, ai.AIError) as error:
        raise ai.AIError(f"invalid dataset contents: {error}") from error


def inspect_brain(path, project_directory="."):
    """Load a native brain through its strict validator and return metadata."""
    root, target = _safe_path(path, project_directory)
    model = nn.load_brain(str(target), str(root))
    result = nn.summary(model)
    result["path"] = target.relative_to(root).as_posix()
    result["format"] = "memingo.sequential"
    result["version"] = 1
    return result


def workspace(project_directory="."):
    """Index AI assets in a project without executing any source files."""
    root = Path(project_directory).resolve()
    if not root.is_dir():
        raise ai.AIError(f"AI Studio workspace does not exist: {root}")
    assets = {"models": [], "checkpoints": [], "datasets": []}
    extensions = {
        ".mgoai": "models",
        ".mgochk": "checkpoints",
        ".mgodata": "datasets",
    }
    for path in sorted(root.rglob("*")):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        category = extensions.get(path.suffix.lower())
        if category is None:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        record = {"name": path.name, "path": relative.as_posix(), "size_bytes": size}
        if category == "models":
            try:
                model = nn.load_brain(str(path), str(root))
                record.update({
                    "valid": True,
                    "summary": nn.summary(model),
                })
            except (OSError, ValueError, TypeError) as error:
                record.update({"valid": False, "error": str(error)})
        elif category == "datasets":
            try:
                data = load_dataset(relative.as_posix(), root)
                record.update({"valid": True, "summary": dataset_summary(data)})
            except (OSError, ValueError, TypeError) as error:
                record.update({"valid": False, "error": str(error)})
        else:
            record["valid"] = size <= 32 * 1024 * 1024
        assets[category].append(record)
    return {
        "studio": "Memingo AI Studio",
        "version": 1,
        "workspace": str(root),
        "counts": {name: len(items) for name, items in assets.items()},
        **assets,
    }
