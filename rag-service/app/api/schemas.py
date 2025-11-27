from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# Request Schemas

class DocumentUploadRequest(BaseModel):
    """Request for document upload"""
    user_id: str = Field(..., description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class SearchRequest(BaseModel):
    """Request for semantic search"""
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User ID")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class RAGQueryRequest(BaseModel):
    """Request for RAG query"""
    query: str = Field(..., description="User question")
    user_id: str = Field(..., description="User ID")
    context_size: int = Field(default=5, ge=1, le=20, description="Number of chunks for context")
    stream: bool = Field(default=False, description="Enable streaming")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class ReindexRequest(BaseModel):
    """Request for document reindexing"""
    chunk_size: Optional[int] = Field(default=None, ge=100, le=5000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=1000)


# Response Schemas

class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    status: str
    document_id: str
    filename: str
    chunks_created: int
    file_size: int
    indexed_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class SearchResultItem(BaseModel):
    """Single search result item"""
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response for search"""
    status: str
    query: str
    results: List[SearchResultItem]
    total_found: int
    search_time_ms: Optional[int] = None


class SourceItem(BaseModel):
    """Source document reference"""
    document_name: str
    relevance_score: float
    page: Optional[int] = None


class RAGQueryResponse(BaseModel):
    """Response for RAG query"""
    status: str
    query: str
    answer: str
    sources: List[SourceItem]
    tokens_used: int
    response_time_ms: int


class DocumentInfo(BaseModel):
    """Document information"""
    document_id: str
    filename: str
    user_id: str
    file_size: int
    file_type: str
    chunks_count: int
    uploaded_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class DocumentListItem(BaseModel):
    """Document list item"""
    document_id: str
    filename: str
    chunks_count: int
    uploaded_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class DocumentListResponse(BaseModel):
    """Response for document list"""
    status: str
    documents: List[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DeleteDocumentResponse(BaseModel):
    """Response for document deletion"""
    status: str
    message: str
    document_id: str
    chunks_deleted: int


class BatchUploadResult(BaseModel):
    """Result for single file in batch upload"""
    filename: str
    document_id: Optional[str] = None
    chunks_created: Optional[int] = None
    status: str
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for batch upload"""
    status: str
    total_uploaded: int
    results: List[BatchUploadResult]
    successful: int
    failed: int


class DocumentTypeStats(BaseModel):
    """Statistics by document type"""
    pdf: int = 0
    docx: int = 0
    txt: int = 0
    md: int = 0


class MostQueriedDocument(BaseModel):
    """Most queried document info"""
    document_id: str
    filename: str
    query_count: int


class StatisticsResponse(BaseModel):
    """Response for statistics"""
    status: str
    user_id: str
    total_documents: int
    total_chunks: int
    total_storage_mb: float
    documents_by_type: DocumentTypeStats
    most_queried_documents: List[MostQueriedDocument]
    last_query_at: Optional[datetime] = None


class DependencyStatus(BaseModel):
    """Status of a dependency"""
    database: str
    pgvector: str
    anthropic_api: str
    embedding_model: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    dependencies: DependencyStatus
    embedding_model: str
    database_documents: Optional[int] = None
    database_chunks: Optional[int] = None
    timestamp: datetime


class ReindexResponse(BaseModel):
    """Response for reindexing"""
    status: str
    document_id: str
    old_chunks_count: int
    new_chunks_count: int
    reindexed_at: datetime


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str
    details: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
