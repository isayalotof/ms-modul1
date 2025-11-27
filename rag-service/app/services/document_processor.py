import os
import re
from typing import List, Dict, Any
from pathlib import Path
import aiofiles
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from app.config import settings
from app.utils.logger import logger


class DocumentProcessor:
    """Service for processing and chunking documents"""

    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.supported_formats = settings.supported_formats.split(',')

    async def process_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Process a file and extract text.

        Args:
            file_path: Path to the file
            filename: Original filename

        Returns:
            Dictionary with extracted text and metadata
        """
        file_ext = Path(filename).suffix.lower()[1:]

        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")

        try:
            if file_ext == 'pdf':
                return await self._process_pdf(file_path)
            elif file_ext == 'docx':
                return await self._process_docx(file_path)
            elif file_ext in ['txt', 'md']:
                return await self._process_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            raise

    async def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        try:
            reader = PdfReader(file_path)
            text = ""
            pages = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text += f"\n[Page {page_num + 1}]\n{page_text}"

            word_count = len(text.split())

            return {
                "text": text,
                "metadata": {
                    "pages": pages,
                    "word_count": word_count,
                }
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    async def _process_docx(self, file_path: str) -> Dict[str, Any]:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            word_count = len(text.split())

            return {
                "text": text,
                "metadata": {
                    "paragraphs": len(doc.paragraphs),
                    "word_count": word_count,
                }
            }
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            raise

    async def _process_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from TXT/MD file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text = await f.read()

            word_count = len(text.split())
            lines = text.count('\n') + 1

            return {
                "text": text,
                "metadata": {
                    "lines": lines,
                    "word_count": word_count,
                }
            }
        except Exception as e:
            logger.error(f"Error processing text file: {str(e)}")
            raise

    def create_chunks(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to split
            metadata: Optional metadata to include with each chunk

        Returns:
            List of chunks with metadata
        """
        # Clean text
        text = self._clean_text(text)

        # Split into chunks
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to end at a sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                split_point = max(last_period, last_newline)

                if split_point > self.chunk_overlap:
                    end = start + split_point + 1
                    chunk_text = text[start:end]

            chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    "chunk_index": len(chunks),
                    "start_char": start,
                    "end_char": end,
                    **(metadata or {})
                }
            })

            start = end - self.chunk_overlap

        logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    def validate_file(self, filename: str, file_size: int) -> bool:
        """
        Validate file format and size.

        Args:
            filename: File name
            file_size: File size in bytes

        Returns:
            True if valid

        Raises:
            ValueError: If file is invalid
        """
        file_ext = Path(filename).suffix.lower()[1:]

        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )

        if file_size > settings.max_file_size:
            raise ValueError(
                f"File too large: {file_size} bytes. "
                f"Maximum size: {settings.max_file_size} bytes"
            )

        return True
