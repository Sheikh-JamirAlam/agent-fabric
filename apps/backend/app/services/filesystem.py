import os
from pathlib import Path
from functools import lru_cache

import pathspec

IGNORED_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules",
                ".venv", "venv", "dist", "build", "wheels", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".cache", "bun.lock", "uv.lock"}


@lru_cache(maxsize=32)
def gitignore_spec(workspace_root: str) -> pathspec.GitIgnoreSpec:
    gitignore = Path(workspace_root) / ".gitignore"
    if not gitignore.is_file():
        return pathspec.GitIgnoreSpec([])
    return pathspec.GitIgnoreSpec.from_lines(gitignore.read_text(encoding="utf-8").splitlines())


def is_ignored(path: Path, workspace_root: Path) -> bool:
    relative = path.relative_to(workspace_root)
    return any(part in IGNORED_DIRS for part in relative.parts) or gitignore_spec(str(workspace_root)).match_file(relative.as_posix())


def safe_path(workspace_root: Path, requested_path: str) -> Path:
    target = (workspace_root / requested_path).resolve()
    if target != workspace_root and workspace_root not in target.parents:
        raise ValueError("Requested path must stay inside the workspace.")
    return target
