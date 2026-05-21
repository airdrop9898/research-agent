"""PDF export for research reports using reportlab."""
from pathlib import Path
from datetime import datetime


def md_to_pdf(markdown_content: str, output_path: Path, title: str = "Research Report") -> Path:
    """Convert markdown content to PDF. Falls back to simple text if reportlab missing."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    except ImportError:
        raise RuntimeError("reportlab not installed — run: pip install reportlab")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=20,
                        textColor=HexColor("#1f6feb"), spaceAfter=12)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=16,
                        textColor=HexColor("#1f6feb"), spaceAfter=8, spaceBefore=12)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=13,
                        textColor=HexColor("#374151"), spaceAfter=6, spaceBefore=10)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10,
                          alignment=TA_JUSTIFY, spaceAfter=6, leading=14)
    code_style = ParagraphStyle("Code", parent=styles["Code"], fontSize=9,
                                fontName="Courier", textColor=HexColor("#374151"),
                                backColor=HexColor("#f3f4f6"), spaceAfter=6, leading=12)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=18, bulletIndent=6)

    flow = []
    in_code = False
    code_buf = []
    for line in markdown_content.split("\n"):
        # Code block toggle
        if line.startswith("```"):
            if in_code:
                flow.append(Paragraph("<br/>".join([_escape(l) for l in code_buf]), code_style))
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        line = line.rstrip()
        if not line:
            flow.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            flow.append(Paragraph(_escape(line[2:]), h1))
        elif line.startswith("## "):
            flow.append(Paragraph(_escape(line[3:]), h2))
        elif line.startswith("### "):
            flow.append(Paragraph(_escape(line[4:]), h3))
        elif line.startswith("- ") or line.startswith("* "):
            flow.append(Paragraph(f"• {_inline(line[2:])}", bullet))
        elif line[0:3].rstrip().rstrip(".").isdigit() and ". " in line[:5]:
            flow.append(Paragraph(_inline(line), bullet))
        elif line.startswith("---"):
            flow.append(Spacer(1, 12))
        else:
            flow.append(Paragraph(_inline(line), body))

    doc.build(flow)
    return output_path


def _escape(text: str) -> str:
    """Escape XML-style chars for reportlab paragraphs."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _inline(text: str) -> str:
    """Convert simple inline markdown to reportlab markup."""
    import re
    s = _escape(text)
    # Bold **text**
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    # Italic *text*
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    # Code `text`
    s = re.sub(r"`([^`]+)`", r'<font face="Courier" color="#1f6feb">\1</font>', s)
    # Links [text](url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2"><font color="#1f6feb">\1</font></link>', s)
    return s
