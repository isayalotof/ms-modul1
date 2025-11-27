import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.vector_store import vector_store
from app.services.anthropic_client import anthropic_client
from app.database.models import Query
from app.utils.logger import logger


class RAGPipeline:
    """Main RAG pipeline for question answering"""

    async def query(
        self,
        db: AsyncSession,
        query: str,
        user_id: str,
        context_size: int = 5,
        min_similarity: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute RAG query pipeline.

        Args:
            db: Database session
            query: User question
            user_id: User ID
            context_size: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold
            filters: Optional metadata filters
            stream: Whether to stream response

        Returns:
            Response with answer and sources
        """
        start_time = time.time()

        try:
            # Step 1: Retrieve relevant chunks
            logger.info(f"Searching for relevant chunks for query: {query[:100]}")
            relevant_chunks = await vector_store.search_similar_chunks(
                db=db,
                query=query,
                user_id=user_id,
                top_k=context_size,
                min_similarity=min_similarity,
                filters=filters
            )

            if not relevant_chunks:
                return {
                    "status": "success",
                    "query": query,
                    "answer": "К сожалению, я не нашел релевантных документов для ответа на ваш вопрос. Попробуйте переформулировать запрос или загрузить дополнительные документы.",
                    "sources": [],
                    "tokens_used": 0,
                    "response_time_ms": int((time.time() - start_time) * 1000)
                }

            # Step 2: Generate response using Claude
            logger.info(f"Generating response with {len(relevant_chunks)} chunks")
            response = await anthropic_client.generate_response(
                query=query,
                context=relevant_chunks,
                stream=stream
            )

            # Step 3: Format sources
            sources = self._format_sources(relevant_chunks)

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Step 4: Log query
            await self._log_query(
                db=db,
                user_id=user_id,
                query_text=query,
                results_count=len(relevant_chunks),
                response_time_ms=response_time_ms,
                tokens_used=response.get("tokens_used", 0)
            )

            return {
                "status": "success",
                "query": query,
                "answer": response["answer"],
                "sources": sources,
                "tokens_used": response["tokens_used"],
                "response_time_ms": response_time_ms
            }

        except Exception as e:
            logger.error(f"Error in RAG pipeline: {str(e)}")
            raise

    async def query_stream(
        self,
        db: AsyncSession,
        query: str,
        user_id: str,
        context_size: int = 5,
        min_similarity: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute RAG query pipeline with streaming.

        Args:
            db: Database session
            query: User question
            user_id: User ID
            context_size: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold
            filters: Optional metadata filters

        Yields:
            Streaming response chunks
        """
        start_time = time.time()

        try:
            # Send status update
            yield {"type": "status", "message": "Ищу релевантные документы..."}

            # Step 1: Retrieve relevant chunks
            relevant_chunks = await vector_store.search_similar_chunks(
                db=db,
                query=query,
                user_id=user_id,
                top_k=context_size,
                min_similarity=min_similarity,
                filters=filters
            )

            if not relevant_chunks:
                yield {
                    "type": "text",
                    "content": "К сожалению, я не нашел релевантных документов для ответа на ваш вопрос."
                }
                yield {
                    "type": "complete",
                    "tokens_used": 0,
                    "time_ms": int((time.time() - start_time) * 1000)
                }
                return

            # Send sources
            sources = self._format_sources(relevant_chunks)
            yield {"type": "sources", "sources": sources}

            # Send status update
            yield {"type": "status", "message": "Генерирую ответ..."}

            # Step 2: Stream response from Claude
            total_tokens = 0
            async for chunk in anthropic_client._generate_streaming(
                anthropic_client._build_prompt(
                    query,
                    anthropic_client._build_context(relevant_chunks)
                )
            ):
                if chunk["type"] == "complete":
                    total_tokens = chunk["tokens_used"]
                yield chunk

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Log query
            await self._log_query(
                db=db,
                user_id=user_id,
                query_text=query,
                results_count=len(relevant_chunks),
                response_time_ms=response_time_ms,
                tokens_used=total_tokens
            )

        except Exception as e:
            logger.error(f"Error in streaming RAG pipeline: {str(e)}")
            yield {"type": "error", "message": str(e)}

    def _format_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources from chunks"""
        sources = []
        seen = set()

        for chunk in chunks:
            doc_id = chunk["document_id"]
            if doc_id not in seen:
                source = {
                    "document_name": chunk["document_name"],
                    "relevance_score": chunk["similarity_score"]
                }

                # Add page if available
                if chunk.get("metadata", {}).get("page"):
                    source["page"] = chunk["metadata"]["page"]

                sources.append(source)
                seen.add(doc_id)

        return sources

    async def _log_query(
        self,
        db: AsyncSession,
        user_id: str,
        query_text: str,
        results_count: int,
        response_time_ms: int,
        tokens_used: int
    ):
        """Log query for analytics"""
        try:
            query_log = Query(
                user_id=user_id,
                query_text=query_text,
                results_count=results_count,
                response_time_ms=response_time_ms,
                tokens_used=tokens_used
            )
            db.add(query_log)
            await db.flush()
        except Exception as e:
            logger.error(f"Error logging query: {str(e)}")


# Global RAG pipeline instance
rag_pipeline = RAGPipeline()
