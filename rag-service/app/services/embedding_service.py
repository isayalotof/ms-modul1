import asyncio
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.utils.logger import logger


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self):
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size
        self.model = None
        logger.info(f"Initializing embedding service with model: {self.model_name}")

    def _load_model(self):
        """Lazy load the embedding model"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        self._load_model()

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.model.encode,
                text
            )

            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        self._load_model()

        try:
            all_embeddings = []

            # Process in batches
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]

                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    self.model.encode,
                    batch
                )

                all_embeddings.extend(embeddings.tolist())

                logger.info(f"Generated embeddings for batch {i // self.batch_size + 1}")

            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise

    def get_model_info(self) -> dict:
        """Get information about the embedding model"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "loaded": self.model is not None
        }


# Global embedding service instance
embedding_service = EmbeddingService()
