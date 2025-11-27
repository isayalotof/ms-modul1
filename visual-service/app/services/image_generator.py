"""Image generation service using external APIs."""
import uuid
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
from PIL import Image
import io

from app.config import settings
from app.utils.logger import logger
from app.services.s3_client import s3_client
from app.services.anthropic_client import anthropic_client


class ImageGenerator:
    """Service for generating images using AI models."""

    def __init__(self):
        """Initialize image generator."""
        self.api_key = settings.IMAGE_GEN_API_KEY
        self.supported_sizes = ["512x512", "1024x1024", "1024x1792"]
        self.supported_styles = ["realistic", "artistic", "minimalist"]

    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        user_id: str = "",
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            style: Image style (realistic, artistic, minimalist)
            size: Image size (512x512, 1024x1024, 1024x1792)
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
            enhanced_prompt = await anthropic_client.enhance_prompt(prompt, style)
            logger.info(f"Generating image for user {user_id}")

            image_data = await self._call_image_api(enhanced_prompt, size, style)

            image_id = str(uuid.uuid4())
            object_key = f"images/{image_id}.png"

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(image_data)
                tmp_path = tmp_file.name

            metadata = {
                "user_id": user_id,
                "prompt": prompt[:200],
                "style": style,
                "size": size,
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
                    "file_size": file_info["size"],
                    "generated_at": metadata["generated_at"],
                },
            }

        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            raise

    async def _call_image_api(
        self,
        prompt: str,
        size: str,
        style: str,
    ) -> bytes:
        """Call external image generation API.

        This is a placeholder implementation. In production, integrate with:
        - Stability AI (Stable Diffusion)
        - OpenAI (DALL-E)
        - Midjourney API
        - or other image generation services

        Args:
            prompt: Enhanced prompt
            size: Image size
            style: Image style

        Returns:
            Image data as bytes
        """
        if not self.api_key:
            logger.warning("No image API key configured, generating placeholder")
            return await self._generate_placeholder_image(size, prompt)

        width, height = map(int, size.split("x"))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.example.com/v1/generate",
                    json={
                        "prompt": prompt,
                        "width": width,
                        "height": height,
                        "style": style,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        raise Exception(f"API returned status {response.status}")

                    return await response.read()

        except Exception as e:
            logger.warning(f"External API call failed: {str(e)}, using placeholder")
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

        watermark = f"{size} - Placeholder"
        draw.text((10, 10), watermark, fill=(255, 255, 255, 180))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.read()


image_generator = ImageGenerator()
