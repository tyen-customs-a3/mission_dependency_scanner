"""Configuration handling for mission dependency scanner."""
from pathlib import Path
import json
from typing import Dict, Any
import os

DEFAULT_CONFIG = {
    "paths": {
        "game": Path(r"C:\Program Files (x86)\Steam\steamapps\common\Arma 3"),
        "mods": Path(r"D:\pca\pcanext"),
        "missions": Path(r"D:\pca\pca_missions"),
        "cache": Path("cache")
    }
}

class Config:
    def __init__(self, config_path: Path = Path("scanner_config.json")):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return {
                    "paths": {
                        k: Path(v) for k, v in config["paths"].items()
                    }
                }
        return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            self.save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def save_config(self, config: Dict[str, Any]) -> None:
        with open(self.config_path, 'w') as f:
            json.dump({
                "paths": {
                    k: str(v) for k, v in config["paths"].items()
                }
            }, f, indent=4)

    @property
    def game_path(self) -> Path:
        return self.config["paths"]["game"]

    @property
    def mods_path(self) -> Path:
        return self.config["paths"]["mods"]

    @property
    def missions_path(self) -> Path:
        return self.config["paths"]["missions"]

    @property
    def cache_path(self) -> Path:
        return self.config["paths"]["cache"]
