from pathlib import Path
import json

from app.agents.research_agent import ResearchAgent

RESET = "\033[0m"
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RED = "\033[91m"


def panel(title: str, content: str, color: str = CYAN) -> None:
    print(f"\n{color}┌─ {title} ─┐{RESET}")
    print(content.rstrip())
    print(f"{color}└{'─' * (len(title) + 4)}┘{RESET}")


def run_turn(agent: ResearchAgent, messages: list, task: str) -> None:
    messages.append({"role": "user", "content": task})
    submissions = []

    print(f"\n{DIM}Researching...{RESET}")
    for update in agent.graph.stream({"messages": messages}, stream_mode="updates"):
        for node_name, node_update in update.items():
            for message in node_update.get("messages", []):
                messages.append(message)
                if node_name == "tools":
                    tool_name = getattr(message, "name", "unknown")
                    if tool_name == "submit_findings":
                        submissions.append(message)
                        panel("submit_findings", str(message.content), GREEN)
                    else:
                        content = str(message.content)
                        panel(f"tool result · {tool_name}",
                              content[:1200], DIM)
                elif getattr(message, "tool_calls", None):
                    for tool_call in message.tool_calls:
                        panel(f"tool call · {tool_call['name']}", str(
                            tool_call["args"]), BLUE)
                elif message.content:
                    panel(node_name, str(message.content), YELLOW)

    if not submissions:
        panel("error", "Research completed without a submit_findings result.", RED)
        return

    submission = submissions[-1].content
    if isinstance(submission, str):
        try:
            submission = json.loads(submission)
        except json.JSONDecodeError:
            submission = {}

    hypothesis = submission.get("hypothesis") if isinstance(submission, dict) else None
    if hypothesis:
        print(f"\n{GREEN}fabric >{RESET} {hypothesis}")


def main():
    workspace = Path.cwd()
    print(f"{CYAN}╭────────────────────────────╮{RESET}")
    print(f"{CYAN}│        AgentFabric          │{RESET}")
    print(f"{CYAN}╰────────────────────────────╯{RESET}")
    print(f"{DIM}Workspace: {workspace}{RESET}")
    print(f"{DIM}Ask questions about this project. Type 'exit' to stop.{RESET}")

    agent = ResearchAgent(workspace)
    messages = []
    while True:
        try:
            task = input(f"\n{GREEN}you › {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not task:
            continue
        if task.lower() in {"exit", "quit", ":q"}:
            print("Goodbye!")
            break
        run_turn(agent, messages, task)


if __name__ == "__main__":
    main()
