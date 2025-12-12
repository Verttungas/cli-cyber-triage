#!/usr/bin/env python3
"""
Cyber-Triage CLI - Sistema de análisis automatizado de incidentes DLP
"""

import os
from pathlib import Path
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import box
from datetime import datetime
import time

from db_manager import DatabaseManager
from gemini_analyzer import GeminiAnalyzer

console = Console()
EVIDENCE_DIR = Path(os.getenv("EVIDENCE_DIR", "./evidencia_temp"))


def print_header():
    """Imprime header del sistema"""
    console.print("\n[bold cyan]" + "="*80 + "[/bold cyan]")
    console.print("[bold cyan]  🛡️  CYBER-TRIAGE - DLP Incident Analysis System[/bold cyan]")
    console.print("[bold cyan]  Powered by Gemini 2.5 Pro[/bold cyan]")
    console.print("[bold cyan]" + "="*80 + "[/bold cyan]\n")


def initialize_system():
    """Inicializa componentes del sistema"""
    console.print("[bold]🔧 Inicializando sistema...[/bold]\n")
    
    # Database
    try:
        db = DatabaseManager()
        console.print("✅ Database: Conectada")
    except Exception as e:
        console.print(f"❌ Database: Error - {e}")
        return None, None
    
    # Gemini
    try:
        analyzer = GeminiAnalyzer(
            db_manager=db,
            model_name="gemini-2.5-pro"
        )
        console.print("✅ Gemini 2.5 Pro: Inicializado\n")
    except Exception as e:
        console.print(f"❌ Gemini: Error - {e}\n")
        return db, None
    
    return db, analyzer


def download_incidents():
    """Ejecuta descarga de incidentes"""
    console.print(Panel.fit(
        "📥 Descargando incidentes del día (Max 5)...",
        border_style="blue"
    ))
    
    import evidence_downloader
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Descargando...", total=None)
        
        try:
            evidence_downloader.main()
            progress.update(task, completed=True)
            console.print("\n✅ Descarga completada\n")
            return True
        except Exception as e:
            console.print(f"\n❌ Error en descarga: {e}\n")
            return False


def list_incidents():
    """Lista incidentes disponibles"""
    if not EVIDENCE_DIR.exists():
        console.print("[yellow]⚠️  No hay incidentes descargados[/yellow]\n")
        return []
    
    incidents = [d for d in EVIDENCE_DIR.iterdir() if d.is_dir()]
    
    if not incidents:
        console.print("[yellow]⚠️  No hay incidentes descargados[/yellow]\n")
        return []
    
    table = Table(title="📋 Incidentes Disponibles", box=box.ROUNDED)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Incident ID", style="white")
    table.add_column("Archivo", style="green")
    table.add_column("Fecha", style="blue")
    
    for idx, inc_dir in enumerate(incidents, 1):
        # Buscar archivo
        files = [f.name for f in inc_dir.iterdir() if f.name != "metadata.json"]
        file_name = files[0] if files else "[dim]Sin archivo[/dim]"
        
        # Fecha
        timestamp = inc_dir.stat().st_mtime
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        table.add_row(str(idx), inc_dir.name[:60], file_name, date_str)
    
    console.print(table)
    console.print(f"\nTotal: [bold]{len(incidents)}[/bold] incidentes\n")
    
    return incidents


def display_analysis(result):
    """Muestra resultado del análisis optimizado para EC2"""
    if not result['success']:
        console.print(f"[red]❌ Error: {result['error']}[/red]\n")
        return
    
    # Mapeo de colores
    colors = {
        'TRUE_POSITIVE': 'red',
        'FALSE_POSITIVE': 'green',
        'REQUIRES_REVIEW': 'yellow'
    }
    color = colors.get(result['verdict'], 'white')
    emoji = {'TRUE_POSITIVE': '🚨', 'FALSE_POSITIVE': '✅', 'REQUIRES_REVIEW': '⚠️'}.get(result['verdict'], '❓')
    
    # Datos Contextuales
    ctx = result.get('incident_context', {})
    
    # Crear Tabla de Contexto (Sin bordes, integrada)
    context_table = Table(box=None, show_header=False, padding=(0, 2))
    context_table.add_column(style="bold white")
    context_table.add_column(style="white")
    
    context_table.add_row("Usuario:", str(ctx.get('user', 'N/A')))
    context_table.add_row("Origen:", str(ctx.get('source', 'N/A')))
    context_table.add_row("Destino:", f"[{color}]{ctx.get('destination', 'N/A')}[/{color}]")
    
    # Construir contenido del Panel Principal
    main_content = Group(
        Panel(
            result.get('executive_summary', 'Sin resumen disponible.'),
            title="[bold]Resumen Ejecutivo[/bold]",
            border_style="white"
        ),
        Text(""), # Espaciador
        context_table,
        Text(""), # Espaciador
        Panel(
            result['reasoning'],
            title="[bold]Análisis Técnico Detallado[/bold]",
            border_style=color
        )
    )

    # Renderizar Panel Final
    console.print(Panel(
        main_content,
        title=f"{emoji} {result['verdict']}",
        subtitle=f"Confianza: {result['confidence']*100:.1f}% | Riesgo: {result.get('risk_level', 'N/A')}",
        border_style=color,
        expand=True
    ))
    
    # Indicadores (Solo lista simple)
    if result.get('indicators'):
        console.print("[bold]Indicadores detectados:[/bold]")
        for ind in result['indicators']:
            console.print(f"  • {ind}", style="dim")
    
    console.print()


