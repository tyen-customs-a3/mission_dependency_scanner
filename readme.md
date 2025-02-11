# Mission Dependency Scanner

A tool for validating Arma 3 mission dependencies against multiple modsets with configurable class definitions.

## Features
- Extracts and processes PBO files automatically
- Scans base game assets (optional)
- Supports multiple modset configurations
- Case-insensitive class validation
- Configurable class definitions per modset
- JSON or text report formats
- Progress tracking with rich console output
- Asset scan caching for improved performance

## Requirements
- Python 3.8+
- Mikero's Tools (specifically ExtractPbo.exe in PATH)
- Required modules (must be in parent directory):
  - [asset_scanner](https://github.com/tyen-customs-a3/asset_scanner)
  - [class_parser](https://github.com/tyen-customs-a3/class_scanner)
  - [mission_scanner](https://github.com/tyen-customs-a3/mission_scanner)

## Configuration

Create a `config.json` file:

```json
{
    "paths": {
        "game": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Arma 3",
        "cache": "cache",
        "missions": [
            "path/to/mission1.pbo",
            "path/to/mission_folder"
        ]
    },
    "tasks": [
        {
            "name": "vanilla",
            "mods": [],
        },
        {
            "name": "cba_ace",
            "mods": [
                "@CBA_A3",
                "@ace"
            ],
        }
    ]
}
```

## Usage

```bash
# Using config file
python -m dependency_scanner --config config.json

# Override mission path
python -m dependency_scanner --config config.json --mission path/to/mission.pbo

# Specify output format
python -m dependency_scanner --config config.json --format json

# Override cache location
python -m dependency_scanner --config config.json --cache path/to/cache
```

## Workflow

1. Base Game Processing (if required)
   - Scans base game assets
   - Creates cached asset database

2. Mission Preprocessing
   - Extracts PBO files if needed
   - Uses existing extracted folders when available
   - Handles both individual PBOs and directories

3. Mission Scanning
   - Processes all mission files
   - Extracts equipment references
   - Collects class definitions

4. Per-Task Validation
   - Each task runs independently
   - Fresh mod scanning per task
   - Separate class definitions
   - Individual report generation

5. Report Generation
   - Lists missing dependencies
   - Shows validation statistics
   - Supports JSON or text format

## Report Example

```text
===== MISSION DEPENDENCY REPORT =====

=== Mission: example.Stratis ===
Missing Classes:
  - ACE_MedicalSupplies_Advanced
  - TFAR_anprc152

=== Mission: training.Malden ===
No missing classes

===== SUMMARY =====
Total Missing Classes: 2
Total Valid Classes: 856

All Missing Classes (across all missions):
  - ACE_MedicalSupplies_Advanced
  - TFAR_anprc152
```

## Development

To set up a development environment:

```bash
# Create virtual environment
python -m venv venv

# Activate environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```