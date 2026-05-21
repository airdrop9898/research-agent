# MiMo Research Agent

Long-horizon autonomous research agent powered by MiMo V2.5 Pro.

Beri agent satu kalimat goal — agent decompose, search multi-source, iterate, verify, dan return laporan markdown lengkap.

## Features

- **Goal decomposition** via MiMo agentic planning
- **Multi-source search** — web (Tavily/Brave/DDG), arXiv, GitHub, news
- **Source quality scoring** — domain reputation tier-1 to blacklist
- **Iterative depth** — skeptic loop fact-checks own output, retries on gaps
- **Long-form output** — markdown 1,000-8,000 words
- **PDF export** — `--pdf` flag for client deliverables
- **Multi-turn refinement** — `--session <id>` to extend prior research
- **Knowledge graph** — FTS5 SQLite indexes findings across all sessions
- **CLI + REST API** — standalone tool or service

## Architecture

```
User Goal
   ↓
[1] Goal Decomposer (MiMo)  →  research questions
   ↓
[2] Source Router            →  web|arxiv|github|news per question
   ↓
[3] Search Executor          →  Tavily/Brave/DDG/arXiv/GitHub
   ↓
[4] Quality Scorer           →  rank sources by domain tier
   ↓
[5] Synthesizer (MiMo)       →  combine, cite [N]
   ↓
[6] Skeptic (MiMo)           →  gaps? contradictions? confidence?
   ↓ (loop until confident)
[7] Report Writer (MiMo)     →  markdown
   ↓
[8] PDF + KG indexing        →  outputs/research-*.md, .pdf, knowledge.db
```

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# (optional) add TAVILY_KEY for high-quality web search

# Run research
python -m agent.cli research "Analyze top 5 RWA projects 2026" --pdf

# Refine session
python -m agent.cli sessions
python -m agent.cli research "Focus on Ondo specifically" --session <id>

# Search knowledge graph
python -m agent.cli kg-search "tokenization"
python -m agent.cli kg-stats

# REST API
python -m agent.cli serve --port 8765
curl 'http://localhost:8765/research/raw?goal=YourGoal'
```

## Configuration

`.env`:
- `MIMO_BASE_URL` — default `http://localhost:20128/v1`
- `MIMO_MODEL` — default `xmtp/mimo-v2.5-pro`
- `TAVILY_KEY` — optional, get at tavily.com (1k free/month)
- `MAX_QUESTIONS`, `MAX_SOURCES`, `MAX_ITERATIONS` — pipeline tuning

## Output

```
outputs/
├── research-{slug}-{date}.md     # Full markdown report
├── research-{slug}-{date}.pdf    # PDF (with --pdf flag)
├── sessions.db                    # Multi-turn session storage
└── knowledge.db                   # Cross-session FTS5 KG
```

## Source Quality Tiers

| Tier | Score | Examples |
|---|---|---|
| 1 | 95 | wikipedia, arxiv, .edu, .gov, github |
| 2 | 85 | reuters, bloomberg, bbc, nature, techcrunch |
| 3 | 75 | coindesk, theblock, defillama, hackernews |
| 4 | 55 | reddit, twitter, blogspot |
| Black | 20 | quora, ehow, wikihow |

Sources below threshold (default 60) are filtered before synthesis.

## License

MIT

## Contact

- **GitHub:** [@airdrop9898](https://github.com/airdrop9898)
- **Email:** airdrop10969@gmail.com
- **Issues:** [github.com/airdrop9898/research-agent/issues](https://github.com/airdrop9898/research-agent/issues)

Maintained by Andri Wibisono. Open to collaboration, integration with knowledge management tools, and research partnerships.
