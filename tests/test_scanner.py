"""Test scanner functionality."""
import pytest
from pathlib import Path
from mission_dependency_scanner import DependencyScanner

def test_scanner_init(mock_asset_api, mock_class_api, mock_mission_scanner):
    scanner = DependencyScanner(Path("cache"))
    assert scanner.asset_api is not None
    assert scanner.class_api is not None
    assert scanner.mission_scanner is not None

def test_validate_mission(mock_asset_api, mock_class_api, mock_mission_scanner):
    scanner = DependencyScanner(Path("cache"))
    result = scanner.validate_mission(Path("test_mission"))
    
    assert len(result.valid_assets) == 1
    assert len(result.valid_classes) == 1
    assert len(result.missing_assets) == 0
    assert len(result.missing_classes) == 0

def test_missing_dependencies(mock_asset_api, mock_class_api, mock_mission_scanner):
    mock_mission_scanner.return_value.scan_directory.return_value = [{
        "file": "mission.sqm",
        "equipment": ["@mod/missing.paa", "MissingClass"]
    }]
    
    scanner = DependencyScanner(Path("cache"))
    result = scanner.validate_mission(Path("test_mission"))
    
    assert len(result.missing_assets) == 1
    assert len(result.missing_classes) == 1
