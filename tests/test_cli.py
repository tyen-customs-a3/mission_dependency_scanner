"""Test CLI functionality."""
import pytest
from pathlib import Path
from mission_dependency_scanner.cli import main

def test_cli_with_config(temp_config, mock_asset_api, mock_class_api, mock_mission_scanner):
    import sys
    sys.argv = ["scan-mission", "--config", str(temp_config)]
    assert main() == 0

def test_cli_with_missing_mission(temp_config, mock_asset_api, mock_class_api, mock_mission_scanner):
    import sys
    mock_mission_scanner.return_value.scan_directory.side_effect = FileNotFoundError
    sys.argv = ["scan-mission", "--config", str(temp_config)]
    assert main() == 1
