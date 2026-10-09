"""Bubblewrap (bwrap) wrapper: runs a command in a throw-away sandbox.

No network, read-only system dirs, one writable workspace, dies with the parent.
"""
from __future__ import annotations

import shutil
from typing import Sequence


def bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


def wrap(argv: Sequence[str], workspace: str) -> list[str]:
    """Return the full bwrap command line for `argv`. The workspace appears at /workspace."""
    return [
        "bwrap",
        "--unshare-all",          # new pid/ipc/uts/net/user namespaces -> no network
        "--die-with-parent",
        "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/lib64", "/lib64",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", workspace, "/workspace",
        "--chdir", "/workspace",
        *argv,
    ]
