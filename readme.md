# Mission Dependency Scanner

A tool for validating Arma 3 mission dependencies by building comprehensive databases of mod assets and classes, then scanning missions to ensure all referenced content exists.

## Project Goals
- Create a complete asset inventory from mod folders
- Build class databases from config files
- Validate mission dependencies against these databases
- Identify missing or invalid references
- Help mission makers ensure compatibility

## Workflow
1. Scans mod folders to catalog all available assets
2. Parses config files to build class hierarchies
3. Analyzes mission files for references
4. Cross-references mission content against databases
5. Reports missing dependencies

## Features
- Builds asset database from mod folders
- Builds class database from config files  
- Scans missions for asset and class references
- Validates all dependencies exist
- Reports missing or invalid references

## Requirements
- Python 3.8+
- extractpbo in PATH

## Installation

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```python
from mission_dependency_scanner import DependencyScanner
from pathlib import Path

# Initialize scanner
scanner = DependencyScanner(Path("cache"))

# Build mod database
scanner.build_asset_database([
    Path("@CBA_A3"),
    Path("@ace"),
    Path("@task_force_radio")
])

# Build class database
scanner.build_class_database([
    Path("@CBA_A3/config.cpp"),
    Path("@ace/config.cpp"),
    Path("@task_force_radio/config.cpp")
])

# Validate mission
result = scanner.validate_mission(Path("my_mission.Stratis"))

# Review results
print("\nMissing Assets:")
for asset in result.missing_assets:
    print(f"- {asset}")

print("\nMissing Classes:")
for class_name in result.missing_classes:
    print(f"- {class_name}")

print("\nStatistics:")
print(f"Valid Assets: {len(result.valid_assets)}")
print(f"Valid Classes: {len(result.valid_classes)}")
print(f"Total Missing: {len(result.missing_assets) + len(result.missing_classes)}")
```

## Command Line Usage

```bash
# Basic usage
scan-mission path/to/mission @CBA_A3 @ace @task_force_radio

# Specify cache directory
scan-mission --cache ./cache path/to/mission @CBA_A3 @ace

# Process multiple mods
scan-mission path/to/mission @mod1 @mod2 @mod3
```

The scanner will:
1. Process each mod folder for assets and classes
2. Validate the mission against the collected data
3. Display a summary of findings
4. List any missing dependencies

## Configuration

Create `scanner_config.json` in your working directory:

```json
{
    "paths": {
        "game": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Arma 3",
        "mods": "D:\\pca\\pcanext",
        "missions": "D:\\pca\\pca_missions",
        "cache": "cache"
    }
}
```

Override config paths using command line arguments:

```bash
# Use config paths
scan-mission

# Override mission path
scan-mission --mission "path/to/specific/mission"

# Add additional mod paths
scan-mission --mods "@extra_mod1" "@extra_mod2"

# Use different config file
scan-mission --config "other_config.json"
```

## Output Example
```
Missing Assets:
- @ace\addons\medical\data\missing_texture.paa
- @tfar\sounds\missing_radio.wss

Missing Classes:
- ACE_MedicalSupplies
- TFAR_anprc152

Statistics:
Valid Assets: 1420
Valid Classes: 856
Total Missing: 4
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/test_scanner.py
```

### Test Structure
- `conftest.py`: Common test fixtures
- `test_config.py`: Configuration handling tests
- `test_scanner.py`: Core functionality tests
- `test_cli.py`: Command line interface tests