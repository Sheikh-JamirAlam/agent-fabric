from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import MODEL_NAME
from app.state import AgentState
from app.tools import read_file


SYSTEM_PROMPT = "You are an expert Research Agent responsible for finding and reading files in the codebase. Use the available tools when you need file contents."
tools = [read_file]
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
