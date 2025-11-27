"""Claude-powered chart generation agent using text descriptions."""
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json

from anthropic import AsyncAnthropic
from app.config import settings
from app.utils.logger import logger
from app.services.s3_client import s3_client


class ClaudeChartAgent:
    """Agent that generates charts from natural language descriptions using Claude Sonnet 4.5."""

    def __init__(self):
        """Initialize Claude chart agent."""
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            # Configure HTTP client with proxy if available
            http_client = None
            if settings.HTTPS_PROXY:
                import httpx
                http_client = httpx.AsyncClient(
                    proxies={
                        "http://": settings.HTTP_PROXY or settings.HTTPS_PROXY,
                        "https://": settings.HTTPS_PROXY,
                    }
                )
                logger.info(f"Claude agent configured with HTTPS proxy: {settings.HTTPS_PROXY}")

            self.client = AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                http_client=http_client,
            )

    async def generate_chart_from_description(
        self,
        description: str,
        user_id: str = "",
    ) -> Dict[str, Any]:
        """Generate a chart from natural language description using Claude agent.

        Args:
            description: Natural language description of the desired chart
            user_id: User identifier

        Returns:
            Dict with chart URL, key, and metadata

        Raises:
            Exception: If generation fails
        """
        if not self.client:
            raise Exception("Anthropic API key not configured")

        try:
            logger.info(f"Generating chart from description for user {user_id}")

            # Use Claude to generate matplotlib code
            chart_code = await self._generate_chart_code(description)

            # Execute the code and generate chart
            chart_id = str(uuid.uuid4())
            object_key = f"charts/{chart_id}.png"

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Execute the generated code
            namespace = {
                "plt": plt,
                "np": np,
                "sns": sns,
                "filepath": tmp_path,
            }

            # Set seaborn theme
            sns.set_theme(style="whitegrid")

            try:
                exec(chart_code, namespace)
            except Exception as e:
                logger.error(f"Error executing generated code: {str(e)}")
                raise Exception(f"Failed to execute chart code: {str(e)}")

            if not Path(tmp_path).exists():
                raise Exception("Chart code did not generate a file")

            # Upload to S3
            metadata = {
                "user_id": user_id,
                "description": description[:200],
                "generated_by": "claude-sonnet-4.5",
                "generated_at": datetime.utcnow().isoformat(),
            }

            chart_url = await s3_client.upload_file(
                tmp_path,
                object_key,
                content_type="image/png",
                metadata=metadata,
            )

            Path(tmp_path).unlink(missing_ok=True)

            file_info = await s3_client.get_file_info(object_key)

            return {
                "status": "success",
                "chart_url": chart_url,
                "chart_key": object_key,
                "metadata": {
                    "file_size": file_info["size"],
                    "generated_by": "claude-sonnet-4.5",
                    "description": description[:200],
                    "generated_at": metadata["generated_at"],
                },
            }

        except Exception as e:
            logger.error(f"Chart generation from description failed: {str(e)}")
            raise

    async def _generate_chart_code(self, description: str) -> str:
        """Generate matplotlib code from natural language description using Claude.

        Args:
            description: Natural language description of chart

        Returns:
            Python code string for generating the chart
        """
        system_prompt = """You are an expert data visualization specialist. Your task is to generate Python code using matplotlib and seaborn to create charts based on natural language descriptions.

Requirements:
1. Generate complete, executable Python code
2. Use matplotlib (plt), numpy (np), and seaborn (sns) - these are already imported
3. The code MUST save the figure using: plt.savefig(filepath, dpi=300, bbox_inches='tight')
4. Always call plt.close() after saving to free memory
5. If data is not provided, generate realistic sample data
6. Make the chart visually appealing with proper labels, titles, and colors
7. Use appropriate chart types based on the description
8. DO NOT include any imports - plt, np, sns, and filepath are already available
9. DO NOT include any explanatory text - only executable Python code

Chart types you can create:
- Line charts, bar charts, scatter plots, pie charts, histograms
- Heatmaps, box plots, violin plots, area charts
- Multi-panel figures, subplots
- Statistical visualizations

Example output format:
```python
# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, y, linewidth=2, color='blue')
ax.set_title('Sine Wave', fontsize=14, fontweight='bold')
ax.set_xlabel('X axis')
ax.set_ylabel('Y axis')
ax.grid(True, alpha=0.3)

# Save and close
plt.savefig(filepath, dpi=300, bbox_inches='tight')
plt.close()
```

Remember: Return ONLY the Python code, no explanations or markdown formatting."""

        try:
            logger.info(f"Requesting chart code from Claude for: {description[:100]}...")

            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate matplotlib code for this chart:\n\n{description}",
                    }
                ],
                system=system_prompt,
            )

            code = response.content[0].text.strip()

            # Clean up code (remove markdown code blocks if present)
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            code = code.strip()

            logger.info(f"Generated chart code ({len(code)} chars)")
            logger.debug(f"Chart code:\n{code}")

            return code

        except Exception as e:
            logger.error(f"Failed to generate chart code: {str(e)}")
            raise Exception(f"Claude API error: {str(e)}")


claude_chart_agent = ClaudeChartAgent()
