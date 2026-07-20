from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from logger import logger

console = Console()

def show_banner() -> None:
    #Displays the application banner.
    banner = r"""
    [bold cyan]
     __      __    _ _                         
     \ \    / /_ _| | | __ _  ___ __ _ _ __    
      \ \/\/ / _` | | |/ _` |/ __/ _` | '__|   
       \_/\_/\__,_|_|_|\__,_|\___\__,_|_|      
    [/bold cyan]
           [italic yellow]By IsraelGarciaDev[/italic yellow]
    """
    console.print(banner)

def show_extraction_stats(marca: str, total: int, nuevas: int, bajadas: int) -> None:
    #Muestra un resumen compacto y elegante del escaneo.
    panel = Panel(
        f"[bold white]Coches procesados:[/bold white] [cyan]{total}[/cyan]\n"
        f"[bold green]Nuevas joyas:[/bold green] [green]{nuevas}[/green]\n"
        f"[bold yellow]Bajadas detectadas:[/bold yellow] [yellow]{bajadas}[/yellow]",
        title=f"📊 [bold]{marca.upper()}[/bold]",
        border_style="bright_blue",
        expand=False
    )
    console.print(panel)

def show_menu_combustible() -> None:
    #Displays the fuel selection menu.
    panel_content = (
        "[1] [bold]Gasolina[/bold] ⛽  [2] [bold]Diesel[/bold] 🚜\n"
        "[3] [bold]Híbrido[/bold] 🔋   [4] [bold]Eléctrico[/bold] ⚡\n"
        "[0] [bold]Cualquiera[/bold] 🌍"
    )
    console.print(Panel(panel_content, title="⛽ [bold yellow]Combustible[/bold yellow]", border_style="yellow", expand=False))

def log_step(msg: str) -> None:
    #Logs a step to console and file.
    # We use logger for file persistence, but might want to print to console with specific style
    # Logger already has a console handler, so simple logger.info should appear.
    # To keep the "blue arrow" style, we can just print for UI and log info for file.
    console.print(f"[bold blue]❯[/bold blue] {msg}")
    logger.info(msg)

def log_success(msg: str) -> None:
    #Logs a success message.
    console.print(f"[bold green]✔[/bold green] {msg}")
    logger.info(f"SUCCESS: {msg}")

def log_error(msg: str) -> None:
    #Logs an error message.
    console.print(Panel(f"[bold red]❌ ERROR:[/bold red] {msg}", border_style="red"))
    logger.error(msg)

def log_vps_status(msg: str) -> None:
    #Logs a status update (gray/dim).
    console.print(f"[dim gray]⚙️ {msg}[/dim gray]")
    logger.info(f"STATUS: {msg}")
