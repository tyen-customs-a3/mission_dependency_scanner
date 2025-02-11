from pathlib import Path
from typing import Dict, Optional
import logging

from dependency_scanner.core.reporting.report_writer import ReportWriter
from dependency_scanner.core.types import ValidationResult, ScanResult
from dependency_scanner.core.scanning.content_scanner import ContentScanResult
from dependency_scanner.core.validation.validator import DependencyValidator

logger = logging.getLogger(__name__)

class TaskValidationResult:
    """Result of task validation including report path."""
    def __init__(self, validation_results: Dict[Path, ValidationResult], report_path: Optional[Path] = None):
        self.validation_results = validation_results
        self.report_path = report_path

class TaskValidator:
    """Validates task content and generates reports."""
    
    def __init__(self, max_workers: int, report_dir: Path):
        self.max_workers = max_workers
        self.validator = DependencyValidator(max_workers)
        self.report_writer = ReportWriter(report_dir)
        
    def validate_task(self,
                     task_name: str,
                     mission_results: Dict[Path, ScanResult],
                     game_content: ContentScanResult,
                     task_content: ContentScanResult,
                     format_type: str = "text") -> Optional[TaskValidationResult]:
        """Validate task and generate report."""
        try:
            validation_results = self.validator.validate_content(
                mission_results=mission_results,
                game_content={
                    'classes': game_content.classes,
                    'assets': game_content.assets
                },
                task_content={
                    'classes': task_content.classes,
                    'assets': task_content.assets
                }
            )
            
            if not validation_results:
                return None
                
            # Generate report
            report_path = self.report_writer.write_report(
                task_name,
                validation_results,
                format_type
            )
            
            return TaskValidationResult(validation_results, report_path)
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            return None
