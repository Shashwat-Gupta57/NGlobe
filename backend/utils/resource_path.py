"""PyInstaller resource path helper.

Resolves file paths correctly whether running from source or from a
PyInstaller-bundled executable (where files are extracted to _MEIPASS).
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Resolve a resource path for both development and bundled environments.

    When running from source, paths are relative to the backend package root.
    When running as a PyInstaller bundle, paths are relative to the temp
    extraction directory (_MEIPASS).

    Args:
        relative_path: Path relative to the application root.

    Returns:
        Absolute Path to the resource.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path


def is_frozen() -> bool:
    """Check if the application is running as a PyInstaller bundle."""
    return getattr(sys, "frozen", False)
