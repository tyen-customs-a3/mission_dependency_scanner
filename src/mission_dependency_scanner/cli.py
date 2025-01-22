"""Command line interface for mission dependency scanner."""
import argparse
from pathlib import Path
from typing import List
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from mission_dependency_scanner import DependencyScanner
from mission_dependency_scanner.config import Config

console = Console()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan mission dependencies against mod content")
    parser.add_argument("--mission", type=Path, help="Path to mission folder")
    parser.add_argument("--mods", type=Path, nargs="*", help="Additional mod paths")
    parser.add_argument("--cache", type=Path, help="Cache directory")
    parser.add_argument("--config", type=Path, default=Path("scanner_config.json"), help="Config file path")
    return parser.parse_args()

def scan_mods(scanner: DependencyScanner, mod_paths: List[Path]) -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        for mod_path in progress.track(mod_paths, description="Scanning mods..."):
            console.print(f"Processing: {mod_path}")
            scanner.build_asset_database([mod_path])
            scanner.build_class_database([mod_path / "config.cpp"])

def print_results(result, mission_path: Path) -> None:
    console.print(f"\n[bold]Results for mission:[/bold] {mission_path}")
    
    table = Table(show_header=True)
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("Valid Assets", str(len(result.valid_assets)))
    table.add_row("Valid Classes", str(len(result.valid_classes)))
    table.add_row("Missing Assets", str(len(result.missing_assets)))
    table.add_row("Missing Classes", str(len(result.missing_classes)))
    
    console.print(table)
    
    if result.missing_assets:
        console.print("\n[red]Missing Assets:[/red]")
        for asset in sorted(result.missing_assets):
            console.print(f"  - {asset}")
            
    if result.missing_classes:
        console.print("\n[red]Missing Classes:[/red]")
        for class_name in sorted(result.missing_classes):
            console.print(f"  - {class_name}")

def main() -> int:
    args = parse_args()
    config = Config(args.config)
    
    # Use config paths with optional CLI overrides
    cache_dir = args.cache or config.cache_path
    mission_path = args.mission or config.missions_path
    mod_paths = [config.mods_path]
    if args.mods:
        mod_paths.extend(args.mods)
    
    scanner = DependencyScanner(cache_dir)
    
    try:
        scan_mods(scanner, mod_paths)
        result = scanner.validate_mission(mission_path)
        print_results(result, mission_path)
        return 0
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
