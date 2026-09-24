import os
from pathlib import Path

from langchain.tools import tool

from app.services.filesystem import is_ignored


def create_search_codebase_tool(workspace_root: Path):
    workspace_root = workspace_root.expanduser().resolve()

    if not workspace_root.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace_root}")

    @tool
    def search_codebase(query_strings: list[str], extension: str | None = None,
                        max_lines: int = 100, max_results: int = 10) -> dict:
        """Searches codebase for lines containing any of the provided query strings. The result includes exact file paths, line numbers, and surrounding context for each match.

        Args:
            query_strings: List of case-insensitive text strings to find.
            extension: Optional file extension filter.
            max_lines: Optional maximum number of lines to read from each file.
            max_results: Optional maximum number of matching results to return.
        """
        if not query_strings or not any(query_strings):
            return {"error": "The search query cannot be empty."}
        if max_lines < 1 or max_results < 1:
            return {"error": "max_lines and max_results must be greater than zero."}

        normalized_extension = None
        if extension:
            normalized_extension = extension.lower()
            if not normalized_extension.startswith("."):
                normalized_extension = f".{normalized_extension}"

        results = []
        query_lower = [query.casefold() for query in query_strings]
        truncated = False

        for current_root, dirs, files in os.walk(workspace_root):
            if len(results) >= max_results:
                break

            current_path = Path(current_root)

            dirs[:] = [directory for directory in dirs if not is_ignored(
                current_path / directory, workspace_root,)]

            for filename in files:
                path = current_path / filename
                if is_ignored(path, workspace_root):
                    continue
                if (normalized_extension and path.suffix.lower() != normalized_extension):
                    continue

                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

                matching_line_numbers = [
                    line_number
                    for line_number, line in enumerate(lines, start=1)
                    if any(query in line.casefold() for query in query_lower)
                ]
                if not matching_line_numbers:
                    continue

                if len(results) >= max_results:
                    truncated = True
                    break

                first_match = matching_line_numbers[0]
                last_match = matching_line_numbers[-1]
                context_start = max(1, first_match - max_lines // 2)
                context_end = context_start + max_lines - 1

                if context_end > len(lines):
                    context_end = len(lines)
                    context_start = max(1, context_end - max_lines + 1)

                # Ensure a context window includes all matches when they fit.
                if last_match <= context_end:
                    pass
                elif last_match - first_match + 1 <= max_lines:
                    context_end = last_match
                    context_start = max(1, context_end - max_lines + 1)

                context = [
                    {
                        "line_number": line_number,
                        "line": lines[line_number - 1],
                        "is_match": line_number in matching_line_numbers,
                    }
                    for line_number in range(context_start, context_end + 1)
                ]
                results.append({
                    "path": str(path.relative_to(workspace_root)),
                    "matching_line_numbers": matching_line_numbers,
                    "context": context,
                })

        return {
            "query": query_strings,
            "extension": normalized_extension,
            "matches": results,
            "truncated": truncated,
        }

    return search_codebase
