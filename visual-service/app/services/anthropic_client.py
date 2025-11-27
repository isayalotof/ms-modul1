"""Anthropic Claude API client for prompt analysis."""
from typing import Optional
import httpx
from anthropic import AsyncAnthropic
from app.config import settings
from app.utils.logger import logger


class AnthropicClient:
    """Async Anthropic Claude client for prompt analysis and enhancement."""

    def __init__(self):
        """Initialize Anthropic client."""
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            # Configure HTTP client with proxy if available
            http_client = None
            if settings.HTTPS_PROXY:
                http_client = httpx.AsyncClient(
                    proxies={
                        "http://": settings.HTTP_PROXY or settings.HTTPS_PROXY,
                        "https://": settings.HTTPS_PROXY,
                    }
                )
                logger.info(f"Anthropic client configured with HTTPS proxy: {settings.HTTPS_PROXY}")

            self.client = AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                http_client=http_client,
            )

    async def enhance_prompt(self, prompt: str, style: str = "realistic") -> str:
        """Enhance image generation prompt using Claude.

        Args:
            prompt: Original prompt
            style: Desired style (realistic, artistic, minimalist)

        Returns:
            Enhanced prompt

        Raises:
            Exception: If API call fails
        """
        if not self.client:
            logger.warning("Anthropic API key not configured, returning original prompt")
            return prompt

        try:
            system_prompt = f"""You are an expert at creating detailed image generation prompts.
Enhance the given prompt to be more specific and detailed while maintaining the {style} style.
Keep the enhanced prompt concise (max 200 words) but visually descriptive.
Focus on visual elements, composition, lighting, and atmosphere."""

            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": f"Enhance this image prompt: {prompt}",
                    }
                ],
                system=system_prompt,
            )

            enhanced = message.content[0].text.strip()
            logger.info(f"Prompt enhanced successfully")
            return enhanced

        except Exception as e:
            logger.error(f"Failed to enhance prompt: {str(e)}")
            return prompt

    async def analyze_chart_code(self, code: str) -> dict:
        """Analyze custom chart code for safety and validity.

        Args:
            code: Python code to analyze

        Returns:
            Analysis result dict with 'safe' and 'message' keys
        """
        if not self.client:
            logger.warning("Anthropic API key not configured, skipping code analysis")
            return {"safe": True, "message": "Analysis skipped (no API key)"}

        try:
            system_prompt = """You are a code security analyst. Analyze the given matplotlib/Python code for:
1. Security issues (file access, network calls, shell commands)
2. Dangerous imports or operations
3. Whether it's a valid matplotlib chart generation code

Respond with JSON format: {"safe": true/false, "message": "explanation"}"""

            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze this code:\n\n```python\n{code}\n```",
                    }
                ],
                system=system_prompt,
            )

            result_text = message.content[0].text.strip()

            import json
            result = json.loads(result_text)
            logger.info(f"Code analysis completed: {result['safe']}")
            return result

        except Exception as e:
            logger.error(f"Failed to analyze code: {str(e)}")
            return {"safe": False, "message": f"Analysis failed: {str(e)}"}

    async def check_health(self) -> bool:
        """Check Anthropic API health.

        Returns:
            True if API is accessible
        """
        if not self.client:
            return False

        try:
            await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return True

        except Exception as e:
            logger.error(f"Anthropic health check failed: {str(e)}")
            return False


anthropic_client = AnthropicClient()
