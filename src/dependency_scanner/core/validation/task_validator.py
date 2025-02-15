from pathlib import Path
from typing import Dict, Optional
import logging

from mission_scanner import ScanResult

from dependency_scanner.core.analysis.suggestion_generator import SuggestionGenerator
from dependency_scanner.core.reporting.report_writer import ReportWriter
from dependency_scanner.core.scanning.content_scanner import ContentScanResult
from dependency_scanner.core.types import ValidationResult
from dependency_scanner.core.validation.validator import DependencyValidator
from dependency_scanner.core.analysis.class_analyzer import ClassAnalyzer

logger = logging.getLogger(__name__)

class TaskValidationResult:
    """Result of task validation including report path."""
    def __init__(self, validation_results: Dict[Path, ValidationResult], report_path: Optional[Path] = None):
        self.validation_results = validation_results
        self.report_path = report_path

class TaskValidator:
    """Validates task content and generates reports."""
    
    def __init__(self, max_workers: int, reports_dir: Path):
        self.max_workers = max_workers
        self.reports_dir = reports_dir  # Make reports_dir accessible
        self.validator = DependencyValidator(max_workers)
        self.report_writer = ReportWriter(reports_dir)
        self.class_analyzer = ClassAnalyzer()
        self.validation_results: Dict[str, Dict[Path, ValidationResult]] = {}
        self.suggestion_generator = SuggestionGenerator()
        
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

            # Store results for potential later comparison
            self.validation_results[task_name] = validation_results
            
            # Analyze classes and write summary
            class_sets = self.class_analyzer.analyze_results(validation_results)
            summary_path = self.reports_dir / f"class_summary_{task_name}.txt"
            self.class_analyzer.write_class_summary(summary_path, class_sets)

            # Generate regular report
            report_path = self.report_writer.write_report(
                task_name,
                validation_results,
                format_type
            )
            
            # After report is written, generate suggestions
            all_missing_classes = set()
            for result in validation_results.values():
                all_missing_classes.update(result.missing_classes)
            
            if all_missing_classes:
                available_classes = set(game_content.classes.keys())
                available_classes.update(task_content.classes.keys())
                
                suggestions = self.suggestion_generator.generate_suggestions(
                    all_missing_classes,
                    available_classes
                )
                
                # Write suggestions to separate report
                self.suggestion_generator.write_suggestion_report(
                    self.reports_dir,
                    task_name,
                    suggestions
                )
            
            return TaskValidationResult(validation_results, report_path)
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            return None
