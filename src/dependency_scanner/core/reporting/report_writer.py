from pathlib import Path
from typing import Dict, Optional
import logging
import json
from datetime import datetime

from dependency_scanner.core.types import ValidationResult

logger = logging.getLogger(__name__)

class ReportWriter:
    """Handles generation and writing of validation reports."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def write_report(self, 
                    task_name: str,
                    validation_results: Dict[Path, ValidationResult],
                    format_type: str = "text") -> Optional[Path]:
        """Generate and write validation report."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.output_dir / f"report_{task_name}_{timestamp}.{format_type}"
            
            if format_type == "text":
                self._write_text_report(report_path, validation_results)
            else:
                self._write_json_report(report_path, validation_results)
                
            logger.info(f"Report written to: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Failed to write report: {e}")
            return None
            
    def _write_text_report(self, path: Path, results: Dict[Path, ValidationResult]) -> None:
        """Write results in text format using category-based view."""
        with path.open('w', encoding='utf-8') as f:
            f.write("=== Mission Dependency Report ===\n\n")
            
            non_compliant = []
            compliant = []
            
            for mission_path, result in results.items():
                if result.missing_classes or result.missing_assets:
                    non_compliant.append((mission_path, result))
                else:
                    compliant.append(mission_path)
            
            if non_compliant:
                f.write("[!] MISSIONS WITH MISSING DEPENDENCIES\n")
                f.write("-" * 50 + "\n\n")
                for mission_path, result in non_compliant:
                    f.write(f"{mission_path.name}\n")
                    
                    if result.missing_classes:
                        f.write("  Missing Classes:\n")
                        for cls in sorted(result.missing_classes):
                            f.write(f"  └─ {cls}\n")
                            
                    if result.missing_assets:
                        f.write("  Missing Assets:\n")
                        for asset in sorted(result.missing_assets):
                            f.write(f"  └─ {asset}\n")
                    f.write("\n")
            
            f.write(f"\n[+] COMPLIANT MISSIONS ({len(compliant)})\n")
            f.write("-" * 50 + "\n")
            for mission_path in sorted(compliant):
                f.write(f"{mission_path.name}\n")
            
            total = len(results)
            f.write("\n")
            f.write("[*] SUMMARY")
            f.write("\n")
            f.write("-" * 9 + "\n")
            f.write(f"Total Missions: {total}\n")
            f.write(f"Compliant: {len(compliant)}\n")
            f.write(f"Non-compliant: {len(non_compliant)}\n")
            f.write(f"Pass Rate: {(len(compliant)/total)*100:.1f}%\n")
            f.write(f"Last Validated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    def _write_json_report(self, path: Path, results: Dict[Path, ValidationResult]) -> None:
        """Write results in JSON format."""
        json_data = {
            str(mission_path): {
                "valid_classes": list(result.valid_classes),
                "valid_assets": list(result.valid_assets),
                "missing_classes": list(result.missing_classes),
                "missing_assets": list(result.missing_assets),
                "property_results": result.property_results
            }
            for mission_path, result in results.items()
        }
        
        path.write_text(json.dumps(json_data, indent=2))
