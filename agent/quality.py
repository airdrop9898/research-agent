"""Source quality scorer — rank sources by reliability."""
from urllib.parse import urlparse
from typing import List, Dict


# Tier 1: highly trusted sources (95-100)
TIER_1_DOMAINS = {
    "wikipedia.org", "arxiv.org", "nature.com", "science.org",
    "ieee.org", "acm.org", "cell.com", "thelancet.com", "nejm.org",
    "github.com", "github.io",  # canonical code
    "stanford.edu", "mit.edu", "harvard.edu", "ox.ac.uk", "cam.ac.uk",
}

# Tier 2: reputable mainstream (80-90)
TIER_2_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "wsj.com", "ft.com", "economist.com", "bloomberg.com",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "nature.com", "scientificamerican.com",
    "techcrunch.com", "wired.com", "arstechnica.com", "theverge.com",
    "huggingface.co", "papers.ssrn.com",
    "cnbc.com", "ft.com", "forbes.com",
}

# Tier 3: industry/specialized (70-80)
TIER_3_DOMAINS = {
    "coindesk.com", "cointelegraph.com", "theblock.co",
    "etherscan.io", "bscscan.com", "defillama.com",
    "ycombinator.com", "news.ycombinator.com", "stackoverflow.com",
    "medium.com",  # depends on author, generic mid
    "substack.com",  # depends on writer
    "dev.to", "stackshare.io",
    "kaggle.com", "openreview.net",
}

# Tier 4: blogs / aggregators / unverified (50-65)
TIER_4_DOMAINS = {
    "blogspot.com", "wordpress.com", "tumblr.com",
    "reddit.com", "twitter.com", "x.com",
}

# Blacklist: low-quality / spam (10-30)
BLACKLIST_DOMAINS = {
    "answers.com", "ask.com", "quora.com",  # often low-quality
    "ehow.com", "wikihow.com",
    "coinmarketcap.com/community",  # community posts
}

# Negative signals in URL
NEGATIVE_PATTERNS = [
    "/blog/", "/forum/", "/community/",  # less authoritative even on good domains
]

POSITIVE_PATTERNS = [
    "/research/", "/papers/", "/whitepaper", "/docs/",
]


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        # Strip www
        if host.startswith("www."):
            host = host[4:]
        return host.lower()
    except Exception:
        return ""


def matches_set(domain: str, domain_set: set) -> bool:
    """Check if domain or any parent domain is in the set."""
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        sub = ".".join(parts[i:])
        if sub in domain_set:
            return True
    return False


def score_source(url: str, snippet: str = "") -> int:
    """Score a source 0-100 based on domain reputation + URL signals."""
    if not url:
        return 30
    domain = domain_of(url)
    if not domain:
        return 30

    base = 50  # default mid

    if matches_set(domain, BLACKLIST_DOMAINS):
        base = 20
    elif matches_set(domain, TIER_1_DOMAINS):
        base = 95
    elif matches_set(domain, TIER_2_DOMAINS):
        base = 85
    elif matches_set(domain, TIER_3_DOMAINS):
        base = 75
    elif matches_set(domain, TIER_4_DOMAINS):
        base = 55
    # .gov / .edu boost
    if domain.endswith(".gov") or domain.endswith(".edu"):
        base = max(base, 90)
    # .org boost (slight)
    elif domain.endswith(".org"):
        base += 3

    # URL pattern adjustments
    url_lower = url.lower()
    for neg in NEGATIVE_PATTERNS:
        if neg in url_lower:
            base -= 5
    for pos in POSITIVE_PATTERNS:
        if pos in url_lower:
            base += 5

    # Snippet quality signals
    if snippet:
        if len(snippet) > 200:  # has substantial content
            base += 2
        if any(kw in snippet.lower() for kw in ("research", "study", "according to", "data shows")):
            base += 3

    return max(0, min(100, base))


def rank_sources(sources: List[Dict]) -> List[Dict]:
    """Add score to each source and sort by score (highest first)."""
    scored = []
    for s in sources:
        s["quality_score"] = score_source(s.get("url", ""), s.get("snippet", ""))
        scored.append(s)
    scored.sort(key=lambda x: -x["quality_score"])
    return scored


def filter_high_quality(sources: List[Dict], min_score: int = 60) -> List[Dict]:
    """Keep only sources with quality_score >= min_score."""
    return [s for s in sources if s.get("quality_score", 0) >= min_score]
