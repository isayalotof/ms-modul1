"""API request and response schemas."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(..., description="Description of the image to generate")
    style: str = Field(
        default="realistic",
        description="Image style: realistic, artistic, minimalist",
    )
    size: str = Field(
        default="1024x1024",
        description="Image size: 512x512, 1024x1024, 1024x1792",
    )
    user_id: str = Field(..., description="User identifier")


class ImageMetadata(BaseModel):
    """Image metadata."""

    size: str
    style: str
    file_size: int
    generated_at: str


class GenerateImageResponse(BaseModel):
    """Response model for image generation."""

    status: str
    image_url: str
    image_key: str
    metadata: ImageMetadata


class ChartData(BaseModel):
    """Chart data model."""

    x: Optional[List[Any]] = None
    y: List[Any]
    labels: Optional[List[str]] = None


class ChartOptions(BaseModel):
    """Chart options model."""

    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    color: Optional[str] = None
    grid: bool = True
    marker: Optional[str] = None
    size: Optional[int] = None
    bins: Optional[int] = None


class GenerateChartRequest(BaseModel):
    """Request model for chart generation."""

    chart_type: str = Field(
        ...,
        description="Chart type: line, bar, scatter, pie, histogram",
    )
    data: ChartData = Field(..., description="Chart data")
    title: Optional[str] = Field(None, description="Chart title")
    options: Optional[ChartOptions] = Field(None, description="Chart options")
    user_id: str = Field(..., description="User identifier")


class ChartMetadata(BaseModel):
    """Chart metadata."""

    chart_type: str
    file_size: int
    dimensions: str
    generated_at: str


class GenerateChartResponse(BaseModel):
    """Response model for chart generation."""

    status: str
    chart_url: str
    chart_key: str
    metadata: ChartMetadata


class GenerateChartFromCodeRequest(BaseModel):
    """Request model for chart generation from code."""

    code: str = Field(
        ...,
        description="Python code using matplotlib (must use 'filepath' variable)",
    )
    user_id: str = Field(..., description="User identifier")


class ChartFromCodeMetadata(BaseModel):
    """Chart from code metadata."""

    file_size: int
    generated_at: str


class GenerateChartFromCodeResponse(BaseModel):
    """Response model for chart generation from code."""

    status: str
    chart_url: str
    chart_key: str
    metadata: ChartFromCodeMetadata


class FileMetadata(BaseModel):
    """File metadata model."""

    size: int
    content_type: str
    last_modified: str


class FileInfoResponse(BaseModel):
    """Response model for file info."""

    status: str
    file_key: str
    file_url: str
    presigned_url: str
    metadata: FileMetadata


class DeleteFileResponse(BaseModel):
    """Response model for file deletion."""

    status: str
    message: str
    file_key: str


class DependencyStatus(BaseModel):
    """Dependency status model."""

    s3: str
    anthropic_api: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    service: str
    version: str
    dependencies: DependencyStatus
    timestamp: str


class MetricsResponse(BaseModel):
    """Response model for metrics."""

    total_images_generated: int
    total_charts_generated: int
    total_storage_used: str
    uptime: str
    requests_per_minute: float


class ErrorResponse(BaseModel):
    """Error response model."""

    status: str = "error"
    message: str
    details: Optional[str] = None
