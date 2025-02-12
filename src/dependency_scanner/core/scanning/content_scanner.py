from pathlib import Path
from typing import Dict, Optional
import logging
from dataclasses import dataclass

from class_scanner.models import ClassData
from asset_scanner import Asset
from dependency_scanner.core.types import ScanTask
from dependency_scanner.core.scanning.gamedata_handler import GameDataHandler

logger = logging.getLogger(__name__)

@dataclass
class ContentScanResult:
    """Results from scanning game or mod content."""
    classes: Dict[str, ClassData]
    assets: Dict[str, Asset]

class ContentScanner:
    """Handles scanning of game and mod content."""
    
    def __init__(self, cache_dir: Path, max_workers: int = 16):
        self.cache_dir = cache_dir
        self.max_workers = max_workers
        self._handler: Optional[GameDataHandler] = None
        
    def scan_content(self, task: ScanTask) -> Optional[ContentScanResult]:
        """Scan content for a given task."""
        try:
            # Create fresh handler for each scan operation
            self._handler = GameDataHandler(
                self.cache_dir / task.name,
                self.max_workers
            )
            
            content = self._handler.scan_mod_content(task.mods)
            if not content:
                return None
                
            return ContentScanResult(
                classes=content.get('classes', {}),
                assets=content.get('assets', {})
            )
            
        except Exception as e:
            logger.error(f"Failed to scan content for task {task.name}: {e}")
            return None
            
    def close(self) -> None:
        """Cleanup resources."""
        if self._handler:
            self._handler.close()
            self._handler = None
