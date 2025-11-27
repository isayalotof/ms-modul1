"""API routes for Visual Service."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import (
    GenerateImageRequest,
    GenerateImageResponse,
    GenerateChartRequest,
    GenerateChartResponse,
    GenerateChartFromCodeRequest,
    GenerateChartFromCodeResponse,
    GenerateChartFromTextRequest,
    GenerateChartFromTextResponse,
    FileInfoResponse,
    DeleteFileResponse,
    HealthResponse,
    MetricsResponse,
    ErrorResponse,
)
from app.services import (
    image_generator,
    chart_generator,
    claude_chart_agent,
    s3_client,
    anthropic_client,
)
from app.config import settings
from app.utils.logger import logger


router = APIRouter()


@router.post(
    "/api/v1/visual/generate-image",
    response_model=GenerateImageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_image(request: GenerateImageRequest):
    """Generate an image from a text prompt.

    Args:
        request: Image generation request

    Returns:
        Image generation response with URL and metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        result = await image_generator.generate_image(
            prompt=request.prompt,
            style=request.style,
            size=request.size,
            user_id=request.user_id,
        )
        return result

    except ValueError as e:
        logger.error(f"Invalid parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Invalid prompt or parameters", "details": str(e)},
        )

    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Image generation failed", "details": str(e)},
        )


@router.post(
    "/api/v1/visual/generate-chart",
    response_model=GenerateChartResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_chart(request: GenerateChartRequest):
    """Generate a chart from data.

    Args:
        request: Chart generation request

    Returns:
        Chart generation response with URL and metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        result = await chart_generator.generate_chart(
            chart_type=request.chart_type,
            data=request.data.model_dump(),
            title=request.title,
            options=request.options.model_dump() if request.options else None,
            user_id=request.user_id,
        )
        return result

    except ValueError as e:
        logger.error(f"Invalid chart parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Invalid chart data or type", "details": str(e)},
        )

    except Exception as e:
        logger.error(f"Chart generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Chart generation failed", "details": str(e)},
        )


@router.post(
    "/api/v1/visual/generate-chart-from-code",
    response_model=GenerateChartFromCodeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_chart_from_code(request: GenerateChartFromCodeRequest):
    """Generate a chart from custom matplotlib code.

    Args:
        request: Chart from code generation request

    Returns:
        Chart generation response with URL and metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        result = await chart_generator.generate_from_code(
            code=request.code,
            user_id=request.user_id,
        )
        return result

    except ValueError as e:
        logger.error(f"Invalid or unsafe code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Invalid or unsafe code", "details": str(e)},
        )

    except Exception as e:
        logger.error(f"Chart generation from code failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Chart generation from code failed", "details": str(e)},
        )


@router.post(
    "/api/v1/visual/generate-chart-from-text",
    response_model=GenerateChartFromTextResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_chart_from_text(request: GenerateChartFromTextRequest):
    """Generate a chart from natural language description using Claude Sonnet 4.5.

    Args:
        request: Chart from text generation request

    Returns:
        Chart generation response with URL and metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        result = await claude_chart_agent.generate_chart_from_description(
            description=request.description,
            user_id=request.user_id,
        )
        return result

    except Exception as e:
        logger.error(f"Chart generation from text failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Chart generation from text failed", "details": str(e)},
        )


@router.get(
    "/api/v1/visual/file/{file_key:path}",
    response_model=FileInfoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_file_info(file_key: str):
    """Get file information and presigned URL.

    Args:
        file_key: S3 object key

    Returns:
        File information with presigned URL

    Raises:
        HTTPException: If file not found
    """
    try:
        file_info = await s3_client.get_file_info(file_key)
        presigned_url = await s3_client.generate_presigned_url(file_key)
        file_url = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/{file_key}"

        return {
            "status": "success",
            "file_key": file_key,
            "file_url": file_url,
            "presigned_url": presigned_url,
            "metadata": file_info,
        }

    except Exception as e:
        logger.error(f"File not found: {file_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "File not found"},
        )


@router.delete(
    "/api/v1/visual/file/{file_key:path}",
    response_model=DeleteFileResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def delete_file(file_key: str):
    """Delete a file from storage.

    Args:
        file_key: S3 object key

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If file not found or deletion fails
    """
    try:
        await s3_client.delete_file(file_key)

        return {
            "status": "success",
            "message": "File deleted successfully",
            "file_key": file_key,
        }

    except Exception as e:
        logger.error(f"Failed to delete file: {file_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "File not found"},
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """Health check endpoint.

    Returns:
        Service health status and dependencies
    """
    s3_status = "ok" if await s3_client.check_health() else "error"
    anthropic_status = "ok" if await anthropic_client.check_health() else "error"

    overall_status = "healthy" if s3_status == "ok" else "unhealthy"

    response_status = (
        status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return {
        "status": overall_status,
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "dependencies": {
            "s3": s3_status,
            "anthropic_api": anthropic_status,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_metrics():
    """Get service metrics.

    Returns:
        Service usage metrics
    """
    return {
        "total_images_generated": 0,
        "total_charts_generated": 0,
        "total_storage_used": "0 GB",
        "uptime": "0h 0m",
        "requests_per_minute": 0.0,
    }
