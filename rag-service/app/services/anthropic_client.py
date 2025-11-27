from typing import List, Dict, Any, AsyncGenerator
from anthropic import AsyncAnthropic
from app.config import settings
from app.utils.logger import logger


class AnthropicClient:
    """Client for interacting with Anthropic's Claude API"""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.max_tokens

    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response using Claude with RAG context.

        Args:
            query: User query
            context: List of relevant document chunks
            stream: Whether to stream the response

        Returns:
            Response with answer and metadata
        """
        try:
            # Build context string
            context_str = self._build_context(context)

            # Build prompt
            prompt = self._build_prompt(query, context_str)

            if stream:
                return await self._generate_streaming(prompt)
            else:
                return await self._generate_complete(prompt)

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    async def _generate_complete(self, prompt: str) -> Dict[str, Any]:
        """Generate complete response"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            answer = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            return {
                "answer": answer,
                "tokens_used": tokens_used,
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Error in complete generation: {str(e)}")
            raise

    async def _generate_streaming(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response"""
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ) as stream:
                async for text in stream.text_stream:
                    yield {
                        "type": "text",
                        "content": text
                    }

                # Get final message with token usage
                message = await stream.get_final_message()
                tokens_used = message.usage.input_tokens + message.usage.output_tokens

                yield {
                    "type": "complete",
                    "tokens_used": tokens_used,
                    "model": self.model
                }

        except Exception as e:
            logger.error(f"Error in streaming generation: {str(e)}")
            raise

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from chunks"""
        if not chunks:
            return "Нет доступного контекста."

        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            source = f"[Источник {idx}: {chunk['document_name']}"
            if chunk.get('metadata', {}).get('page'):
                source += f", стр. {chunk['metadata']['page']}"
            source += "]"

            context_parts.append(
                f"{source}\n{chunk['content']}\n"
            )

        return "\n---\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt for Claude"""
        return f"""Ты - полезный AI-ассистент. Твоя задача - ответить на вопрос пользователя на основе предоставленного контекста из документов.

КОНТЕКСТ ИЗ ДОКУМЕНТОВ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

ИНСТРУКЦИИ:
1. Внимательно прочитай контекст из документов
2. Ответь на вопрос пользователя, основываясь ТОЛЬКО на информации из контекста
3. Если в контексте нет информации для ответа на вопрос, честно скажи об этом
4. Структурируй ответ, используй списки и примеры из контекста
5. Укажи источники информации (названия документов, страницы)
6. Отвечай на русском языке

ОТВЕТ:"""


# Global Anthropic client instance
anthropic_client = AnthropicClient()
