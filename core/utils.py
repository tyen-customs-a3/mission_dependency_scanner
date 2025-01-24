import sys
import logging
from pathlib import Path
import subprocess
import os

def setup_module_paths():
    """Setup paths for external module dependencies."""
    base_dir = Path(__file__).parent.parent.parent
    module_paths = [
        base_dir / "asset_scanner/src",
        base_dir / "ini_class_parser/src",
        base_dir / "mission_scanner/src"
    ]
    
    for path in module_paths:
        abs_path = path.resolve()
        if abs_path.exists() and str(abs_path) not in sys.path:
            sys.path.insert(0, str(abs_path))

def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('dependency_scanner')

def check_mikero_tools() -> bool:
    """Check if mikero's tools (specifically ExtractPbo) are available in PATH."""
    try:
        subprocess.run(['ExtractPbo', '-P'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def extract_pbo(pbo_path: Path, timeout: int = 30) -> Path:
    """Extract a PBO file using mikero's tools.
    Args:
        pbo_path: Path to PBO file
        timeout: Maximum time in seconds to wait for extraction
    Returns:
        Path to the extracted directory
    """
    if not check_mikero_tools():
        raise RuntimeError("Mikero's tools (ExtractPbo.exe) not found in PATH")
    
    output_dir = pbo_path.with_suffix('')
    
    try:
        result = subprocess.run(
            ['extractpbo', '-P', str(pbo_path)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"PBO extraction failed for {pbo_path.name}: {result.stderr}")
            
        if not output_dir.exists():
            raise RuntimeError(f"Output directory not created after extraction: {output_dir}")
            
        return output_dir
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"PBO extraction timed out after {timeout}s: {pbo_path.name}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract PBO {pbo_path.name}: {str(e)}")
