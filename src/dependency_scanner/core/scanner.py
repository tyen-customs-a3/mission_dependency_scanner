from pathlib import Path
from typing import Dict, List
import logging

from dependency_scanner.core.types import ScanTask, ValidationResult, ScanResult
from dependency_scanner.core.scanning.mission_handler import MissionHandler
from dependency_scanner.core.scanning.gamedata_handler import GameDataHandler
from dependency_scanner.core.validation.validator import DependencyValidator

logger = logging.getLogger(__name__)

class DependencyScanner:
    """Coordinates scanning and validation of mission dependencies."""
    
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self.mission_handler = MissionHandler(max_workers)
        self.mod_handler = GameDataHandler()
        self.validator = None
        self.game_classes = {}  # Cache for game classes
        self.game_data = {}  # Store game content
        self.mission_results = {}  # Store mission scan results
        self.cache_dir = None
    
    def close(self):
        """Cleanup all resources."""
        if self.mod_handler:
            self.mod_handler.close()
        if self.mission_handler:
            self.mission_handler.close()
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when used as context manager."""
        self.close()
    
    def initialize_apis(self, cache_dir: Path):
        """Initialize necessary APIs."""
        self.cache_dir = cache_dir
        # Change cache location to be under the main cache directory
        reports_cache = cache_dir / "gamedata"
        reports_cache.mkdir(parents=True, exist_ok=True)
        
        self.mod_handler.initialize(reports_cache)
        self.validator = DependencyValidator(
            self.mod_handler.asset_api,
            self.max_workers
        )
    
    def scan_base_content(self, game_path: Path):
        """Scan base game content first."""
        if not game_path or not game_path.exists():
            raise RuntimeError(f"Invalid game path: {game_path}")
            
        logger.info(f"Starting base game content scan from: {game_path}")
        self.game_data = self.mod_handler.scan_mod_content([game_path])
        
        if not self.game_data:
            raise RuntimeError("Failed to scan game content!")
            
        logger.info(f"Base game scan complete - Found {len(self.game_data)} classes")
        
        # Verify we have some basic game content
        if len(self.game_data) < 1000:  # Arma 3 has thousands of classes
            logger.warning("Unusually small number of game classes found - scan may be incomplete")
    
    def scan_missions(self, missions: List[Path]):
        """Scan all missions once."""
        logger.info("Scanning missions...")
        valid_missions = self._validate_mission_paths(missions)
        if not valid_missions:
            raise RuntimeError("No valid mission paths found")
            
        self.mission_results = self.mission_handler.scan_missions(valid_missions)
        logger.info(f"Mission scan complete - Processed {len(self.mission_results)} missions")
    
    def execute_task(self, task: ScanTask, format_type: str = "text") -> Path:
        """Execute mod-specific scanning and validation."""
        if not self.game_data:
            raise RuntimeError("Base game content not scanned. Call scan_base_content() first")
        if not self.mission_results:
            raise RuntimeError("Missions not scanned. Call scan_missions() first")
        
        # Scan mod content for this task
        logger.info(f"Scanning mod content for task: {task.name}")
        mod_data = self.mod_handler.scan_mod_content(task.mods)
        
        # Combine game and mod data
        combined_data = {**self.game_data, **mod_data}
        logger.info(f"Combined {len(mod_data)} mod classes with {len(self.game_data)} game classes")
        
        # Validate dependencies
        logger.info("Validating mission dependencies...")
        validation_results = self.validator.validate_missions(
            self.mission_results, 
            combined_data
        )
        
        return self._generate_report(task.name, validation_results, format_type)
    
    def _validate_mission_paths(self, missions: List[Path]) -> List[Path]:
        """Validate and normalize mission paths."""
        valid_missions = []
        for mission in missions:
            if not mission.exists():
                logger.warning(f"Mission path does not exist: {mission}")
                continue
            mission_path = mission.resolve()
            valid_missions.append(mission_path)
            logger.info(f"Added mission path: {mission_path}")
        return valid_missions

    def _generate_report(self, task_name: str, 
                        validation_results: Dict[Path, ValidationResult],
                        format_type: str) -> Path:
        """Generate the final report."""
        from .reporting import write_overall_report
        
        report_dir = Path.cwd() / "reports" / task_name
        report_dir.mkdir(parents=True, exist_ok=True)
        
        formatted_results = [
            (str(name), result) 
            for name, result in validation_results.items() 
            if result
        ]
        
        return write_overall_report(report_dir, formatted_results, format_type)
