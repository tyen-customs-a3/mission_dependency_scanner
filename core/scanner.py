from pathlib import Path
from typing import Dict, Tuple, Set, Callable
import logging
from rich.progress import Progress

from .utils import setup_module_paths, setup_logging, extract_pbo
setup_module_paths()

from asset_scanner import AssetAPI
from ini_class_parser import ClassHierarchyAPI
from mission_scanner import MissionScanner, ScanResult
from .types import ScanTask, ValidationResult, IGNORED_CATEGORIES

logger = setup_logging(debug=True)

def needs_asset_scanning(tasks: list[ScanTask]) -> bool:
    """Check if any tasks require asset scanning."""
    return any(not task.skip_assets for task in tasks)

def base_progress_callback(path: str) -> None:
    """Progress callback for base game scanning."""
    logger.debug(f"Scanning: {path}")

def preprocess_missions(missions: list[Path], progress: Progress) -> list[Path]:
    """Preprocess all mission paths and extract PBOs if needed.
    Returns a list of paths to extracted/regular mission folders."""
    all_mission_folders = []
    extraction_task = progress.add_task("[yellow]Preprocessing missions...", total=len(missions))

    for mission_base in missions:
        try:
            progress.update(extraction_task, description=f"[yellow]Checking: {mission_base.name}")
            
            if not mission_base.exists():
                logger.warning(f"Mission base path not found: {mission_base}")
                progress.console.print(f"[yellow]Warning: Mission base path not found: {mission_base}")
                continue

            # Handle both directories and PBO files
            if mission_base.is_file() and mission_base.suffix.lower() == '.pbo':
                # Check for existing extracted folder
                extracted_dir = mission_base.with_suffix('')
                if extracted_dir.exists():
                    # logger.debug(f"Using existing extracted folder: {extracted_dir}")
                    all_mission_folders.append(extracted_dir)
                else:
                    # Extract PBO only if folder doesn't exist
                    try:
                        progress.console.print(f"[yellow]Extracting: {mission_base.name}")
                        extracted_dir = extract_pbo(mission_base)
                        progress.console.print(f"[green]Successfully extracted: {mission_base.name}")
                        all_mission_folders.append(extracted_dir)
                    except Exception as e:
                        logger.error(f"Failed to extract PBO {mission_base}: {e}")
                        progress.console.print(f"[red]Failed to extract PBO {mission_base}: {e}")
            
            elif mission_base.is_dir():
                # Check for PBOs in directory
                pbo_files = list(mission_base.glob('*.pbo'))
                if pbo_files:
                    # Process all PBOs in directory
                    for pbo_file in pbo_files:
                        extracted_dir = pbo_file.with_suffix('')
                        if extracted_dir.exists():
                            logger.debug(f"Using existing extracted folder: {extracted_dir}")
                            all_mission_folders.append(extracted_dir)
                        else:
                            # Extract PBO only if folder doesn't exist
                            try:
                                progress.console.print(f"[yellow]Extracting: {pbo_file.name}")
                                extracted_dir = extract_pbo(pbo_file)
                                progress.console.print(f"[green]Successfully extracted: {pbo_file.name}")
                                all_mission_folders.append(extracted_dir)
                            except Exception as e:
                                logger.error(f"Failed to extract PBO {pbo_file}: {e}")
                                progress.console.print(f"[red]Failed to extract PBO {pbo_file}: {e}")
                else:
                    # Regular mission folder
                    all_mission_folders.append(mission_base)
                    
        except Exception as e:
            logger.error(f"Error processing mission path {mission_base}: {e}")
            progress.console.print(f"[red]Error processing mission path {mission_base}: {e}")
        finally:
            progress.advance(extraction_task)

    # Log preprocessing results
    total_missions = len(all_mission_folders)
    logger.info(f"Mission preprocessing complete - Found {total_missions} valid mission folders")
    progress.console.print(f"[green]Mission preprocessing complete - Found {total_missions} valid mission folders")
    
    return all_mission_folders

