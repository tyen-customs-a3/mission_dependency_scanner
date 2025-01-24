import argparse
import json
from pathlib import Path
from typing import Tuple, Dict, List
from rich.console import Console
from .types import ScanTask

console = Console()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate Arma 3 mission dependencies")
    parser.add_argument("--config", type=Path, default="config.json",
                       help="Path to config file")
    parser.add_argument("--mission", type=Path, help="Override mission path")
    parser.add_argument("--mods", type=Path, nargs="+", help="Additional mod paths")
    parser.add_argument("--cache", type=Path, help="Override cache directory")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    return parser.parse_args()

def load_config(config_path: Path, cli_args) -> Tuple[Dict[str, Path], List[ScanTask], List[Path]]:
    """Load and merge configuration with CLI arguments."""
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        console.print(f"[yellow]Warning:[/yellow] No config file found at {config_path}")
        config = {"paths": {
            "game": "",
            "cache": "cache",
            "missions": []
        }, "tasks": []}
    
    # Load common paths and missions
    paths = {k: Path(v) for k, v in config["paths"].items() if k != "missions"}
    missions = [Path(m) for m in config["paths"].get("missions", [])]
    
    # Load tasks
    tasks = [
        ScanTask(
            name=t["name"],
            mods=[Path(m) for m in t["mods"]],
            class_config=Path(t["class_config"]),
            skip_assets=t.get("skip_assets", False)
        ) for t in config.get("tasks", [])
    ]
    
    # Handle CLI overrides
    if cli_args.mission:
        missions = [cli_args.mission]
        if cli_args.mods:
            tasks = [ScanTask(
                name="cli_task",
                mods=cli_args.mods,
                class_config=paths["class_config"]
            )]
    
    return paths, tasks, missions
