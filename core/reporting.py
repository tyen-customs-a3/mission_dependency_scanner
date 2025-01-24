import json
import logging
from pathlib import Path
from typing import List, Tuple
from .types import ValidationResult

logger = logging.getLogger(__name__)

def format_results(results: ValidationResult, format_type: str) -> str:
    """Format validation results."""
    if format_type == "json":
        return json.dumps({
            "valid_assets": list(results.valid_assets),
            "valid_classes": list(results.valid_classes),
            "missing_assets": list(results.missing_assets),
            "missing_classes": list(results.missing_classes),
            "statistics": {
                "valid_assets": len(results.valid_assets),
                "valid_classes": len(results.valid_classes),
                "missing_assets": len(results.missing_assets),
                "missing_classes": len(results.missing_classes)
            }
        }, indent=2)
    
    lines = []
    lines.append("\nResults Summary:")
    lines.append(f"Valid Assets: {len(results.valid_assets)}")
    lines.append(f"Valid Classes: {len(results.valid_classes)}")
    lines.append(f"Missing Assets: {len(results.missing_assets)}")
    lines.append(f"Missing Classes: {len(results.missing_classes)}")
    
    if results.missing_assets:
        lines.append("\nMissing Assets:")
        for asset in sorted(results.missing_assets):
            lines.append(f"  - {asset}")
    
    if results.missing_classes:
        lines.append("\nMissing Classes:")
        for class_name in sorted(results.missing_classes):
            lines.append(f"  - {class_name}")
    
    return "\n".join(lines)

def format_mission_results(mission_name: str, results: ValidationResult, format_type: str) -> str:
    """Format validation results for a single mission."""
    if format_type == "json":
        return json.dumps({
            "mission": mission_name,
            "valid_assets": list(results.valid_assets),
            "valid_classes": list(results.valid_classes),
            "missing_assets": list(results.missing_assets),
            "missing_classes": list(results.missing_classes),
            "statistics": {
                "valid_assets": len(results.valid_assets),
                "valid_classes": len(results.valid_classes),
                "missing_assets": len(results.missing_assets),
                "missing_classes": len(results.missing_classes)
            }
        }, indent=2)
    
    lines = []
    lines.append(f"\n=== Mission: {mission_name} ===")
    
    if results.missing_classes:
        lines.append("Missing Classes:")
        for class_name in sorted(results.missing_classes):
            lines.append(f"  - {class_name}")
    else:
        lines.append("No missing classes")

    return "\n".join(lines)

def write_overall_report(report_dir: Path, all_results: List[Tuple[str, ValidationResult]], 
                        format_type: str) -> Path:
    """Generate and write the overall report."""
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Writing report to directory: {report_dir}")

        if format_type == "json":
            all_missing_assets = set()
            all_missing_classes = set()
            for _, result in all_results:
                all_missing_assets.update(result.missing_assets)
                all_missing_classes.update(result.missing_classes)
            
            report_file = report_dir / f"scan_report.json"
            logger.debug(f"Writing report to: {report_file}")
            
            report_data = {
                "summary": {
                    "total_missing_assets": len(all_missing_assets),
                    "total_missing_classes": len(all_missing_classes),
                    "all_missing_assets": sorted(list(all_missing_assets)),
                    "all_missing_classes": sorted(list(all_missing_classes))
                },
                "missions": [
                    {
                        "name": name,
                        "results": {
                            "missing_assets": sorted(list(result.missing_assets)),
                            "missing_classes": sorted(list(result.missing_classes)),
                            "valid_assets": sorted(list(result.valid_assets)),
                            "valid_classes": sorted(list(result.valid_classes))
                        }
                    }
                    for name, result in all_results
                ]
            }
            report_file.write_text(json.dumps(report_data, indent=2), encoding='utf-8')
        else:
            lines = []
            lines.append("===== MISSION DEPENDENCY REPORT =====\n")
            
            for mission_name, result in all_results:
                if result.missing_classes:
                    lines.append(format_mission_results(mission_name, result, format_type))
            
            all_missing_classes = set()
            total_valid_classes = 0
            for _, result in all_results:
                all_missing_classes.update(result.missing_classes)
                total_valid_classes += len(result.valid_classes)
            
            lines.append("\n===== SUMMARY =====")
            lines.append(f"Total Missing Classes: {len(all_missing_classes)}")
            lines.append(f"Total Valid Classes: {total_valid_classes}")
            
            if all_missing_classes:
                lines.append("\nAll Missing Classes (across all missions):")
                for class_name in sorted(all_missing_classes):
                    lines.append(f"  - {class_name}")
            
            report_file = report_dir / f"scan_report.txt"
            report_file.write_text("\n".join(lines), encoding='utf-8')
        
        logger.info(f"Report written successfully to {report_file}")
        return report_file

    except Exception as e:
        logger.error(f"Error writing report: {e}", exc_info=True)
        raise
