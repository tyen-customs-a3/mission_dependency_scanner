"""Mission dependency scanner for Arma 3."""
import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict
import argparse

from mission_scanner import ScanResult

from dependency_scanner.core.config import load_config
from dependency_scanner.core.types import ScanTask
from dependency_scanner.core.scanning.content_scanner import ContentScanResult, ContentScanner
from dependency_scanner.core.validation.task_validator import TaskValidator
from dependency_scanner.core.scanning.mission_scanner import MissionScanningService
from dependency_scanner.core.analysis.result_differ import ResultDiffer

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
    parser.add_argument("--workers", type=int, default=31, help="Number of worker threads")
    return parser.parse_args()

class Scanner:
    """High-level scanner interface."""
    
    def __init__(self, cache_dir: Path, game_path: Path, max_workers: int):
        self.cache_dir = cache_dir
        self.game_path = game_path
        self.max_workers = max_workers
        
        # Initialize components with consistent cache paths
        self.mission_scanner = MissionScanningService(
            max_workers=max_workers,
            cache_dir=cache_dir  # Parent cache dir, service will append "missions"
        )
        self.content_scanner = ContentScanner(cache_dir, max_workers)
        self.task_validator = TaskValidator(max_workers, cache_dir / "reports")
        self.task_results = {}  # Store results by task name
        
    def __enter__(self) -> 'Scanner':
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type: Optional[type], 
                 exc_val: Optional[Exception], 
                 exc_tb: Optional[type]) -> None:
        """Context manager exit with cleanup."""
        # Clean up resources
        if hasattr(self, 'content_scanner'):
            self.content_scanner.close()
        if hasattr(self, 'mission_scanner'):
            self.mission_scanner.close()
            
    def execute_scan(self, tasks: List[ScanTask], missions: List[Path], format_type: str = "text") -> bool:
        """Execute complete scan process."""
        try:
            # Scan missions - use results directly without conversion
            mission_results = self.mission_scanner.scan_missions(missions)
            if not mission_results:
                raise RuntimeError("Mission scan failed")

            # Scan game content
            game_task = ScanTask(
                name="base_game",
                data_path=[self.game_path]
            )
            
            game_content = self.content_scanner.scan_content(game_task, is_mod_folder=False)
            
            if not game_content:
                raise RuntimeError("Game content scan failed")
            
            # Process each task and store results
            success = True
            ordered_task_names = []
            for task in tasks:
                task_success = self._process_single_task(
                    task, 
                    mission_results, 
                    game_content, 
                    format_type
                )
                success &= task_success
                if task_success:
                    ordered_task_names.append(task.name)
                    
            # If we have multiple successful tasks, generate difference report
            if len(ordered_task_names) >= 2:
                self._generate_difference_report(ordered_task_names, format_type)
                
            return success
            
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return False

    def _process_single_task(self, 
                           task: ScanTask,
                           mission_results: Dict[Path, ScanResult],
                           game_content: ContentScanResult,
                           format_type: str) -> bool:
        """Process a single task completely."""
        try:
            logger.info(f"Processing task: {task.name}")
            
            # Scan task content
            task_content = self.content_scanner.scan_content(task, is_mod_folder=True)
            if not task_content:
                logger.error(f"Failed to scan task: {task.name}")
                return False
            
            # Validate task and generate report
            validation_result = self.task_validator.validate_task(
                task.name,
                mission_results,
                game_content,
                task_content,
                format_type
            )
            
            if not validation_result:
                logger.error(f"Failed to validate task: {task.name}")
                return False
                
            # Store validation results from TaskValidationResult object
            self.task_results[task.name] = validation_result.validation_results
            return True
            
        except Exception as e:
            logger.error(f"Failed to process task {task.name}: {e}")
            return False

    def _generate_difference_report(self, task_names: List[str], format_type: str) -> None:
        """Generate difference report between tasks."""
        try:
            differ = ResultDiffer()
            base_results = self.task_results[task_names[0]]
            
            for compare_task_name in task_names[1:]:
                compare_results = self.task_results[compare_task_name]
                diff_results = differ.difference_results(base_results, compare_results)
                
                # Generate difference report
                report_name = f"diff_{task_names[0]}_{compare_task_name}"
                self.task_validator.report_writer.write_report(
                    report_name,
                    diff_results,
                    format_type
                )
                
                logger.info(f"Generated difference report between {task_names[0]} and {compare_task_name}")
                
        except Exception as e:
            logger.error(f"Failed to generate difference report: {e}")

def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    log_file = Path("dependency_scanner.log")
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Starting dependency scanner")
    logger.info(f"Log file: {log_file.absolute()}")
    
    try:
        paths, tasks, missions = load_config(args.config, args)
        game_path = Path(paths.get("game", "")).resolve()
        if not game_path or not missions or not tasks:
            logger.error("Missing required paths")
            return 1

        cache_dir = Path(args.cache or paths.get("cache", ".cache")).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        with Scanner(cache_dir, game_path, args.workers) as scanner:
            success = scanner.execute_scan(tasks, missions, args.format)
            return 0 if success else 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
