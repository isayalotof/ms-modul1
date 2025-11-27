import pytest
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService


def test_document_processor_create_chunks():
    """Test document chunking"""
    processor = DocumentProcessor()
    processor.chunk_size = 100
    processor.chunk_overlap = 20

    text = "This is a test document. " * 20
    chunks = processor.create_chunks(text)

    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


def test_document_processor_validate_file():
    """Test file validation"""
    processor = DocumentProcessor()

    # Valid file
    assert processor.validate_file("test.pdf", 1000) is True

    # Invalid format
    with pytest.raises(ValueError, match="Unsupported file format"):
        processor.validate_file("test.exe", 1000)

    # File too large
    with pytest.raises(ValueError, match="File too large"):
        processor.validate_file("test.pdf", 100000000)


@pytest.mark.asyncio
async def test_embedding_service_info():
    """Test embedding service info"""
    service = EmbeddingService()
    info = service.get_model_info()

    assert "model_name" in info
    assert "dimension" in info
    assert "batch_size" in info
    assert "loaded" in info
