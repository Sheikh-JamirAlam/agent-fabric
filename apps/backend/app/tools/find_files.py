import os
from pathlib import Path

from langchain.tools import tool

from app.services.filesystem import is_ignored


def create_find_files_tool(workspace_root: Path):
    workspace_root = workspace_root.expanduser().resolve()

    if not workspace_root.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace_root}")

    @tool
    def find_files(pattern: str, max_results: int = 500) -> list[str]:
        """Lists all files in the workspace that matches the pattern, optionally limited by result count.

        Args:
            pattern: The pattern to match against file names.
            max_results: Optional maximum number of paths to return.
        """
        if max_results <= 0:
            raise ValueError("max_results must be greater than 0")

        files_list = []
        for current_root, dirs, files in os.walk(workspace_root):
            current_path = Path(current_root)

            dirs[:] = [directory for directory in dirs if not is_ignored(
                current_path / directory,
                workspace_root,
            )
            ]

            for filename in files:
                path = current_path / filename
                if is_ignored(path, workspace_root):
                    continue
                if pattern and pattern in path.relative_to(workspace_root).as_posix():
                    files_list.append(path.relative_to(
                        workspace_root).as_posix())

                if len(files_list) >= max_results:
                    return files_list

        return sorted(files_list)

    return find_files
