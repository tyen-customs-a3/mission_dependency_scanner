import argparse
import json
from pathlib import Path
from typing import Tuple, Dict, List, Union, Any, TypeVar, cast, Optional, overload
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

T = TypeVar('T')

@overload
def _convert_to_path(value: Union[str, Path]) -> Path: ...

@overload
def _convert_to_path(value: List[str]) -> List[Path]: ...

def _convert_to_path(value: Union[str, List[str], Path]) -> Union[Path, List[Path]]:
    """Convert a value to Path or list of Paths."""
    if isinstance(value, (str, Path)):
        return Path(value)
    elif isinstance(value, list):
        return [Path(v) for v in value]
    raise TypeError(f"Cannot convert {type(value)} to Path")

def load_config(config_path: Path, cli_args: argparse.Namespace) -> Tuple[Dict[str, Path], List[ScanTask], List[Path]]:
    """Load and merge configuration."""
    try:
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
        config = {}
    
    paths: Dict[str, Path] = {}
    config_paths = config.get("paths", {})
    for k, v in config_paths.items():
        if k != "missions":
            try:
                converted = _convert_to_path(v)
                if not isinstance(converted, list):
                    paths[k] = converted
            except Exception as e:
                logger.warning(f"Failed to convert path '{k}': {e}")
    
    missions: List[Path] = []
    if cli_args.mission:
        missions = [cli_args.mission]
    else:
        mission_paths = config_paths.get("missions", [])
        if isinstance(mission_paths, str):
            mission_paths = [mission_paths]
        missions = [Path(m) for m in mission_paths]
    
    tasks: List[ScanTask] = []
    if cli_args.mods:
        tasks = [ScanTask(
            name="cli_task",
            data_path=[Path(m) for m in cli_args.mods],
            ignore_patterns=config.get("ignore_patterns", [])
        )]
    else:
        for task_config in config.get("tasks", []):
            mod_paths = [Path(m) for m in task_config["mods"]]
            tasks.append(ScanTask(
                name=task_config["name"],
                data_path=mod_paths,
                ignore_patterns=task_config.get("ignore_patterns", []) or config.get("ignore_patterns", [])
            ))
    
    return paths, tasks, missions
