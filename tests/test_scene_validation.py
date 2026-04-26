import pytest
from backend.setup.scene_validation import validate_scene_payload

def _minimal_valid_scene():
    return {
        "room": {
            "geometry_mode": "room_volume_prism",
            "floor_polygon": [[0,0],[5,0],[5,4],[0,4]],
            "height": 3.0,
            "z_floor": 0.0,
            "source_object_name": "RoomVolume",
        },
        "simulation": {
            "fs": 16000,
            "max_order": 3,
            "air_absorption": False,
            "engine": "ISM_ONLY",
        },
        "band": {"key": "500"},
        "materials": {
            "walls": "reflective_plaster",
            "floor": "wood",
            "ceiling": "reflective_plaster",
            "material_details": {},
        },
        "sources": [
            {
                "name": "SRC_1",
                "position": [2.5, 2.0, 1.5],
                "world_position": [2.5, 2.0, 1.5],
            }
        ],
        "receiver_areas": [
            {
                "name": "MAP_Main",
                "mapping": {
                    "name": "MAP_Main",
                    "spacing": 0.5,
                    "num_x": 2,
                    "num_y": 2,
                    "num_receivers": 4,
                    "world_z": 0.8,
                    "area_width": 5.0,
                    "area_depth": 4.0,
                    "polygon": [[0,0],[5,0],[5,4],[0,4]],
                },
                "receivers": [
                    {
                        "id": 0,
                        "position": [1.0, 1.0, 0.8],
                        "world_position": [1.0, 1.0, 0.8],
                    }
                ],
            }
        ],
    }

def test_valid_scene_passes():
    validate_scene_payload(_minimal_valid_scene())

def test_missing_sources_raises():
    scene = _minimal_valid_scene()
    scene["sources"] = []
    with pytest.raises(ValueError, match="SRC_"):
        validate_scene_payload(scene)

def test_missing_receiver_areas_raises():
    scene = _minimal_valid_scene()
    scene["receiver_areas"] = []
    with pytest.raises(ValueError, match="MAP_"):
        validate_scene_payload(scene)

def test_invalid_geometry_mode_raises():
    scene = _minimal_valid_scene()
    scene["room"]["geometry_mode"] = "invalid_mode"
    with pytest.raises(ValueError, match="geometry_mode"):
        validate_scene_payload(scene)

def test_negative_height_raises():
    scene = _minimal_valid_scene()
    scene["room"]["height"] = -1.0
    with pytest.raises(ValueError, match="height"):
        validate_scene_payload(scene)
