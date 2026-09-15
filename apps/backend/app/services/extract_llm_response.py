def extract_llm_response(response: dict) -> str:
    """Extract llm response message"""
    content = response["messages"][-1].content
    if isinstance(content, list):
        return "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and "text" in block
        )
    return content
