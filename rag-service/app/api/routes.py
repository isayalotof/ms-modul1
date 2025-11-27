import os
import time
import aiofiles
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query as QueryParam
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    DocumentUploadResponse, SearchRequest, SearchResponse, SearchResultItem,
    RAGQueryRequest, RAGQueryResponse, DocumentInfo, DocumentListResponse,
    DocumentListItem, DeleteDocumentResponse, BatchUploadResponse, BatchUploadResult,
    StatisticsResponse, DocumentTypeStats, MostQueriedDocument, HealthResponse,
    DependencyStatus, ReindexRequest, ReindexResponse, ErrorResponse
)
from app.database import get_db, Document, DocumentChunk, Query as QueryModel, test_connection
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import vector_store
from app.services.rag_pipeline import rag_pipeline
from app.services.embedding_service import embedding_service
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


# Helper functions

async def save_upload_file(upload_file: UploadFile, user_id: str) -> tuple[str, int]:
    """Save uploaded file and return path and size"""
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}_{upload_file.filename}"
    file_path = os.path.join(settings.upload_dir, filename)

    # Save file
    file_size = 0
    async with aiofiles.open(file_path, 'wb') as f:
        while chunk := await upload_file.read(8192):
            await f.write(chunk)
            file_size += len(chunk)

    return file_path, file_size


