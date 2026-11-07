"""Shared configuration defaults for Memingo and mgoa."""

from .version import __version__


DEFAULT_REGISTRY = "https://reaccionador2jeje.github.io/Memingo/mgoa/index.json"
DEFAULT_MANIFEST = "memingo.toml"
DEFAULT_LOCKFILE = "memingo.lock.json"
DEFAULT_ENTRY = "main.mgo"

DEFAULT_USER_CONFIG = f"""[memingo]
version = "{__version__}"
registry = "{DEFAULT_REGISTRY}"
auto_update = false
telemetry = false

[runtime]
color = true
editor = "vscode"
"""

DEFAULT_PROJECT_ENV_TEMPLATE = """# Local Memingo environment variables
# CONFIG_JSON={"mode":"dev"}
"""
