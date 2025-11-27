"""Chart generation service using matplotlib and seaborn."""
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

from app.config import settings
from app.utils.logger import logger
from app.services.s3_client import s3_client


class ChartGenerator:
    """Service for generating charts and plots using matplotlib."""

    def __init__(self):
        """Initialize chart generator."""
        self.supported_types = ["line", "bar", "scatter", "pie", "histogram"]
        sns.set_theme(style="whitegrid")

    async def generate_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        user_id: str = "",
    ) -> Dict[str, Any]:
        """Generate a chart from data.

        Args:
            chart_type: Type of chart (line, bar, scatter, pie, histogram)
            data: Chart data (x, y, labels, etc.)
            title: Chart title
            options: Additional options (xlabel, ylabel, color, grid, etc.)
            user_id: User identifier

        Returns:
            Dict with chart URL, key, and metadata

        Raises:
            ValueError: If chart type is invalid
            Exception: If generation fails
        """
        if chart_type not in self.supported_types:
            raise ValueError(f"Chart type must be one of {self.supported_types}")

        options = options or {}

        try:
            logger.info(f"Generating {chart_type} chart for user {user_id}")

            width, height = self._parse_size(settings.DEFAULT_CHART_SIZE)
            dpi = settings.DEFAULT_CHART_DPI

            fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)

            if chart_type == "line":
                self._create_line_chart(ax, data, options)
            elif chart_type == "bar":
                self._create_bar_chart(ax, data, options)
            elif chart_type == "scatter":
                self._create_scatter_chart(ax, data, options)
            elif chart_type == "pie":
                self._create_pie_chart(ax, data, options)
            elif chart_type == "histogram":
                self._create_histogram_chart(ax, data, options)

            if title:
                ax.set_title(title, fontsize=14, fontweight='bold')

            if options.get("xlabel"):
                ax.set_xlabel(options["xlabel"])
            if options.get("ylabel"):
                ax.set_ylabel(options["ylabel"])

            if options.get("grid", True) and chart_type != "pie":
                ax.grid(True, alpha=0.3)

            plt.tight_layout()

            chart_id = str(uuid.uuid4())
            object_key = f"charts/{chart_id}.png"

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                plt.savefig(tmp_path, dpi=dpi, bbox_inches='tight')

            plt.close(fig)

            metadata = {
                "user_id": user_id,
                "chart_type": chart_type,
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
                    "chart_type": chart_type,
                    "file_size": file_info["size"],
                    "dimensions": settings.DEFAULT_CHART_SIZE,
                    "generated_at": metadata["generated_at"],
                },
            }

        except Exception as e:
            logger.error(f"Chart generation failed: {str(e)}")
            raise

    async def generate_from_code(
        self,
        code: str,
        user_id: str = "",
    ) -> Dict[str, Any]:
        """Generate chart from custom matplotlib code.

        Args:
            code: Python code using matplotlib (must use 'filepath' variable)
            user_id: User identifier

        Returns:
            Dict with chart URL, key, and metadata

        Raises:
            Exception: If code execution fails
        """
        try:
            logger.info(f"Generating chart from custom code for user {user_id}")

            if "import os" in code or "subprocess" in code or "eval" in code:
                raise ValueError("Code contains potentially unsafe operations")

            chart_id = str(uuid.uuid4())
            object_key = f"charts/{chart_id}.png"

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            namespace = {
                "plt": plt,
                "np": np,
                "sns": sns,
                "filepath": tmp_path,
            }

            exec(code, namespace)

            if not Path(tmp_path).exists():
                raise ValueError("Code did not generate a file at filepath")

            metadata = {
                "user_id": user_id,
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
                    "generated_at": metadata["generated_at"],
                },
            }

        except Exception as e:
            logger.error(f"Chart generation from code failed: {str(e)}")
            raise

    def _create_line_chart(self, ax, data: Dict, options: Dict):
        """Create a line chart."""
        x = data.get("x", range(len(data["y"])))
        y = data["y"]
        color = options.get("color", "blue")
        marker = options.get("marker", "o")

        ax.plot(x, y, color=color, marker=marker, linewidth=2, markersize=6)

        if "labels" in data and len(data["labels"]) == len(x):
            ax.set_xticks(x)
            ax.set_xticklabels(data["labels"])

    def _create_bar_chart(self, ax, data: Dict, options: Dict):
        """Create a bar chart."""
        x = data.get("x", range(len(data["y"])))
        y = data["y"]
        color = options.get("color", "steelblue")

        ax.bar(x, y, color=color, width=0.6)

        if "labels" in data and len(data["labels"]) == len(x):
            ax.set_xticks(x)
            ax.set_xticklabels(data["labels"])

    def _create_scatter_chart(self, ax, data: Dict, options: Dict):
        """Create a scatter plot."""
        x = data["x"]
        y = data["y"]
        color = options.get("color", "coral")
        size = options.get("size", 50)

        ax.scatter(x, y, c=color, s=size, alpha=0.6, edgecolors='black')

    def _create_pie_chart(self, ax, data: Dict, options: Dict):
        """Create a pie chart."""
        values = data["y"]
        labels = data.get("labels", [f"Item {i+1}" for i in range(len(values))])

        colors = sns.color_palette("pastel", len(values))
        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
        )
        ax.axis('equal')

    def _create_histogram_chart(self, ax, data: Dict, options: Dict):
        """Create a histogram."""
        values = data["y"]
        bins = options.get("bins", 10)
        color = options.get("color", "skyblue")

        ax.hist(values, bins=bins, color=color, edgecolor='black', alpha=0.7)

    def _parse_size(self, size_str: str) -> tuple:
        """Parse size string to width and height."""
        width, height = map(int, size_str.split("x"))
        return width, height


chart_generator = ChartGenerator()
