"""Main orchestrator — ties planner, search, synthesizer, skeptic, report together."""
import asyncio
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .llm import MiMoClient
from .planner import decompose_goal
from .search import execute_search
from .synthesizer import synthesize, skeptic_review
from .report import write_report
from .config import MAX_RESEARCH_ITERATIONS, MAX_SOURCES_PER_QUESTION

console = Console()


async def research_question(
    llm: MiMoClient,
    question: Dict,
    max_iterations: int = 2,
) -> Dict:
    """Research one question with iterative skeptic loop."""
    q_text = question["q"]
    source = question.get("source", "web")
    all_sources = []
    answer = ""

    for iteration in range(max_iterations):
        # Search
        results = await execute_search(q_text, source=source, limit=MAX_SOURCES_PER_QUESTION)
        all_sources.extend(results)

        if not results:
            answer = "No relevant sources found."
            break

        # Synthesize
        answer = await synthesize(llm, q_text, all_sources)

        # Skeptic review
        review = await skeptic_review(llm, q_text, answer)
        confidence = review.get("confidence", 0)

        if confidence >= 80 or iteration == max_iterations - 1:
            break

        # Iterate on follow-up
        follow_ups = review.get("follow_ups", [])
        if not follow_ups:
            break
        # Take first follow-up to refine
        next_q = follow_ups[0]
        q_text = next_q.get("q", q_text)
        source = next_q.get("source", source)

    return {
        "question": question["q"],
        "answer": answer,
        "sources": all_sources[:MAX_SOURCES_PER_QUESTION * 2],
    }


async def run_research(goal: str, max_questions: int = 8, verbose: bool = True, pdf: bool = False,
                       session_id: Optional[str] = None, prior_context: Optional[str] = None) -> Dict:
    """Full research pipeline.

    If session_id is provided and exists, treat this as a refinement turn —
    inject prior context into the planner and append findings.
    """
    from .storage import save_session, add_turn, get_session, new_session_id

    llm = MiMoClient()

    try:
        # Resolve session
        prior_findings: list = []
        original_goal = goal
        if session_id:
            sess = get_session(session_id)
            if sess:
                original_goal = sess["goal"]
                prior_findings = sess["data"].get("findings", [])
                if not prior_context:
                    # Build summary of prior findings as context
                    prior_context = "\n".join([
                        f"Q: {f['question']}\nA: {f['answer'][:300]}..."
                        for f in prior_findings[:5]
                    ])

        if verbose:
            console.print(f"[bold cyan]🎯 Goal:[/bold cyan] {goal}")
            if session_id and prior_findings:
                console.print(f"[dim]Continuing session {session_id} with {len(prior_findings)} prior findings[/dim]")

        # Phase 1: Decompose
        with console.status("[yellow]Decomposing goal into research questions..."):
            decompose_input = goal
            if prior_context:
                decompose_input = f"""{goal}

Prior research context (from previous turns):
{prior_context}

Generate questions that BUILD ON the prior findings — don't repeat ground already covered."""
            questions = await decompose_goal(llm, decompose_input, max_questions=max_questions)
        
        if verbose:
            console.print(f"\n[bold green]✓ {len(questions)} research questions:[/bold green]")
            for i, q in enumerate(questions, 1):
                console.print(f"  {i}. [{q['source']}] {q['q']}")

        # Phase 2: Research each question (parallel batches)
        findings = []
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), 
                     console=console, transient=False) as progress:
            task_ids = []
            for i, q in enumerate(questions, 1):
                task_ids.append(progress.add_task(f"[{i}/{len(questions)}] {q['q'][:60]}", total=1))

            # Run in batches of 3 to avoid overload
            batch_size = 3
            for batch_start in range(0, len(questions), batch_size):
                batch = questions[batch_start:batch_start + batch_size]
                results = await asyncio.gather(*[
                    research_question(llm, q) for q in batch
                ])
                findings.extend(results)
                for i in range(batch_start, min(batch_start + batch_size, len(questions))):
                    progress.update(task_ids[i], completed=1)

        # Phase 3: Final report
        if verbose:
            console.print("\n[yellow]📝 Writing final report...[/yellow]")
        
        report_md, file_path = await write_report(llm, original_goal if session_id else goal, prior_findings + findings, save=True, pdf=pdf)

        # Persist session
        new_id = session_id or new_session_id()
        all_findings = prior_findings + findings
        save_session(new_id, original_goal if session_id else goal, {
            "questions": questions,
            "findings": all_findings,
            "last_report_path": str(file_path) if file_path else None,
        })
        add_turn(new_id, goal, findings, str(file_path) if file_path else None)

        # Index findings into knowledge graph
        try:
            from .kg import index_findings
            index_findings(new_id, findings)
        except Exception as e:
            if verbose:
                console.print(f"[dim yellow]⚠ KG indexing skipped: {e}[/dim yellow]")

        if verbose:
            console.print(f"\n[bold green]✓ Report saved:[/bold green] {file_path}")
            if pdf:
                pdf_path = file_path.with_suffix(".pdf")
                if pdf_path.exists():
                    console.print(f"[bold green]✓ PDF saved:[/bold green] {pdf_path}")
            console.print(f"[dim]Word count: ~{len(report_md.split())} words[/dim]")
            console.print(f"[bold cyan]🔖 Session ID:[/bold cyan] {new_id} [dim](use --session {new_id} to refine)[/dim]")

        return {
            "session_id": new_id,
            "goal": original_goal if session_id else goal,
            "questions": questions,
            "findings": all_findings,
            "report_path": str(file_path) if file_path else None,
            "report_text": report_md,
        }

    finally:
        await llm.close()