def scan_base_data(game_path: Path, cache_dir: Path, missions: list[Path],
                  progress: Progress, require_assets: bool = True) -> tuple[AssetAPI, dict[Path, ScanResult]]:
    """Scan base game data and missions once."""
    logger.debug(f"Starting base data scan - Game: {game_path}, Cache: {cache_dir}, Require assets: {require_assets}")
    
    # Initialize base asset scanner
    base_cache = cache_dir / "base_assets"
    base_api = None
    scanned_files = 0
    
    if require_assets:
        base_cache.mkdir(parents=True, exist_ok=True)
        base_api = AssetAPI(base_cache)
        
        try:
            # Scan base game assets
            if game_path.exists():
                logger.debug(f"Base game path found at {game_path}")
                progress.console.print(f"[cyan]Starting base game scan from {game_path}")
                base_task = progress.add_task("[cyan]Scanning base game assets...", total=1)
                base_api.add_folder("Arma3", game_path)
                base_api._scanner.progress_callback = base_progress_callback
                scanned_files = base_api.scan_all_folders()
                progress.console.print(f"[green]Base game scan complete - processed {scanned_files} files")
                progress.update(base_task, completed=True)
                logger.debug(f"Base scan complete - {scanned_files} files processed")
            else:
                logger.warning(f"Game path not found: {game_path}")
                progress.console.print("[yellow]Warning: Game path not found, skipping base game scan")
        except Exception as e:
            logger.error(f"Error scanning base game: {e}")
            progress.console.print(f"[red]Error scanning base game: {e}")
            base_api = AssetAPI(base_cache)  # Fallback to empty API
    else:
        logger.info("Skipping base game asset scan - no tasks require assets")
        progress.console.print("[blue]Skipping base game asset scan - not required by any tasks")
        base_api = AssetAPI(base_cache)  # Empty API for consistency

    # Preprocess all missions first
    progress.console.print("\n[bold blue]Starting mission preprocessing")
    all_mission_folders = preprocess_missions(missions, progress)
    
    # Scan all missions
    mission_results = {}
    total_classes = 0
    total_equipment = 0
    mission_scanner = MissionScanner()
    
    # Create mission scanning task
    mission_task = progress.add_task("[cyan]Scanning missions...", total=len(all_mission_folders))
    
    for mission_dir in all_mission_folders:
        try:
            mission_name = mission_dir.name
            logger.debug(f"Starting scan of mission: {mission_name}")
            progress.update(mission_task, description=f"[cyan]Scanning mission: {mission_name}")

            # Scan mission directory
            result = mission_scanner.scan_directory(mission_dir)
            if not result:
                logger.warning(f"No results returned for mission: {mission_name}")
                continue
                
            # Note: MissionScanner only returns classes and equipment
            # logger.debug(f"Scan complete for {mission_name}: {len(result.classes)} classes, {len(result.equipment)} equipment")
            mission_results[mission_dir] = result
            
            # Log mission statistics
            total_classes += len(result.classes)
            total_equipment += len(result.equipment)
            # progress.console.print(f"[cyan]Mission {mission_name}: {len(result.classes)} classes, {len(result.equipment)} equipment entries")
            
        except Exception as e:
            logger.error(f"Failed to scan mission {mission_dir}: {e}", exc_info=True)
            # progress.console.print(f"[red]Error scanning mission {mission_dir}: {e}")
        finally:
            progress.advance(mission_task)

    logger.info(f"Mission scanning complete - Found {len(all_mission_folders)} missions with {total_classes} total classes and {total_equipment} equipment entries")
    # progress.console.print(f"[green]Mission scanning complete - Found {len(all_mission_folders)} missions with {total_classes} total classes and {total_equipment} equipment entries")
    
    return base_api, mission_results

def validate_mission(scan_result: ScanResult, mod_api: AssetAPI, classes: Dict[str, Set[str]]) -> ValidationResult:
    """Validate a single mission against class definitions."""
    valid_assets = set()
    missing_assets = set()
    valid_classes = set()
    missing_classes = set()
    property_results = {}
    
    # Convert class lists to lowercase for case-insensitive comparison
    lowercase_classes = {
        category: {class_name.lower() for class_name in class_set}
        for category, class_set in classes.items()
    }
    
    # # Validate all directly referenced classes first
    # for class_name in scan_result.classes:
    #     if not class_name:  # Skip empty/None values
    #         continue
    #     class_name_str = str(class_name).strip()  # Convert to string and clean
    #     if not class_name_str:  # Skip empty strings
    #         continue
            
    #     class_name_lower = class_name_str.lower()
    #     found = False
    #     for category, category_classes in lowercase_classes.items():
    #         if category in IGNORED_CATEGORIES:
    #             continue
    #         if class_name_lower in category_classes:
    #             valid_classes.add(class_name_str)
    #             found = True
    #             break
    #     if not found:
    #         missing_classes.add(class_name_str)

    # Then validate all equipment references
    for equipment in scan_result.equipment:
        if not equipment:  # Skip empty/None values
            continue
        equipment_str = str(equipment).strip()  # Convert to string and clean
        if not equipment_str:  # Skip empty strings
            continue
            
        equipment_lower = equipment_str.lower()
        found = False
        for category, category_classes in lowercase_classes.items():
            if category in IGNORED_CATEGORIES:
                continue
            if equipment_lower in category_classes:
                valid_classes.add(equipment_str)
                found = True
                break
        if not found:
            missing_classes.add(equipment_str)
    
    return ValidationResult(
        valid_assets=valid_assets,
        valid_classes=valid_classes,
        missing_assets=missing_assets,
        missing_classes=missing_classes,
        property_results=property_results
    )

