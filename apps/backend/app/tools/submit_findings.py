from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class SubmitFindingsInput(BaseModel):
    summary: str = Field(description="A concise summary of the findings.")
    relevant_files: list[str] = Field(
        description="Workspace relative file paths relevant to the finding.")
    hypothesis: str = Field(
        description="The likely cause or answer of the finding.")
    supporting_evidence: list[str] = Field(
        description="Specific observations supporting the hypothesis.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence from 0.0 to 1.0 where 0.0 is no confidence and 1.0 is absolute confidence.")


def create_submit_findings_tool(workspace_root: Path):
    workspace_root = workspace_root.expanduser().resolve()

    if not workspace_root.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace_root}")

    def submit_findings(
        summary: str,
        relevant_files: list[str],
        hypothesis: str,
        supporting_evidence: list[str],
        confidence: float,
    ) -> dict:
        """Submit final findings as a structured, machine readable handoff."""
        return {
            "summary": summary,
            "relevant_files": relevant_files,
            "hypothesis": hypothesis,
            "supporting_evidence": supporting_evidence,
            "confidence": confidence,
        }

    return StructuredTool.from_function(
        func=submit_findings,
        name="submit_findings",
        description="Submit final findings instead of responding with free-form text.",
        args_schema=SubmitFindingsInput,
    )
