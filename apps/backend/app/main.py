from app.agents import research_agent
from app.services.extract_llm_response import extract_llm_response


def main() -> None:
    response = research_agent.invoke({
        "messages": [
            {"role": "user", "content": "Give me the contents of read.js."}
        ]
    })
    print(extract_llm_response(response))


if __name__ == "__main__":
    main()
