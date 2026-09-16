from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import MODEL_NAME
from app.state import AgentState
from app.tools import read_file, search_codebase


SYSTEM_PROMPT = """You are an expert Research Agent responsible for finding and analyzing files in the codebase.
Use search_codebase for discovery when you need to find files or lines matching a query. It returns exact file paths, line numbers, and matching lines.
If you encounter any issues or errors while reading files, report them clearly. Always ensure that your responses are concise, informative, and directly address the user's queries. 
Tool-selection rules:
1. Use search_codebase first when you need to discover a file or find matching lines.
2. If search_codebase returns a matching line that directly answers the user's question,
   answer immediately. Do not call read_file.
3. Use read_file only when:
   - the user explicitly asks for the complete file contents,
   - the search result does not contain enough information,
   - surrounding context is required,
   - or multiple matching lines need to be analyzed.
4. Do not call read_file merely because a file path was found."""
tools = [search_codebase, read_file]
llm_with_tools = ChatGoogleGenerativeAI(model=MODEL_NAME).bind_tools(tools)


def call_model(state: AgentState):
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                *state["messages"]]
    return {"messages": [llm_with_tools.invoke(messages)]}


workflow = StateGraph(AgentState)
workflow.add_node("model", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.add_edge(START, "model")
workflow.add_conditional_edges("model", tools_condition)
workflow.add_edge("tools", "model")

research_agent = workflow.compile()
