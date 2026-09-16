from app.agents import research_agent
from app.services.extract_llm_response import extract_llm_response


def print_agent_activity(node_name: str, update: dict) -> None:
    """Print observable model/tool activity from a LangGraph update"""
    for message in update.get("messages", []):
        if node_name == "tools":
            print(f"\n[tool result]\n{message.content}")
            continue

        if message.tool_calls:
            for tool_call in message.tool_calls:
                print(
                    f"\n[tool call] {tool_call['name']}\n"
                    f"arguments: {tool_call['args']}"
                )
        elif message.content:
            print(f"\n[agent]\n{message.content}")


def main() -> None:
    input_state = {
        "messages": [
            {
                "role": "user",
                "content": "Find the JSON file containing user information and tell me the user's name.",
            }
        ]
    }

    final_state = None
    for update in research_agent.stream(input_state, stream_mode="updates"):
        for node_name, node_update in update.items():
            print(f"\n--- {node_name} ---")
            print_agent_activity(node_name, node_update)
            final_state = node_update

    if final_state:
        print("\n--- final answer ---")
        print(extract_llm_response(final_state))


if __name__ == "__main__":
    main()
