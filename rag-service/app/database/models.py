from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    chunks_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_documents_user_id', 'user_id'),
        Index('idx_documents_created_at', 'created_at'),
        Index('idx_documents_meta_data', 'meta_data', postgresql_using='gin'),
    )


class DocumentChunk(Base):
    """Document chunk model with embeddings"""
    __tablename__ = "document_chunks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index('idx_chunks_document_id', 'document_id'),
        Index('idx_chunks_embedding', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )


class Query(Base):
    """Query log model for analytics"""
    __tablename__ = "queries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    results_count = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_queries_user_id', 'user_id'),
        Index('idx_queries_created_at', 'created_at'),
    )
