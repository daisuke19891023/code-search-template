"""Top-level package for the codeagent-lab template."""

from importlib import metadata

__all__ = ["__version__"]

try:
    __version__ = metadata.version("codeagent-lab")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.1.0"
