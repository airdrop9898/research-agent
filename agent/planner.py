"""Goal decomposer + source router using MiMo."""
from typing import List, Dict
from .llm import MiMoClient


PLANNER_SYSTEM = """You are a research planner. Given a high-level goal, decompose it into specific, atomic research questions.

Each question must be:
- Concrete (answerable with facts, not opinions)
- Self-contained (no missing context)
- Source-typed (web/arxiv/github/news)

Return JSON: {"questions": [{"q": "...", "source": "web|arxiv|github|news", "priority": 1-5}]}
"""


SOURCE_ROUTER_HINTS = {
    "academic": "arxiv",
    "paper": "arxiv",
    "research": "arxiv",
    "github": "github",
    "code": "github",
    "repo": "github",
    "news": "news",
    "latest": "news",
    "today": "news",
}


async def decompose_goal(llm: MiMoClient, goal: str, max_questions: int = 8) -> List[Dict]:
    """Break high-level goal into atomic research questions."""
    prompt = f"""Goal: {goal}

Decompose into {max_questions} concrete research questions. Each question should target one specific fact or angle.

Output JSON only."""
    result = await llm.chat_json(prompt, system=PLANNER_SYSTEM, temperature=0.4)
    questions = result.get("questions", [])
    # Clamp and validate
    valid = []
    for q in questions[:max_questions]:
        if not q.get("q"): continue
        valid.append({
            "q": q["q"],
            "source": q.get("source", "web"),
            "priority": int(q.get("priority", 3)),
        })
    return valid
