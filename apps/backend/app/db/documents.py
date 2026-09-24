from typing import Dict
import psycopg

from app.db.connection import database_connection


def register_document(filename: str, source: str) -> Dict[str, str]:
    if not filename or not source:
        return {"error": "No document path was provided."}

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, filename, source FROM documents WHERE source = %s",
                    (source,),
                )
                existing_document = cursor.fetchone()

                if existing_document:
                    return {
                        "document_id": str(existing_document[0]),
                        "filename": existing_document[1],
                        "source": existing_document[2],
                    }

                try:
                    cursor.execute(
                        """
                        INSERT INTO documents (filename, source)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (
                            filename,
                            source,
                        ),
                    )
                    inserted_row = cursor.fetchone()
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
                    cursor.execute(
                        "SELECT id, filename, source FROM documents WHERE source = %s",
                        (source,),
                    )
                    existing_document = cursor.fetchone()
                    if not existing_document:
                        raise
                    return {
                        "document_id": str(existing_document[0]),
                        "filename": existing_document[1],
                        "source": existing_document[2],
                    }

                return {
                    "document_id": str(inserted_row[0]),
                    "filename": filename,
                    "source": source,
                }
    except Exception as exc:
        return {"error": f"Document registration failed: {exc}"}


def get_document_by_id(document_id: str) -> Dict[str, str]:
    if not document_id:
        return {"error": "No document ID was provided."}

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, filename, source FROM documents WHERE id = %s",
                    (document_id,),
                )
                document = cursor.fetchone()

                if not document:
                    return {"error": f"No document found with ID: {document_id}"}

                return {
                    "document_id": document[0],
                    "filename": document[1],
                    "source": document[2],
                }
    except Exception as exc:
        return {"error": f"Failed to retrieve document: {exc}"}