def collect_feedback(result):
    """Recolecta feedback del analista"""
    console.print(Panel.fit(
        "👨‍💼 Human-in-the-Loop: Validación de Analista",
        border_style="cyan"
    ))
    
    original_verdict = result['verdict']
    console.print(f"\n[bold]Veredicto Original:[/bold] {original_verdict}")
    
    # Pregunta si es correcto
    is_correct = Confirm.ask("\n¿El veredicto es correcto?", default=True)
    
    if is_correct:
        console.print("[green]✅ Veredicto confirmado[/green]\n")
        return None
    
    # Solicitar veredicto correcto
    console.print("\n[bold]Opciones:[/bold]")
    console.print("1. TRUE_POSITIVE")
    console.print("2. FALSE_POSITIVE")
    console.print("3. REQUIRES_REVIEW")
    
    choice = Prompt.ask("\nVeredicto correcto", choices=["1", "2", "3"])
    
    verdicts = {
        "1": "TRUE_POSITIVE",
        "2": "FALSE_POSITIVE",
        "3": "REQUIRES_REVIEW"
    }
    
    corrected_verdict = verdicts[choice]
    
    # Comentario
    comment = Prompt.ask("\nComentario del analista")
    
    # Relevancia
    relevance = float(Prompt.ask(
        "Relevancia para aprendizaje (0.0-1.0)",
        default="1.0"
    ))
    
    return {
        'original_verdict': original_verdict,
        'corrected_verdict': corrected_verdict,
        'analyst_comment': comment,
        'relevance_score': relevance
    }


def analyze_incidents_menu(analyzer):
    """Menú de análisis de incidentes"""
    incidents = list_incidents()
    
    if not incidents:
        if Confirm.ask("¿Descargar incidentes ahora?"):
            if download_incidents():
                incidents = list_incidents()
            else:
                return
        else:
            return
    
    console.print("[bold]Opciones:[/bold]")
    console.print("1. Analizar UN incidente")
    console.print("2. Analizar TODOS los incidentes pendientes")
    console.print("3. Analizar primeros 5 incidentes")
    
    choice = Prompt.ask("\nOpción", choices=["1", "2", "3"])
    
    incidents_to_analyze = []
    
    if choice == "1":
        idx = int(Prompt.ask("Número de incidente", default="1")) - 1
        if 0 <= idx < len(incidents):
            incidents_to_analyze = [incidents[idx]]
    elif choice == "2":
        incidents_to_analyze = incidents
    elif choice == "3":
        incidents_to_analyze = incidents[:5]
    
    console.print(f"\n[bold]Analizando {len(incidents_to_analyze)} incidente(s)...[/bold]\n")
    
    for idx, inc_dir in enumerate(incidents_to_analyze, 1):
        console.print(f"[cyan]{'='*80}[/cyan]")
        console.print(f"[bold cyan][{idx}/{len(incidents_to_analyze)}] {inc_dir.name}[/bold cyan]")
        console.print(f"[cyan]{'='*80}[/cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analizando con Gemini...", total=None)
            
            result = analyzer.analyze_incident(
                incident_id=inc_dir.name,
                incident_dir=inc_dir,
                use_rag=True
            )
            
            progress.update(task, completed=True)
        
        display_analysis(result)
        
        if result['success']:
            # Solicitar feedback
            feedback = collect_feedback(result)
            
            if feedback:
                analyzer.submit_feedback(
                    incident_id=result['incident_id'],
                    analysis_id=result['analysis_id'],
                    **feedback
                )
                console.print("[green]✅ Feedback guardado[/green]\n")
        
        if idx < len(incidents_to_analyze):
            time.sleep(2)


def dashboard_menu(db):
    """Menú de dashboard"""
    stats = db.get_database_stats()
    
    table = Table(title="📊 Estadísticas del Sistema", box=box.ROUNDED)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right", style="green")
    
    table.add_row("Total Análisis", str(stats.get('total_analyses', 0)))
    table.add_row("Feedback Recibido", str(stats.get('total_feedback', 0)))
    table.add_row("Precisión IA", f"{stats.get('ai_accuracy', 0):.1f}%")
    
    console.print(table)
    console.print()


def main_menu():
    """Menú principal"""
    print_header()
    
    db, analyzer = initialize_system()
    
    if not db or not analyzer:
        console.print("[red]Error inicializando sistema. Verifica configuración.[/red]")
        return
    
    while True:
        console.print("[bold]MENÚ PRINCIPAL[/bold]")
        console.print("1. 📥 Descargar Incidentes")
        console.print("2. 🔍 Analizar Incidentes")
        console.print("3. 📊 Ver Dashboard")
        console.print("4. 🚪 Salir\n")
        
        choice = Prompt.ask("Opción", choices=["1", "2", "3", "4"])
        
        console.print()
        
        if choice == "1":
            download_incidents()
        elif choice == "2":
            analyze_incidents_menu(analyzer)
        elif choice == "3":
            dashboard_menu(db)
        elif choice == "4":
            console.print("[bold]👋 Hasta luego![/bold]\n")
            break


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operación cancelada por el usuario[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error fatal: {e}[/red]\n")