def scan_task(task: ScanTask, game_path: Path, cache_dir: Path,
              base_api: AssetAPI, mission_results: Dict[Path, ScanResult],
              progress: Progress, format_type: str) -> Path:
    """Execute a single scanning task using pre-scanned base data"""
    progress.console.print(f"\n[bold blue]Starting task {task.name}")
    progress.console.print(f"[blue]Processing {len(task.mods)} mods and {len(mission_results)} missions")
    logger.debug(f"Task settings - skip_assets: {task.skip_assets}")

    # Initialize mod-specific asset API if needed
    mod_api = None
    if not task.skip_assets:
        mod_cache = cache_dir / "mod_assets" / task.name
        mod_cache.mkdir(parents=True, exist_ok=True)
        mod_api = AssetAPI(mod_cache)

        # Copy base assets to mod API
        asset_count = mod_api.merge_assets(base_api)
        progress.console.print(f"[blue]Merged {asset_count} base assets")

    # Status tracking
    phases = 1 if task.skip_assets else 2
    status_task = progress.add_task(f"[bold blue]{task.name} Status", total=phases)

    # Scan mod folders if not skipping assets
    if not task.skip_assets:
        progress.update(status_task, description="[bold blue]Phase 1: Mod Asset Scanning")
        mod_task = progress.add_task("[cyan]Scanning mod assets...", total=len(task.mods))
        for mod_path in task.mods:
            progress.update(mod_task, description=f"[cyan]Scanning mod: {mod_path.name}")
            mod_api.add_folder(mod_path.name.strip('@'), mod_path)
            mod_api.scan_all_folders()
            progress.advance(mod_task)
        progress.update(status_task, advance=1)

    # Process class definitions
    progress.update(status_task, description="[bold blue]Phase 2: Class Processing")
    class_api = ClassHierarchyAPI(task.class_config)
    
    class_task = progress.add_task("[cyan]Processing class definitions...", total=1)
    progress.update(class_task, description=f"[cyan]Parsing: {task.class_config}")
    
    # Process all categories
    classes = {}
    for category in class_api.get_available_categories():
        category_classes = class_api.get_all_classes(category)
        classes[category] = set(category_classes.keys())

    total_classes = sum(len(c) for c in classes.values())
    progress.console.print(f"[bold green]Total classes found: {total_classes}[/bold green]")
    
    progress.update(class_task, completed=True)
    progress.update(status_task, advance=1)

    # Validate missions
    all_results = []
    total_missing = 0
    mission_validate_task = progress.add_task("[cyan]Validating missions...", total=len(mission_results))
    
    for mission_path, scan_result in mission_results.items():
        progress.update(mission_validate_task, description=f"[cyan]Validating: {mission_path.name}")
        if task.skip_assets:
            # Create empty API if skipping assets
            result = validate_mission(scan_result, AssetAPI(cache_dir), classes)
        else:
            result = validate_mission(scan_result, mod_api, classes)
        all_results.append((mission_path.name, result))
        
        # Log validation results
        missing = len(result.missing_assets) + len(result.missing_classes)
        total_missing += missing
        if missing > 0:
            progress.console.print(f"[yellow]Found {missing} missing dependencies in {mission_path.name}")
        progress.advance(mission_validate_task)

    progress.console.print(f"[{'green' if total_missing == 0 else 'yellow'}]Validation complete - {total_missing} total missing dependencies")
    
    # Generate report
    from .reporting import write_overall_report
    report_dir = Path(__file__).parent.parent.parent / "temp_reports" / task.name
    report_dir.mkdir(parents=True, exist_ok=True)
    return write_overall_report(report_dir, all_results, format_type)
