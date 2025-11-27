"""Tests for services."""
import pytest
from app.services.chart_generator import ChartGenerator


@pytest.fixture
def chart_generator():
    """Create chart generator instance."""
    return ChartGenerator()


def test_chart_generator_supported_types(chart_generator):
    """Test supported chart types."""
    assert "line" in chart_generator.supported_types
    assert "bar" in chart_generator.supported_types
    assert "scatter" in chart_generator.supported_types
    assert "pie" in chart_generator.supported_types
    assert "histogram" in chart_generator.supported_types


def test_parse_size(chart_generator):
    """Test size parsing."""
    width, height = chart_generator._parse_size("800x600")
    assert width == 800
    assert height == 600

    width, height = chart_generator._parse_size("1024x768")
    assert width == 1024
    assert height == 768


@pytest.mark.asyncio
async def test_generate_chart_invalid_type(chart_generator):
    """Test chart generation with invalid type."""
    with pytest.raises(ValueError):
        await chart_generator.generate_chart(
            chart_type="invalid",
            data={"y": [1, 2, 3]},
            user_id="test",
        )


@pytest.mark.asyncio
async def test_generate_from_code_unsafe(chart_generator):
    """Test chart generation with unsafe code."""
    unsafe_code = "import os; os.system('rm -rf /')"

    with pytest.raises(ValueError):
        await chart_generator.generate_from_code(
            code=unsafe_code,
            user_id="test",
        )
