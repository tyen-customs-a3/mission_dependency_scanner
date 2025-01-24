"""Mission dependency scanner for Arma 3."""
import sys
import traceback
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

# Add core module to path and setup external modules
sys.path.insert(0, str(Path(__file__).parent))
from core.utils import setup_module_paths
setup_module_paths()

from core.config import parse_args, load_config
from core.scanner import scan_base_data, scan_task, needs_asset_scanning

console = Console()

def main():
    """Run the dependency scanner workflow."""
    console = Console()
    try:
        args = parse_args()
        try:
            paths, tasks, missions = load_config(args.config, args)
        except Exception as e:
            console.print(f"[bold red]Error loading config:[/bold red] {str(e)}")
            return 1

        if not missions:
            console.print("[bold red]Error:[/bold red] No missions specified")
            return 1
            
        if not tasks:
            console.print("[bold red]Error:[/bold red] No tasks specified")
            return 1

        # Create report directory
        report_base = Path(__file__).parent / "temp_reports"
        report_base.mkdir(exist_ok=True)

        with Progress() as progress:
            try:
                progress.console.print("[bold green]Starting base data scan[/bold green]")
                progress.console.print(f"[bold]Game path:[/bold] {paths['game']}")
                progress.console.print(f"[bold]Number of missions:[/bold] {len(missions)}")
                progress.console.print(f"[bold]Number of tasks:[/bold] {len(tasks)}")
                
                # Check if we need asset scanning
                require_assets = needs_asset_scanning(tasks)
                
                # Scan base data once
                try:
                    base_api, mission_results = scan_base_data(
                        paths["game"],
                        paths["cache"],
                        missions,
                        progress,
                        require_assets=require_assets
                    )
                except Exception as e:
                    console.print(f"[bold red]Error scanning base data:[/bold red] {str(e)}")
                    return 1

                # Process each task
                task_status = progress.add_task("[bold blue]Processing Tasks", total=len(tasks))
                reports = []
                
                for task in tasks:
                    try:
                        progress.console.print(f"\n[bold cyan]Starting task:[/bold cyan] {task.name}")
                        report_file = scan_task(
                            task=task,
                            game_path=paths["game"],
                            cache_dir=paths["cache"],
                            base_api=base_api,
                            mission_results=mission_results,
                            progress=progress,
                            format_type=args.format
                        )
                        reports.append((task.name, report_file))
                    except Exception as e:
                        console.print(f"[bold red]Error in task {task.name}:[/bold red] {str(e)}")
                    finally:
                        progress.advance(task_status)

                # Print summary of all reports
                if reports:
                    progress.console.print("\n[bold green]All tasks completed![/bold green]")
                    for task_name, report_file in reports:
                        progress.console.print(
                            f"[green]Report for {task_name}:[/green] {report_file}"
                        )
                else:
                    console.print("[bold red]No reports generated[/bold red]")
                    return 1

            except Exception as e:
                console.print("[bold red]Error during scan:[/bold red]")
                console.print(traceback.format_exc())
                return 1

    except Exception as e:
        console.print("[bold red]Unhandled error:[/bold red]")
        console.print(traceback.format_exc())
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
