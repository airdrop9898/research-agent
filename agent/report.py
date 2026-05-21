"""Final report writer."""
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from .llm import MiMoClient
from .config import OUTPUT_DIR


REPORT_SYSTEM = """You are a senior research analyst writing a comprehensive markdown report.

Structure:
1. # Executive Summary (3-5 bullet key findings)
2. ## Background & Context
3. ## Detailed Findings (one section per research question, with citations)
4. ## Cross-Cutting Themes (patterns across findings)
5. ## Open Questions & Limitations
6. ## Recommendations (if applicable)
7. ## References (numbered list with URLs)

Rules:
- Use proper markdown headers, lists, tables
- Cite sources inline as [N], expand in References section
- Include a TL;DR at top
- Length: 2000-8000 words depending on complexity
- No fluff, no AI-isms ("In conclusion", "It's important to note")
- Concrete data, numbers, dates where available
- Indonesian/English: match the goal's language
"""


def slugify(text: str, max_len: int = 50) -> str:
    """Simple slugify for filenames."""
    import re
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].strip("-")


async def write_report(
    llm: MiMoClient,
    goal: str,
    findings: List[Dict],
    save: bool = True,
    pdf: bool = False,
) -> tuple[str, Path]:
    """
    Generate final markdown report.

    findings: [{"question": str, "answer": str, "sources": [...]}]
    Returns (markdown_text, file_path).
    """
    findings_text = "\n\n---\n\n".join([
        f"### Q: {f['question']}\n\n{f['answer']}\n\nSources:\n" +
        "\n".join([f"- [{i+1}] {s.get('title', '')}: {s.get('url', '')} (quality: {s.get('quality_score', '?')})"
                   for i, s in enumerate(f.get('sources', []))])
        for f in findings
    ])

    prompt = f"""Goal: {goal}

Research Findings:
{findings_text}

Write a comprehensive markdown report. Include all citations from the findings."""

    report_md = await llm.chat(
        prompt,
        system=REPORT_SYSTEM,
        temperature=0.5,
        max_tokens=8192,
    )

    # Add header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# Research Report: {goal}

*Generated: {timestamp} by MiMo Research Agent*

---

"""
    full_report = header + report_md

    # Save
    file_path = None
    if save:
        slug = slugify(goal)
        date = datetime.now().strftime("%Y%m%d")
        file_path = OUTPUT_DIR / f"research-{slug}-{date}.md"
        file_path.write_text(full_report, encoding="utf-8")

        if pdf:
            from .pdf import md_to_pdf
            pdf_path = file_path.with_suffix(".pdf")
            try:
                md_to_pdf(full_report, pdf_path, title=goal)
            except RuntimeError as e:
                # reportlab missing — log but don't fail
                pass

    return full_report, file_path
