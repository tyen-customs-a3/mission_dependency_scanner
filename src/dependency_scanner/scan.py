"""Mission dependency scanner for Arma 3."""
import sys
import logging
from pathlib import Path
from typing import List, Optional
import argparse

from dependency_scanner.core.config import load_config, parse_args
from dependency_scanner.core.scanner import DependencyScanner
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
    parser.add_argument("--workers", type=int, default=16, help="Number of worker threads")
    return parser.parse_args()

class Scanner:
    """High-level scanner interface."""
    
    def __init__(self, cache_dir: Path, max_workers: int):
        self.cache_dir = cache_dir
        self.scanner = DependencyScanner(max_workers)
        self.scanner.initialize_apis(cache_dir)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scanner.close()
    
    def execute_scan(self, tasks: List[ScanTask], game_path: Path, missions: List[Path], format_type: str = "text") -> List[Optional[Path]]:
        """Execute complete scan process."""
        try:
            # Initialize scanner
            if not game_path.exists():
                raise ValueError(f"Game path does not exist: {game_path}")
            
            # 1. Scan base game content
            logger.info("Starting base game content scan...")
            self.scanner.scan_base_content(game_path)
            
            # 2. Scan all missions
            logger.info("Starting mission scan...")
            self.scanner.scan_missions(missions)
            
            # 3. Process each task
            reports = []
            for task in tasks:
                logger.info(f"Processing task: {task.name}")
                try:
                    report = self.scanner.execute_task(task, format_type)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Task failed: {task.name} - {e}")
                    reports.append(None)
            
            return reports
            
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            return []

def main() -> int:
    """Main entry point."""
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        paths, tasks, missions = load_config(args.config, args)
        game_path = paths.get("game")
        if not game_path:
            logger.error("Game path not specified")
            return 1

        if not missions or not tasks:
            logger.error("No missions or tasks specified")
            return 1

        cache_dir = Path(args.cache or paths.get("cache", ".cache")).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with Scanner(cache_dir, args.workers) as scanner:
                reports = scanner.execute_scan(tasks, game_path, missions, args.format)
                return 0 if all(reports) else 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return 1
        
    except Exception as e: 
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
