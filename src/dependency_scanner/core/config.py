import argparse
import json
from pathlib import Path
from typing import Tuple, Dict, List, Union
import logging

from dependency_scanner.core.types import ScanTask

logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate Arma 3 mission dependencies")
    parser.add_argument("--config", type=Path, default="config.json", help="Path to config file")
    parser.add_argument("--mission", type=Path, help="Single mission to scan")
    parser.add_argument("--mods", type=Path, nargs="+", help="Mod directories to scan")
    parser.add_argument("--cache", type=Path, help="Cache directory")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def _convert_to_path(value: Union[str, List[str], Path]) -> Union[Path, List[Path]]:
    """Convert a value to Path or list of Paths."""
    if isinstance(value, (str, Path)):
        return Path(value)
    elif isinstance(value, list):
        return [Path(v) for v in value]
    raise TypeError(f"Cannot convert {type(value)} to Path")

def load_config(config_path: Path, cli_args) -> Tuple[Dict[str, Path], List[ScanTask], List[Path]]:
    """Load and merge configuration."""
    try:
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
        config = {}
    
    # Parse paths, excluding known list-type paths
    paths = {}
    config_paths = config.get("paths", {})
    for k, v in config_paths.items():
        if k != "missions":  # Skip missions as it's handled separately
            try:
                paths[k] = _convert_to_path(v)
            except Exception as e:
                logger.warning(f"Failed to convert path '{k}': {e}")
    
    # Get missions
    missions = []
    if cli_args.mission:
        missions = [cli_args.mission]
    else:
        mission_paths = config_paths.get("missions", [])
        if isinstance(mission_paths, str):
            mission_paths = [mission_paths]
        missions = [Path(m) for m in mission_paths]
    
    # Get game path
    game_path = paths.get("game")
    if not game_path or not game_path.exists():
        logger.warning(f"Game path not found or invalid: {game_path}")
        game_path = None

    # Get tasks
    tasks = []
    if cli_args.mods:
        # Create single task from CLI args
        mod_paths = cli_args.mods
        if game_path:
            mod_paths = [game_path] + mod_paths
        tasks = [ScanTask(
            name="cli_task",
            mods=[Path(m) for m in mod_paths],
            class_config=Path("class_config.json")
        )]
    else:
        # Load tasks from config
        for task_config in config.get("tasks", []):
            mod_paths = [Path(m) for m in task_config["mods"]]
            if game_path:
                mod_paths = [game_path] + mod_paths
            tasks.append(ScanTask(
                name=task_config["name"],
                mods=mod_paths,
                class_config=Path(task_config.get("class_config", "class_config.json"))
            ))
    
    return paths, tasks, missions
