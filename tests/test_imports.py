def test_import_scene_validation():
    from backend.setup import scene_validation
    assert hasattr(scene_validation, "validate_scene_payload")

def test_import_room_geometry():
    from backend.setup import room_geometry
    assert hasattr(room_geometry, "validate_polygon")

def test_import_shared_keys():
    from shared import scene_keys, result_keys
    assert scene_keys is not None
    assert result_keys is not None

