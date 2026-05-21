"""Configuration for MiMo Research Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# MiMo LLM endpoint (OpenAI-compatible)
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "http://localhost:20128/v1")
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "sk-local")
MIMO_MODEL = os.getenv("MIMO_MODEL", "xmtp/mimo-v2.5-pro")

# Search APIs (optional)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
TAVILY_KEY = os.getenv("TAVILY_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

# Agent behavior
MAX_RESEARCH_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "5"))
MAX_QUESTIONS_PER_GOAL = int(os.getenv("MAX_QUESTIONS", "8"))
MAX_SOURCES_PER_QUESTION = int(os.getenv("MAX_SOURCES", "5"))

# Output
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
OUTPUT_DIR.mkdir(exist_ok=True)
