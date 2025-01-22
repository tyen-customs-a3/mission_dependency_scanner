"""Common test fixtures."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_asset_api():
    with patch('asset_scanner.AssetAPI') as mock:
        mock.return_value.get_all_assets.return_value = {
            "@mod/textures/test.paa",
            "@mod/models/test.p3d"
        }
        yield mock

@pytest.fixture
def mock_class_api():
    with patch('ini_class_parser.ClassHierarchyAPI') as mock:
        mock.return_value.get_all_classes.return_value = {
            "Vehicle": {"Car", "Tank"},
            "Weapon": {"Rifle", "Pistol"}
        }
        yield mock

@pytest.fixture
def mock_mission_scanner():
    with patch('mission_scanner.Scanner') as mock:
        mock.return_value.scan_directory.return_value = [{
            "file": "mission.sqm",
            "equipment": ["@mod/textures/test.paa", "Car"]
        }]
        yield mock

@pytest.fixture
def temp_config(tmp_path):
    config = {
        "paths": {
            "game": str(tmp_path / "game"),
            "mods": str(tmp_path / "mods"),
            "missions": str(tmp_path / "missions"),
            "cache": str(tmp_path / "cache")
        }
    }
    config_file = tmp_path / "config.json"
    import json
    config_file.write_text(json.dumps(config))
    return config_file
