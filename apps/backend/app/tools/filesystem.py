from pathlib import Path

from langchain.tools import tool


IGNORED_DIRS = {".git", "__pycache__", "*.py[oc]", "wheels",
                "*.egg-info", "node_modules", ".venv", "venv", "dist", "build"}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


@tool
def read_file(file_path_or_name: str, max_lines: int = 500) -> dict:
    """Reads a file from the repository given a relative path or filename.

    Args:
        file_path_or_name: Relative path or exact filename.
        max_lines: Maximum number of lines to read from the file.
    """
    repository_root = _repository_root()
    target_path = repository_root / file_path_or_name
    if target_path.is_file():
        return _read_file_content(target_path, max_lines)

    matches = [
        path for path in repository_root.rglob(file_path_or_name)
        if path.is_file() and not any(part in IGNORED_DIRS for part in path.parts)
    ]
    if not matches:
        return {"error": f"File '{file_path_or_name}' not found in repository."}
    if len(matches) > 1:
        paths = "\n".join(str(path.relative_to(repository_root))
                          for path in matches)
        return {"error": f"Multiple files matched '{file_path_or_name}'. Please specify an exact path:\n{paths}"}
    return _read_file_content(matches[0], max_lines)


@tool
def search_codebase(query: str, extension: str | None = None,
                    max_results: int = 100) -> dict:
    """Find lines matching a query in the codebase.

    Use this for discovery. The result includes exact file paths, line numbers, and matching lines. If the matching line directly answers the user's question, do not call read_file afterward.

    Args:
        query: Case-insensitive text to find, such as 'user' or 'username'.
        extension: Optional file extension filter, such as 'json' or '.json'.
        max_results: Maximum number of matching lines to return.
    """
    if not query.strip():
        return {"error": "The search query cannot be empty."}

    normalized_extension = None
    if extension:
        normalized_extension = extension.lower()
        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

    repository_root = _repository_root()
    results = []
    query_lower = query.casefold()

    for path in repository_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if normalized_extension and path.suffix.lower() != normalized_extension:
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, PermissionError, OSError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if query_lower in line.casefold():
                results.append({
                    "path": str(path.relative_to(repository_root)),
                    "line_number": line_number,
                    "line": line,
                })
                if len(results) >= max_results:
                    return {
                        "query": query,
                        "extension": normalized_extension,
                        "matches": results,
                        "truncated": True,
                    }

    return {
        "query": query,
        "extension": normalized_extension,
        "matches": results,
        "truncated": False,
        "match_count": len(results),
    }