# Endpoints

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    metadata: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload and index a document"""
    try:
        # Parse metadata if provided
        import json
        meta = json.loads(metadata) if metadata else {}

        # Validate file
        processor = DocumentProcessor()
        file_size_estimate = 0  # We'll get actual size after saving

        # Save file
        file_path, file_size = await save_upload_file(file, user_id)

        try:
            # Validate file
            processor.validate_file(file.filename, file_size)

            # Process file
            logger.info(f"Processing file: {file.filename}")
            result = await processor.process_file(file_path, file.filename)

            # Create chunks
            chunks = processor.create_chunks(result["text"], result["metadata"])

            # Create document record
            file_ext = Path(file.filename).suffix.lower()[1:]
            document = Document(
                user_id=user_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_ext,
                meta_data={**meta, **result["metadata"]},
                chunks_count=len(chunks)
            )
            db.add(document)
            await db.flush()

            # Add chunks to vector store
            await vector_store.add_document_chunks(db, document.id, chunks)
            await db.commit()

            logger.info(f"Document uploaded successfully: {document.id}")

            return DocumentUploadResponse(
                status="success",
                document_id=str(document.id),
                filename=file.filename,
                chunks_created=len(chunks),
                file_size=file_size,
                indexed_at=document.created_at,
                metadata={**meta, **result["metadata"]}
            )

        except Exception as e:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Semantic search across documents"""
    try:
        start_time = time.time()

        # Search for similar chunks
        results = await vector_store.search_similar_chunks(
            db=db,
            query=request.query,
            user_id=request.user_id,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            filters=request.filters
        )

        search_time_ms = int((time.time() - start_time) * 1000)

        # Format results
        result_items = [
            SearchResultItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_name=r["document_name"],
                content=r["content"],
                similarity_score=r["similarity_score"],
                metadata=r.get("metadata")
            )
            for r in results
        ]

        return SearchResponse(
            status="success",
            query=request.query,
            results=result_items,
            total_found=len(results),
            search_time_ms=search_time_ms
        )

    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """RAG query with answer generation"""
    try:
        if request.stream:
            raise HTTPException(
                status_code=400,
                detail="Use /query/stream endpoint for streaming responses"
            )

        # Execute RAG pipeline
        response = await rag_pipeline.query(
            db=db,
            query=request.query,
            user_id=request.user_id,
            context_size=request.context_size,
            filters=request.filters
        )

        return RAGQueryResponse(**response)

    except Exception as e:
        logger.error(f"Error in RAG query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def rag_query_stream(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """RAG query with streaming response"""
    try:
        async def event_generator():
            async for chunk in rag_pipeline.query_stream(
                db=db,
                query=request.query,
                user_id=request.user_id,
                context_size=request.context_size,
                filters=request.filters
            ):
                import json
                yield f"data: {json.dumps(chunk)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error in streaming RAG query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get document information"""
    try:
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentInfo(
            document_id=str(document.id),
            filename=document.filename,
            user_id=document.user_id,
            file_size=document.file_size,
            file_type=document.file_type,
            chunks_count=document.chunks_count,
            uploaded_at=document.created_at,
            metadata=document.meta_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = QueryParam(...),
    page: int = QueryParam(default=1, ge=1),
    page_size: int = QueryParam(default=20, ge=1, le=100),
    category: Optional[str] = QueryParam(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of user's documents"""
    try:
        # Build query
        stmt = select(Document).where(Document.user_id == user_id)

        if category:
            stmt = stmt.where(Document.meta_data['category'].astext == category)

        # Get total count
        count_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
        if category:
            count_stmt = count_stmt.where(Document.meta_data['category'].astext == category)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination
        stmt = stmt.order_by(Document.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        documents = result.scalars().all()

        # Format response
        doc_items = [
            DocumentListItem(
                document_id=str(doc.id),
                filename=doc.filename,
                chunks_count=doc.chunks_count,
                uploaded_at=doc.created_at,
                metadata=doc.meta_data
            )
            for doc in documents
        ]

        total_pages = (total + page_size - 1) // page_size

        return DocumentListResponse(
            status="success",
            documents=doc_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: UUID,
    user_id: str = QueryParam(...),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    try:
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check ownership
        if document.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: document belongs to another user"
            )

        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)

        # Get chunks count before deletion
        chunks_count = document.chunks_count

        # Delete document (chunks will be deleted by cascade)
        await db.delete(document)
        await db.commit()

        logger.info(f"Document deleted: {document_id}")

        return DeleteDocumentResponse(
            status="success",
            message="Document deleted successfully",
            document_id=str(document_id),
            chunks_deleted=chunks_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    user_id: str = Form(...),
    metadata: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple documents"""
    try:
        import json
        meta = json.loads(metadata) if metadata else {}

        results = []
        successful = 0
        failed = 0

        for file in files:
            try:
                # Save file
                file_path, file_size = await save_upload_file(file, user_id)

                try:
                    # Process and index
                    processor = DocumentProcessor()
                    processor.validate_file(file.filename, file_size)

                    result = await processor.process_file(file_path, file.filename)
                    chunks = processor.create_chunks(result["text"], result["metadata"])

                    # Create document
                    file_ext = Path(file.filename).suffix.lower()[1:]
                    document = Document(
                        user_id=user_id,
                        filename=file.filename,
                        file_path=file_path,
                        file_size=file_size,
                        file_type=file_ext,
                        meta_data={**meta, **result["metadata"]},
                        chunks_count=len(chunks)
                    )
                    db.add(document)
                    await db.flush()

                    await vector_store.add_document_chunks(db, document.id, chunks)

                    results.append(BatchUploadResult(
                        filename=file.filename,
                        document_id=str(document.id),
                        chunks_created=len(chunks),
                        status="success"
                    ))
                    successful += 1

                except Exception as e:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    results.append(BatchUploadResult(
                        filename=file.filename,
                        status="error",
                        error=str(e)
                    ))
                    failed += 1

            except Exception as e:
                results.append(BatchUploadResult(
                    filename=file.filename,
                    status="error",
                    error=str(e)
                ))
                failed += 1

        await db.commit()

        return BatchUploadResponse(
            status="success",
            total_uploaded=len(files),
            results=results,
            successful=successful,
            failed=failed
        )

    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    user_id: str = QueryParam(...),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics"""
    try:
        # Total documents
        total_docs_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
        total_docs_result = await db.execute(total_docs_stmt)
        total_documents = total_docs_result.scalar() or 0

        # Total chunks
        total_chunks = await vector_store.get_total_chunks_count(db, user_id)

        # Total storage
        storage_stmt = select(func.sum(Document.file_size)).where(Document.user_id == user_id)
        storage_result = await db.execute(storage_stmt)
        total_storage_bytes = storage_result.scalar() or 0
        total_storage_mb = total_storage_bytes / (1024 * 1024)

        # Documents by type
        docs_stmt = select(Document).where(Document.user_id == user_id)
        docs_result = await db.execute(docs_stmt)
        docs = docs_result.scalars().all()

        docs_by_type = DocumentTypeStats()
        for doc in docs:
            if doc.file_type == 'pdf':
                docs_by_type.pdf += 1
            elif doc.file_type == 'docx':
                docs_by_type.docx += 1
            elif doc.file_type == 'txt':
                docs_by_type.txt += 1
            elif doc.file_type == 'md':
                docs_by_type.md += 1

        # Most queried documents (placeholder - would need proper tracking)
        most_queried = []

        # Last query time
        last_query_stmt = select(QueryModel.created_at).where(
            QueryModel.user_id == user_id
        ).order_by(QueryModel.created_at.desc()).limit(1)
        last_query_result = await db.execute(last_query_stmt)
        last_query_at = last_query_result.scalar_one_or_none()

        return StatisticsResponse(
            status="success",
            user_id=user_id,
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_storage_mb=round(total_storage_mb, 2),
            documents_by_type=docs_by_type,
            most_queried_documents=most_queried,
            last_query_at=last_query_at
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/reindex", response_model=ReindexResponse)
async def reindex_document(
    document_id: UUID,
    user_id: str = QueryParam(...),
    request: ReindexRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """Reindex a document"""
    try:
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        old_chunks_count = document.chunks_count

        # Delete old chunks
        await vector_store.delete_document_chunks(db, document_id)

        # Reprocess document
        processor = DocumentProcessor()
        if request and request.chunk_size:
            processor.chunk_size = request.chunk_size
        if request and request.chunk_overlap:
            processor.chunk_overlap = request.chunk_overlap

        result = await processor.process_file(document.file_path, document.filename)
        chunks = processor.create_chunks(result["text"], result["metadata"])

        # Add new chunks
        await vector_store.add_document_chunks(db, document_id, chunks)

        # Update document
        document.chunks_count = len(chunks)
        document.updated_at = datetime.utcnow()
        await db.commit()

        return ReindexResponse(
            status="success",
            document_id=str(document_id),
            old_chunks_count=old_chunks_count,
            new_chunks_count=len(chunks),
            reindexed_at=document.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Debug endpoint for diagnostics
@router.get("/debug/database")
async def debug_database(
    user_id: Optional[str] = QueryParam(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check database state"""
    try:
        result = {}

        # Total documents
        if user_id:
            docs_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
        else:
            docs_stmt = select(func.count(Document.id))
        docs_result = await db.execute(docs_stmt)
        result["total_documents"] = docs_result.scalar() or 0

        # Total chunks
        if user_id:
            chunks_stmt = select(func.count(DocumentChunk.id)).join(Document).where(Document.user_id == user_id)
        else:
            chunks_stmt = select(func.count(DocumentChunk.id))
        chunks_result = await db.execute(chunks_stmt)
        result["total_chunks"] = chunks_result.scalar() or 0

        # Chunks with embeddings
        if user_id:
            emb_stmt = select(func.count(DocumentChunk.id)).join(Document).where(
                Document.user_id == user_id,
                DocumentChunk.embedding.isnot(None)
            )
        else:
            emb_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.embedding.isnot(None))
        emb_result = await db.execute(emb_stmt)
        result["chunks_with_embeddings"] = emb_result.scalar() or 0

        # Recent documents
        recent_stmt = select(Document)
        if user_id:
            recent_stmt = recent_stmt.where(Document.user_id == user_id)
        recent_stmt = recent_stmt.order_by(Document.created_at.desc()).limit(5)
        recent_result = await db.execute(recent_stmt)
        recent_docs = recent_result.scalars().all()

        result["recent_documents"] = [
            {
                "id": str(doc.id),
                "user_id": doc.user_id,
                "filename": doc.filename,
                "chunks_count": doc.chunks_count,
                "created_at": doc.created_at.isoformat()
            }
            for doc in recent_docs
        ]

        # Sample chunks
        sample_stmt = select(DocumentChunk).limit(3)
        if user_id:
            sample_stmt = sample_stmt.join(Document).where(Document.user_id == user_id)
        sample_result = await db.execute(sample_stmt)
        sample_chunks = sample_result.scalars().all()

        result["sample_chunks"] = [
            {
                "id": str(chunk.id),
                "content_preview": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                "has_embedding": chunk.embedding is not None and len(chunk.embedding) > 0,
                "embedding_dimension": len(chunk.embedding) if (chunk.embedding is not None and len(chunk.embedding) > 0) else None
            }
            for chunk in sample_chunks
        ]

        return result

    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint (at root level, not under /api/v1/rag)
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        dependencies = DependencyStatus(
            database="ok",
            pgvector="ok",
            anthropic_api="ok",
            embedding_model="ok"
        )

        # Test database
        try:
            await db.execute(text("SELECT 1"))
        except:
            dependencies.database = "error"

        # Get counts
        try:
            total_docs_result = await db.execute(select(func.count(Document.id)))
            total_docs = total_docs_result.scalar() or 0

            total_chunks_result = await db.execute(select(func.count(DocumentChunk.id)))
            total_chunks = total_chunks_result.scalar() or 0
        except:
            total_docs = None
            total_chunks = None
            dependencies.database = "error"

        # Determine overall status
        status = "healthy" if all(
            v == "ok" for v in [
                dependencies.database,
                dependencies.pgvector,
                dependencies.anthropic_api,
                dependencies.embedding_model
            ]
        ) else "unhealthy"

        response = HealthResponse(
            status=status,
            service=settings.service_name,
            version=settings.service_version,
            dependencies=dependencies,
            embedding_model=settings.embedding_model,
            database_documents=total_docs,
            database_chunks=total_chunks,
            timestamp=datetime.utcnow()
        )

        return response

    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            service=settings.service_name,
            version=settings.service_version,
            dependencies=DependencyStatus(
                database="error",
                pgvector="unknown",
                anthropic_api="unknown",
                embedding_model="unknown"
            ),
            embedding_model=settings.embedding_model,
            timestamp=datetime.utcnow()
        )
