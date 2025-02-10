import json
import logging
from pathlib import Path
from typing import List, Tuple

from dependency_scanner.core.types import ValidationResult

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
            "mission": {
                "name": mission_name,
                "directory": str(mission_name),
                "world": mission_name.split('.')[-1] if '.' in mission_name else "Unknown"
            },
            "results": {
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
            }
        }, indent=2)
    
    mission_world = mission_name.split('.')[-1] if '.' in mission_name else "Unknown"
    lines = []
    lines.append(f"\n=== Mission: {mission_name} ===")
    lines.append(f"World: {mission_world}")
    lines.append(f"Directory: {mission_name}")
    lines.append(f"\nStatistics:")
    lines.append(f"  Valid Classes: {len(results.valid_classes)}")
    lines.append(f"  Missing Classes: {len(results.missing_classes)}")
    lines.append(f"  Valid Assets: {len(results.valid_assets)}")
    lines.append(f"  Missing Assets: {len(results.missing_assets)}")
    
    if results.missing_classes:
        lines.append("\nMissing Classes:")
        for class_name in sorted(results.missing_classes):
            lines.append(f"  - {class_name}")
    
    if results.missing_assets:
        lines.append("\nMissing Assets:")
        for asset in sorted(results.missing_assets):
            lines.append(f"  - {asset}")

    return "\n".join(lines)

def write_overall_report(report_dir: Path, all_results: List[Tuple[str, ValidationResult]], 
                        format_type: str) -> Path:
    """Generate and write the overall report."""
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Sort results by mission name
        sorted_results = sorted(all_results, key=lambda x: Path(x[0]).name)
        
        if format_type == "json":
            report_file = report_dir / "scan_report.json"
            report_data = {
                "missions": [
                    {
                        "path": name,
                        "name": Path(name).name,
                        "world": Path(name).suffix.lstrip('.'),
                        "results": {
                            "missing_assets": sorted(list(result.missing_assets)),
                            "missing_classes": sorted(list(result.missing_classes)),
                            "valid_assets": sorted(list(result.valid_assets)),
                            "valid_classes": sorted(list(result.valid_classes))
                        }
                    }
                    for name, result in sorted_results
                ],
                "summary": {
                    "total_missions": len(sorted_results),
                    "total_missing_assets": len(set().union(*(r.missing_assets for _, r in sorted_results))),
                    "total_missing_classes": len(set().union(*(r.missing_classes for _, r in sorted_results)))
                }
            }
            report_file.write_text(json.dumps(report_data, indent=2), encoding='utf-8')
        else:
            lines = ["===== MISSION DEPENDENCY REPORT =====\n"]
            
            # Group results by mission
            for mission_path, result in sorted_results:
                mission = Path(mission_path)
                lines.append(f"Mission: {mission.name}")
                lines.append(f"World: {mission.suffix.lstrip('.')}")
                lines.append(f"Path: {mission_path}")
                lines.append(f"\nStatistics:")
                lines.append(f"  Valid Classes: {len(result.valid_classes)}")
                lines.append(f"  Missing Classes: {len(result.missing_classes)}")
                lines.append(f"  Valid Assets: {len(result.valid_assets)}")
                lines.append(f"  Missing Assets: {len(result.missing_assets)}\n")
                
                if result.missing_classes:
                    lines.append("Missing Classes:")
                    for cls in sorted(result.missing_classes):
                        lines.append(f"  - {cls}")
                    lines.append("")
                
                if result.missing_assets:
                    lines.append("Missing Assets:")
                    for asset in sorted(result.missing_assets):
                        lines.append(f"  - {asset}")
                    lines.append("")
                
                lines.append("-" * 80 + "\n")
            
            report_file = report_dir / "scan_report.txt"
            report_file.write_text("\n".join(lines), encoding='utf-8')
        
        logger.info(f"Report written to: {report_file}")
        return report_file
        
    except Exception as e:
        logger.error(f"Error writing report: {e}", exc_info=True)
        raise
