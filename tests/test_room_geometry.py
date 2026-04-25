import pytest
from backend.setup.room_geometry import validate_polygon, validate_height

def test_valid_polygon_passes():
    polygon = [[0, 0], [5, 0], [5, 4], [0, 4]]
    validate_polygon(polygon)

def test_polygon_too_few_points_raises():
    with pytest.raises(ValueError, match="at least 3 vertices"):
        validate_polygon([[0, 0], [1, 1]])

def test_polygon_duplicate_points_raises():
    with pytest.raises(ValueError, match="distinct"):
        validate_polygon([[0, 0], [0, 0], [0, 0]])

def test_valid_height_passes():
    result = validate_height(3.0)
    assert float(result) == pytest.approx(3.0)

def test_zero_height_raises():
    with pytest.raises(ValueError, match="height must be"):
        validate_height(0.0)

def test_negative_height_raises():
    with pytest.raises(ValueError, match="height must be"):
        validate_height(-1.0)
