from typing import TypedDict, List, Dict, Any
from pgvector import Vector

from app.db.connection import database_connection

EMBEDDING_DIMENSIONS = 1536


class EmbeddedChunk(TypedDict):
    page_content: str
    metadata: dict[str, Any]
    embedding: list[float]


def register_chunks(document_id: str, chunks: List[EmbeddedChunk]) -> Dict[str, str | int | None]:
    if not document_id:
        return {"error": "A document_id is required to register chunks."}
    if not chunks:
        return {"error": "No chunks were provided for registration."}

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                for chunk in chunks:
                    embedding = chunk.get("embedding")
                    if embedding is None:
                        raise ValueError(
                            f"Chunk {chunk["metadata"].get("chunk_index")} has no embedding."
                        )
                    if len(embedding) != EMBEDDING_DIMENSIONS:
                        raise ValueError(
                            f"Chunk {chunk["metadata"].get("chunk_index")} has embedding dimension {len(embedding)}; expected {EMBEDDING_DIMENSIONS}."
                        )

                    cursor.execute(
                        """
                        INSERT INTO document_chunks (document_id, chunk_index, content, section, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (document_id, chunk_index)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            document_id,
                            chunk["metadata"].get("chunk_index"),
                            chunk["page_content"],
                            chunk["metadata"].get(
                                "Header 1") or chunk["metadata"].get("Header 2"),
                            Vector(embedding),
                        ),
                    )

        return {
            "document_id": document_id,
            "chunks_registered": len(chunks),
            "error": None,
        }
    except Exception as exc:
        return {"error": f"Chunk registration failed: {exc}"}


def find_similar_chunks(vector: list[float], top_k: int = 5,) -> List[Dict[str, Any]] | Dict[str, str]:
    if top_k < 1 or top_k > 15:
        return {"error": "top_k must be an integer between 1 and 15."}
    if not vector:
        return {"error": "The embedding vector cannot be empty."}
    if len(vector) != EMBEDDING_DIMENSIONS:
        return {"error": f"The embedding vector must have {EMBEDDING_DIMENSIONS} dimensions; got {len(vector)}."}

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT docs.id, docs.filename, chunks.chunk_index, chunks.content, chunks.section, (1 - (chunks.embedding <=> %s)) AS similarity
                    FROM document_chunks chunks
                    INNER JOIN documents docs ON chunks.document_id = docs.id
                    WHERE (1 - (chunks.embedding <=> %s)) > 0.65
                    ORDER BY similarity DESC
                    LIMIT %s
                    """,
                    (Vector(vector), Vector(vector), top_k,),
                )
                results = cursor.fetchall()

        if not results:
            return {"error": "No similar chunks found."}
        return [
            {
                "document_id": row[0],
                "filename": row[1],
                "chunk_index": row[2],
                "content": row[3],
                "section": row[4],
                "similarity": row[5],
            } for row in results
        ]
    except Exception as exc:
        return {"error": f"Failed to find similar chunks: {exc}"}
