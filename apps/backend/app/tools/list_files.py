import os
from pathlib import Path

from langchain.tools import tool

from app.services.filesystem import is_ignored


def create_list_files_tool(workspace_root: Path):
    workspace_root = workspace_root.expanduser().resolve()

    if not workspace_root.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace_root}")

    @tool
    def list_files(extension: str | None = None, max_results: int = 500) -> list[str]:
        """Lists all files in the workspace, optionally filtered by extension and optionally limited by result count.

        Args:
            extension: Optional file extension filter.
            max_results: Optional maximum number of paths to return.
        """
        if max_results <= 0:
            raise ValueError("max_results must be greater than 0")
        normalized_extension = None
        if extension:
            normalized_extension = extension.lower()
            if not normalized_extension.startswith("."):
                normalized_extension = f".{normalized_extension}"

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
                if (normalized_extension and path.suffix.lower() != normalized_extension):
                    continue

                files_list.append(path.relative_to(workspace_root).as_posix())

                if len(files_list) >= max_results:
                    return files_list

        return sorted(files_list)

    return list_files
