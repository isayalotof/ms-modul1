from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, delete, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Document, DocumentChunk
from app.services.embedding_service import embedding_service
from app.utils.logger import logger


class VectorStore:
    """Service for storing and querying vector embeddings"""

    async def add_document_chunks(
        self,
        db: AsyncSession,
        document_id: UUID,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Add document chunks with embeddings to the vector store.

        Args:
            db: Database session
            document_id: Document ID
            chunks: List of chunks with content and metadata

        Returns:
            Number of chunks added
        """
        try:
            # Extract texts for batch embedding
            texts = [chunk["content"] for chunk in chunks]

            # Generate embeddings
            embeddings = await embedding_service.generate_embeddings_batch(texts)

            # Create chunk records
            chunk_records = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk["content"],
                    embedding=embedding,
                    metadata=chunk.get("metadata")
                )
                chunk_records.append(chunk_record)

            # Bulk insert
            db.add_all(chunk_records)
            await db.flush()

            logger.info(f"Added {len(chunk_records)} chunks for document {document_id}")
            return len(chunk_records)

        except Exception as e:
            logger.error(f"Error adding document chunks: {str(e)}")
            raise

    async def search_similar_chunks(
        self,
        db: AsyncSession,
        query: str,
        user_id: str,
        top_k: int = 5,
        min_similarity: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using cosine similarity.

        Args:
            db: Database session
            query: Search query
            user_id: User ID for filtering
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            filters: Optional metadata filters

        Returns:
            List of similar chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = await embedding_service.generate_embedding(query)

            # Build query
            # Using cosine distance (1 - cosine similarity)
            similarity = DocumentChunk.embedding.cosine_distance(query_embedding)

            stmt = (
                select(
                    DocumentChunk,
                    Document,
                    (1 - similarity).label("similarity_score")
                )
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(Document.user_id == user_id)
                .where((1 - similarity) >= min_similarity)
                .order_by(similarity)
                .limit(top_k)
            )

            # Apply metadata filters if provided
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(
                        Document.metadata[key].astext == str(value)
                    )

            result = await db.execute(stmt)
            rows = result.all()

            # Format results
            results = []
            for chunk, document, score in rows:
                results.append({
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "document_name": document.filename,
                    "content": chunk.content,
                    "similarity_score": float(score),
                    "metadata": chunk.metadata or {}
                })

            logger.info(f"Found {len(results)} similar chunks for query")
            return results

        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise

    async def delete_document_chunks(self, db: AsyncSession, document_id: UUID) -> int:
        """
        Delete all chunks for a document.

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            Number of chunks deleted
        """
        try:
            stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            result = await db.execute(stmt)
            count = result.rowcount

            logger.info(f"Deleted {count} chunks for document {document_id}")
            return count

        except Exception as e:
            logger.error(f"Error deleting document chunks: {str(e)}")
            raise

    async def get_chunks_count(self, db: AsyncSession, document_id: UUID) -> int:
        """Get number of chunks for a document"""
        stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def get_total_chunks_count(self, db: AsyncSession, user_id: Optional[str] = None) -> int:
        """Get total number of chunks, optionally filtered by user"""
        stmt = select(func.count(DocumentChunk.id))

        if user_id:
            stmt = stmt.join(Document).where(Document.user_id == user_id)

        result = await db.execute(stmt)
        return result.scalar() or 0


# Global vector store instance
vector_store = VectorStore()
