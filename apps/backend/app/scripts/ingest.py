import re
import time
from pathlib import Path
from typing import List

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter, TokenTextSplitter)
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.db.documents import register_document
from app.db.chunks import EmbeddedChunk, register_chunks

EMBEDDING_DIMENSIONS = 1536
MAX_EMBEDDING_RETRIES = 5
RETRY_DELAY_SECONDS = 35
MIN_REQUEST_INTERVAL = 1.0


def _embed_one_with_retry(
    embedding_model,
    text: str,
    last_request_time: float,
) -> tuple[list[float], float]:
    for attempt in range(MAX_EMBEDDING_RETRIES):
        elapsed = time.monotonic() - last_request_time

        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        request_started_at = time.monotonic()

        try:
            vector = embedding_model.embed_documents([text])[0]
            return vector, request_started_at

        except Exception as exc:
            error_text = str(exc)

            is_quota_error = (
                "429" in error_text or "RESOURCE_EXHAUSTED" in error_text)

            if not is_quota_error:
                raise
            if attempt == MAX_EMBEDDING_RETRIES - 1:
                raise

            retry_delay = RETRY_DELAY_SECONDS * (attempt + 1)

            print(f"Embedding quota reached. "
                  f"Retrying in {retry_delay} seconds...")

            time.sleep(retry_delay)

    raise RuntimeError("Embedding failed after all retry attempts.")


def run_ingestion():
    docs_path = Path(__file__).resolve().parents[1] / "docs"
    documents_registered = 0
    chunks_registered = 0
    documents_failed = 0
    chunks_failed = 0
    last_request_time = 0.0

    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001", output_dimensionality=EMBEDDING_DIMENSIONS)

    for file in docs_path.rglob("*"):
        if not file.is_file() or file.name == "THIRD_PARTY_NOTICES.md":
            continue

        chunks = []
        try:
            content = file.read_text(encoding="utf-8")
            clean_content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

            registered_document = register_document(file.name, str(file))
            document_id = registered_document.get("document_id")
            if not document_id:
                raise RuntimeError(
                    f"Could not register document {file.name}: {registered_document.get("error", "unknown error")}")

            headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on, strip_headers=False)
            md_header_chunks = markdown_splitter.split_text(clean_content)
            text_splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=15)
            chunks = text_splitter.split_documents(md_header_chunks)

            for chunk_index, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = chunk_index

            embedded_chunks: List[EmbeddedChunk] = []

            for chunk in chunks:
                chunk_index = chunk.metadata.get("chunk_index")
                chunk_text = chunk.page_content

                if not chunk_text.strip():
                    raise ValueError(
                        f"Chunk {chunk_index} has no text to embed."
                    )

                vector, last_request_time = _embed_one_with_retry(
                    embedding_model=embedding_model,
                    text=chunk_text,
                    last_request_time=last_request_time,
                )

                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Embedding for chunk {chunk_index} has dimension {len(vector)}; expected {EMBEDDING_DIMENSIONS}."
                    )

                embedded_chunks.append(
                    {
                        "page_content": chunk.page_content,
                        "metadata": chunk.metadata,
                        "embedding": vector,
                    }
                )

            chunks_result = register_chunks(document_id, embedded_chunks)
            if chunks_result.get("error"):
                raise RuntimeError(
                    f"Could not register chunks for {file.name}: {chunks_result["error"]}")

            documents_registered += 1
            chunks_registered += int(chunks_result.get("chunks_registered", 0) or 0)
        except Exception as exc:
            documents_failed += 1
            chunks_failed += len(chunks)
            print(f"Failed to ingest {file.name}: {exc}")

    print("Ingestion summary:")
    print(f"Documents registered: {documents_registered}")
    print(f"Chunks registered: {chunks_registered}")
    print(f"Documents failed: {documents_failed}")
    print(f"Chunks failed: {chunks_failed}")


if __name__ == "__main__":
    run_ingestion()
