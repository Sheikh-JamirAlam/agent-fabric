from pathlib import Path

from langchain.tools import tool

from app.services.filesystem import is_ignored, safe_path


def _read_file_content(file_path: Path, max_lines: int) -> dict:
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        content = "\n".join(lines[:max_lines])
        truncated = len(lines) > max_lines
        if truncated:
            content += f"\n\n[... Truncated {len(lines) - max_lines} remaining lines ...]"
        return {"filename": file_path.name, "path": str(file_path), "line_count": len(lines), "content": content, "truncated": truncated}
    except (UnicodeDecodeError, PermissionError) as error:
        return {"error": f"Could not read {file_path.name}: {error}"}
    except Exception as error:
        return {"error": f"Unexpected error reading {file_path.name}: {error}"}


def create_read_file_tool(workspace_root: Path):
    workspace_root = workspace_root.expanduser().resolve()

    if not workspace_root.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace_root}")

    @tool
    def read_file(file_path_or_names: list[str], max_lines: int = 100) -> dict:
        """Reads multiple files from the workspace given relative paths or filenames.

        Args:
            file_path_or_names: List of relative paths or exact filenames.
            max_lines: Optional maximum number of lines to read from each file.
        """
        if not file_path_or_names:
            return {"error": "At least one file path is required."}
        if max_lines < 1:
            return {"error": "max_lines must be greater than zero."}

        results = {}
        for file_path_or_name in file_path_or_names:
            target_path = safe_path(workspace_root, file_path_or_name)
            if target_path.is_file() and not is_ignored(target_path, workspace_root):
                file_result = _read_file_content(target_path, max_lines)
            else:
                matches = [
                    path for path in workspace_root.rglob(file_path_or_name)
                    if path.is_file() and not is_ignored(path, workspace_root)
                ]
                if not matches:
                    results[file_path_or_name] = f"File '{file_path_or_name}' not found in repository."
                    continue
                if len(matches) > 1:
                    paths = "\n".join(str(path.relative_to(
                        workspace_root)) for path in matches)
                    results[file_path_or_name] = f"Multiple files matched '{file_path_or_name}'. Please specify an exact path:\n{paths}"
                    continue
                file_result = _read_file_content(matches[0], max_lines)

            results[file_path_or_name] = file_result.get(
                "content", file_result.get("error"))

        return results

    return read_file
