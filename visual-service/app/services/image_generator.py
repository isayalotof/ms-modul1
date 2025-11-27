"""Image generation service using OpenAI DALL-E 3."""
import uuid
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
from PIL import Image
import io
from openai import AsyncOpenAI

from app.config import settings
from app.utils.logger import logger
from app.services.s3_client import s3_client
from app.services.anthropic_client import anthropic_client


class ImageGenerator:
    """Service for generating images using DALL-E 3."""

    def __init__(self):
        """Initialize image generator."""
        self.client = None
        if settings.OPENAI_API_KEY:
            # Configure OpenAI client with proxy if available
            http_client = None
            if settings.HTTPS_PROXY:
                import httpx
                http_client = httpx.AsyncClient(
                    proxies={
                        "http://": settings.HTTP_PROXY or settings.HTTPS_PROXY,
                        "https://": settings.HTTPS_PROXY,
                    }
                )
                logger.info(f"OpenAI client configured with HTTPS proxy: {settings.HTTPS_PROXY}")

            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=http_client,
            )

        self.supported_sizes = ["1024x1024", "1024x1792", "1792x1024"]
        self.supported_styles = ["vivid", "natural"]

    async def generate_image(
        self,
        prompt: str,
        style: str = "vivid",
        size: str = "1024x1024",
        user_id: str = "",
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt using DALL-E 3.

        Args:
            prompt: Text description of the image
            style: Image style (vivid or natural)
            size: Image size (1024x1024, 1024x1792, 1792x1024)
            user_id: User identifier for tracking

        Returns:
            Dict with image URL, key, and metadata

        Raises:
            ValueError: If parameters are invalid
            Exception: If generation fails
        """
        if size not in self.supported_sizes:
            raise ValueError(f"Size must be one of {self.supported_sizes}")

        if style not in self.supported_styles:
            raise ValueError(f"Style must be one of {self.supported_styles}")

        try:
            # Enhance prompt using Claude if available
            enhanced_prompt = await anthropic_client.enhance_prompt(prompt, style)
            logger.info(f"Generating image for user {user_id}")

            # Generate image using DALL-E 3
            image_data = await self._generate_with_dalle3(enhanced_prompt, size, style)

            # Save to S3
            image_id = str(uuid.uuid4())
            object_key = f"images/{image_id}.png"

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(image_data)
                tmp_path = tmp_file.name

            metadata = {
                "user_id": user_id,
                "prompt": prompt[:200],
                "enhanced_prompt": enhanced_prompt[:200],
                "style": style,
                "size": size,
                "model": "dall-e-3",
                "generated_at": datetime.utcnow().isoformat(),
            }

            image_url = await s3_client.upload_file(
                tmp_path,
                object_key,
                content_type="image/png",
                metadata=metadata,
            )

            Path(tmp_path).unlink(missing_ok=True)

            file_info = await s3_client.get_file_info(object_key)

            return {
                "status": "success",
                "image_url": image_url,
                "image_key": object_key,
                "metadata": {
                    "size": size,
                    "style": style,
                    "model": "dall-e-3",
                    "file_size": file_info["size"],
                    "generated_at": metadata["generated_at"],
                },
            }

        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            raise

    async def _generate_with_dalle3(
        self,
        prompt: str,
        size: str,
        style: str,
    ) -> bytes:
        """Generate image using DALL-E 3.

        Args:
            prompt: Enhanced prompt
            size: Image size
            style: Image style (vivid or natural)

        Returns:
            Image data as bytes
        """
        if not self.client:
            logger.warning("OpenAI API key not configured, generating placeholder")
            return await self._generate_placeholder_image(size, prompt)

        try:
            logger.info(f"Calling DALL-E 3 API with prompt: {prompt[:100]}...")

            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                style=style,
                n=1,
            )

            image_url = response.data[0].url

            # Download the generated image
            async with aiohttp.ClientSession() as session:
                proxy = settings.HTTPS_PROXY if settings.HTTPS_PROXY else None
                async with session.get(image_url, proxy=proxy) as img_response:
                    if img_response.status != 200:
                        raise Exception(f"Failed to download image: {img_response.status}")

                    image_data = await img_response.read()
                    logger.info(f"Successfully generated image with DALL-E 3")
                    return image_data

        except Exception as e:
            logger.error(f"DALL-E 3 generation failed: {str(e)}, using placeholder")
            return await self._generate_placeholder_image(size, prompt)

    async def _generate_placeholder_image(
        self,
        size: str,
        text: str,
    ) -> bytes:
        """Generate a placeholder image with text.

        Args:
            size: Image size
            text: Text to display

        Returns:
            PNG image data as bytes
        """
        width, height = map(int, size.split("x"))

        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), color=(100, 150, 200))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except Exception:
            font = ImageFont.load_default()

        wrapped_text = text[:100] + "..." if len(text) > 100 else text
        bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        position = ((width - text_width) // 2, (height - text_height) // 2)

        draw.text(position, wrapped_text, fill=(255, 255, 255), font=font)

        watermark = f"{size} - Placeholder (OpenAI API not configured)"
        draw.text((10, 10), watermark, fill=(255, 255, 255, 180))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.read()


image_generator = ImageGenerator()
