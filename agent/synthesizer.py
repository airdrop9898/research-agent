"""Synthesizer + Skeptic verification loop using MiMo."""
from typing import List, Dict
from .llm import MiMoClient


SYNTHESIZER_SYSTEM = """You are a research synthesizer. Given multiple search results for a research question, extract key facts and synthesize a coherent answer.

Rules:
- Use only information from the provided sources
- Cite sources by index [1], [2], etc.
- Flag contradictions explicitly
- Mark uncertain claims with "(unverified)"
- Be concise but complete
"""


SKEPTIC_SYSTEM = """You are a research skeptic. Given a synthesized answer and the original question, identify:

1. Information gaps (what's missing?)
2. Contradictions between sources
3. Unverified claims that need confirmation
4. Follow-up questions to fill gaps

Return JSON:
{
  "confidence": 0-100,
  "gaps": ["..."],
  "contradictions": ["..."],
  "follow_ups": [{"q": "...", "source": "web|arxiv|github|news"}]
}

If confidence >= 80, follow_ups can be empty.
"""


async def synthesize(
    llm: MiMoClient,
    question: str,
    search_results: List[Dict],
) -> str:
    """Synthesize answer from search results."""
    if not search_results:
        return "No sources found."

    sources_text = "\n\n".join([
        f"[{i+1}] {r.get('title', 'untitled')}\n{r.get('url', '')}\n{r.get('snippet', '')}"
        for i, r in enumerate(search_results)
    ])

    prompt = f"""Question: {question}

Sources:
{sources_text}

Synthesize a complete answer using only the sources above. Cite each claim with [N]."""
    return await llm.chat(prompt, system=SYNTHESIZER_SYSTEM, temperature=0.3, max_tokens=2048)


async def skeptic_review(
    llm: MiMoClient,
    question: str,
    answer: str,
) -> Dict:
    """Skeptic loop — find gaps, generate follow-up questions."""
    prompt = f"""Question: {question}

Synthesized Answer:
{answer}

Review for gaps, contradictions, unverified claims. Generate follow-up questions if confidence < 80."""
    try:
        return await llm.chat_json(prompt, system=SKEPTIC_SYSTEM, temperature=0.4)
    except Exception:
        return {"confidence": 70, "gaps": [], "contradictions": [], "follow_ups": []}
