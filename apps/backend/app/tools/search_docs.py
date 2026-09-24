from typing import Dict

from langchain.tools import tool

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.db.chunks import find_similar_chunks

EMBEDDING_DIMENSIONS = 1536


def create_search_docs_tool():
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001", output_dimensionality=EMBEDDING_DIMENSIONS)

    @tool
    def search_docs(query: str, top_k: int = 5) -> Dict[str, str]:
        """Searches the indexed React and Next.js documentation knowledge base for framework concepts, APIs, recommended patterns, and implementation guidance. Use it to retrieve relevant documentation when analyzing or evaluating code against React or Next.js behavior and best practices.

        Args:
            query: The search query.
            top_k: Optional number of top chunks to return.
        """
        if not query or not query.strip():
            return {"error": "query cannot be empty"}
        try:
            vector = embedding_model.embed_query(query)
            similar_chunks = find_similar_chunks(vector, top_k=top_k)
        except Exception as exc:
            return {"error": f"Document search failed: {exc}"}

        if isinstance(similar_chunks, dict):
            return {"error": similar_chunks.get("error", "Document search failed.")}

        search_results = ""
        for index, chunk in enumerate(similar_chunks):
            search_results += (
                f"[Result {index + 1}]\n"
                f"Source: {chunk["filename"]}\n"
                f"Section: {chunk["section"]}\n"
                f"Chunk Index: {chunk["chunk_index"]}\n\n"
                f"{chunk["content"]}\n\n")

        return {"results": search_results}

    return search_docs
