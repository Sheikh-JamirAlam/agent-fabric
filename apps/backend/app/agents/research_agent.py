from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.config import MODEL_NAME
from app.state import AgentState
from app.tools.list_files import create_list_files_tool
from app.tools.read_file import create_read_file_tool
from app.tools.search_codebase import create_search_codebase_tool
from app.tools.find_files import create_find_files_tool
from app.tools.submit_findings import create_submit_findings_tool
from app.tools.search_docs import create_search_docs_tool


class ResearchAgent:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()

        list_files = create_list_files_tool(self.workspace_root)
        read_file = create_read_file_tool(self.workspace_root)
        search_codebase = create_search_codebase_tool(self.workspace_root)
        find_files = create_find_files_tool(self.workspace_root)
        submit_findings = create_submit_findings_tool(self.workspace_root)
        search_docs = create_search_docs_tool()
        self.tools = [find_files, list_files,
                      read_file, search_codebase, submit_findings, search_docs]
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME).bind_tools(self.tools)

        self.workflow = StateGraph(AgentState)

        self.workflow.add_node("model", self.call_model)
        self.workflow.add_node("require_submission", self.require_submission)
        self.workflow.add_node("tools", ToolNode(self.tools))
        self.workflow.add_edge(START, "model")
        self.workflow.add_conditional_edges("model", self.route_after_model)
        self.workflow.add_conditional_edges("tools", self.route_after_tools)
        self.workflow.add_edge("require_submission", "model")

        self.graph = self.workflow.compile()

    def call_model(self, state: AgentState):
        system_prompt = f"""
        You are an expert Research Agent responsible for finding and analyzing files in the codebase.

        The active project workspace is: {self.workspace_root}
        Always operate on this workspace.

        Available tools:
        1. search_codebase: Use this tool to discover files or lines matching a list of queries.
        2. list_files: Use this tool to list workspace files before choosing files to inspect.
        3. read_file: Use this tool to read the contents of multiple files when you have the exact file paths or filenames.
        4. find_files: Use this tool to find files in the workspace that match a specific pattern.
        5. search_docs: Use it when you need React or Next.js documentation to understand expected framework behavior, verify an implementation, or compare the codebase against documented patterns.
        6. submit_findings: Use this exactly once, as the final tool call, to hand off your structured findings.

        Rules:
        - If you encounter issues or errors while reading files, report them clearly.
        - Keep responses concise and informative.
        - If the user mentions a specific file or line, prioritize using read_file.
        - If the user asks for a list of files, use list_files.
        - If the user asks for information about the codebase, use search_codebase.
        - Always use list_files before using read_file to ensure you have the correct file paths.
        - If the user asks for a specific file, use read_file.
        - Do not use search_docs when the answer can be determined entirely from the local codebase.
        - Use search_docs when the task requires React or Next.js framework knowledge that may not be available in the local codebase.
        - Use search_docs when you need to verify whether an implementation follows documented React or Next.js behavior or recommended patterns.
        - Prefer local codebase tools when the question can be answered by inspecting the project alone.
        - You must call submit_findings exactly once before completing.
        - submit_findings must be the final tool call and must be called alone, never in the same turn as another tool.
        - Never finish with a free-form answer; put the complete handoff in submit_findings."""
        messages = [
            {"role": "system", "content": system_prompt},
            *state["messages"],
        ]

        return {
            "messages": [self.llm.invoke(messages)]
        }

    @staticmethod
    def route_after_model(state: AgentState):
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", []) or []

        if not tool_calls:
            return "require_submission"

        has_submission = any(
            call.get("name") == "submit_findings" for call in tool_calls
        )
        if has_submission and len(tool_calls) != 1:
            return "require_submission"

        return "tools"

    @staticmethod
    def route_after_tools(state: AgentState):
        last_message = state["messages"][-1]
        if getattr(last_message, "name", None) == "submit_findings":
            return END
        return "model"

    @staticmethod
    def require_submission(state: AgentState):
        return {
            "messages": [HumanMessage(
                content=(
                    "You attempted to complete the research without a valid final submission. Continue the research if more information is needed. "
                    "Otherwise, call submit_findings as the only tool call in your turn. Do not provide a free-form final answer."
                )
            )]
        }

    def run(self, messages):
        return self.graph.invoke({"messages": messages})
