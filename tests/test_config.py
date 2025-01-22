"""Test configuration handling."""
import pytest
from pathlib import Path
from mission_dependency_scanner.config import Config

def test_config_load(temp_config):
    config = Config(temp_config)
    assert config.game_path.exists()
    assert config.mods_path.exists()
    assert config.missions_path.exists()
    assert config.cache_path.exists()

def test_config_defaults():
    config = Config(Path("nonexistent.json"))
    assert isinstance(config.game_path, Path)
    assert isinstance(config.mods_path, Path)
    assert isinstance(config.missions_path, Path)
    assert isinstance(config.cache_path, Path)
