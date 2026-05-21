"""FastAPI server for /research endpoint."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from .orchestrator import run_research

app = FastAPI(
    title="MiMo Research Agent",
    description="Long-horizon autonomous research powered by MiMo V2.5 Pro",
    version="0.1.0",
)


class ResearchRequest(BaseModel):
    goal: str = Field(..., min_length=10, max_length=500, description="Research goal")
    max_questions: int = Field(8, ge=1, le=20, description="Max questions to decompose into")


class ResearchResponse(BaseModel):
    goal: str
    n_questions: int
    n_findings: int
    report_path: str
    report_preview: str


@app.get("/")
def root():
    return {"service": "mimo-research-agent", "status": "ok"}


@app.post("/research", response_model=ResearchResponse)
async def research_endpoint(req: ResearchRequest):
    try:
        result = await run_research(req.goal, max_questions=req.max_questions, verbose=False)
        return ResearchResponse(
            goal=result["goal"],
            n_questions=len(result["questions"]),
            n_findings=len(result["findings"]),
            report_path=result["report_path"] or "",
            report_preview=result["report_text"][:1000] + "...",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/raw", response_class=PlainTextResponse)
async def research_raw(goal: str, max_questions: int = 8):
    """Returns full markdown report (for curl/clients)."""
    try:
        result = await run_research(goal, max_questions=max_questions, verbose=False)
        return result["report_text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
