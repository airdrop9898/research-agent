"""CLI entrypoint."""
import asyncio
import typer
from rich.console import Console
from .orchestrator import run_research
from .config import MAX_QUESTIONS_PER_GOAL

app = typer.Typer(help="MiMo Research Agent — long-horizon autonomous research")
console = Console()


@app.command()
def research(
    goal: str = typer.Argument(..., help="Research goal (one sentence)"),
    questions: int = typer.Option(MAX_QUESTIONS_PER_GOAL, "--questions", "-q", help="Max research questions to decompose into"),
    pdf: bool = typer.Option(False, "--pdf", help="Also export PDF"),
    session: str = typer.Option(None, "--session", "-s", help="Session ID to continue (refine prior research)"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress progress output"),
):
    """Run research on a goal and generate a markdown report."""
    result = asyncio.run(run_research(goal, max_questions=questions, verbose=not quiet, pdf=pdf, session_id=session))
    if quiet:
        console.print(result.get("report_path", ""))


@app.command()
def sessions():
    """List recent research sessions."""
    from .storage import list_sessions
    from datetime import datetime
    rows = list_sessions(limit=20)
    if not rows:
        console.print("[yellow]No sessions yet.[/yellow]")
        return
    console.print("[bold]Recent research sessions:[/bold]\n")
    for s in rows:
        ts = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")
        console.print(f"  [cyan]{s['id']}[/cyan]  {ts}  {s['goal'][:80]}")
    console.print("\n[dim]To refine: ./venv/bin/python -m agent.cli research \"new question\" --session <id>[/dim]")


@app.command()
def show(session_id: str = typer.Argument(..., help="Session ID")):
    """Show details of a research session."""
    from .storage import get_session, get_turns
    from datetime import datetime
    sess = get_session(session_id)
    if not sess:
        console.print(f"[red]Session {session_id} not found[/red]")
        return
    console.print(f"[bold cyan]🔖 Session:[/bold cyan] {session_id}")
    console.print(f"[bold]Goal:[/bold] {sess['goal']}")
    console.print(f"[dim]Created: {datetime.fromtimestamp(sess['created_at'])}[/dim]\n")
    turns = get_turns(session_id)
    console.print(f"[bold]{len(turns)} turn(s):[/bold]")
    for t in turns:
        ts = datetime.fromtimestamp(t["created_at"]).strftime("%H:%M")
        console.print(f"  [{t['turn_idx']}] {ts} — {t['user_input'][:80]}")
        if t["report_path"]:
            console.print(f"      [dim]→ {t['report_path']}[/dim]")


@app.command()
def kg_search(
    query: str = typer.Argument(..., help="Search query (FTS5 syntax supported)"),
    limit: int = typer.Option(5, "--limit", "-n"),
    min_quality: int = typer.Option(0, "--min-quality"),
):
    """Search the knowledge graph of past findings."""
    from .kg import search_kg
    from datetime import datetime
    results = search_kg(query, limit=limit, min_quality=min_quality)
    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return
    console.print(f"[bold]Found {len(results)} match(es):[/bold]\n")
    for r in results:
        ts = datetime.fromtimestamp(r["indexed_at"]).strftime("%Y-%m-%d")
        console.print(f"[cyan]{r['session_id']}[/cyan] [dim]({ts}, q={r['quality_avg']:.0f})[/dim]")
        console.print(f"  [bold]Q:[/bold] {r['question']}")
        console.print(f"  [bold]A:[/bold] {r['answer'][:200]}...")
        console.print()


@app.command()
def kg_stats():
    """Show knowledge graph statistics."""
    from .kg import kg_stats as _stats
    s = _stats()
    console.print(f"[bold]Knowledge Graph Stats:[/bold]")
    console.print(f"  Total findings:  {s['total_findings']}")
    console.print(f"  Total sessions:  {s['total_sessions']}")
    console.print(f"  Avg quality:     {s['avg_quality_score']}")
    console.print(f"  [dim]DB: {s['db_path']}[/dim]")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8765, "--port"),
):
    """Start FastAPI server (for /research endpoint)."""
    import uvicorn
    from .server import app as fastapi_app
    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
