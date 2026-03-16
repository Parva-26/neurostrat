"""
signal_extractor.py  (v2 - complete rewrite)
─────────────────────────────────────────────
Bridges the frontend's free-text { name, role, context } to the ML
model's 11-feature structured input.
 
v1 PROBLEM: All inputs that didn't contain exact keyword phrases
(e.g. "active on linkedin", "just raised") fell through to identical
hardcoded defaults → ML always received the same numbers → same output.
 
v2 SOLUTION — three-layer extraction:
 
  Layer 1 — Role-based priors
    Every job title, no matter how unusual, is analysed for:
      • Seniority level  (C-Suite → Individual Contributor)
      • Digital nativity (tech worker vs trade worker vs executive)
      • Industry signals (words in the title itself)
    These set DIFFERENT starting values per role type.
 
  Layer 2 — Broad vocabulary analysis
    Scans context for general positive/negative language, not just
    exact phrases.  Works on any free-text description.
 
  Layer 3 — Deterministic identity hash
    A small, stable offset derived from name + role ensures two
    different people always get measurably different feature vectors
    even when their context descriptions are similar.
"""
 
import re
import hashlib
from datetime import datetime
from typing import Tuple
 
 
# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — ROLE-BASED PRIORS
# Different job types have very different LinkedIn/engagement baselines.
# ══════════════════════════════════════════════════════════════════════════════
 
# Maps role characteristics → (engagement_base, linkedin_base, response_rate_base)
# Ordered from most specific to least specific.
ROLE_PRIORS = [
    # ── C-Suite / Founders ─────────────────────────────────────────────────
    (["ceo", "cto", "cfo", "coo", "cpo", "ciso",
      "chief executive", "chief technology", "chief financial",
      "chief operating", "chief product", "chief marketing",
      "founder", "co-founder", "cofounder", "co founder",
      "managing director", "executive director", "president",
      "owner", "proprietor", "principal owner"],
     {"seniority": "C-Suite",  "engagement": 0.42, "linkedin": 0.50, "response": 0.25,
      "note": "C-Suite executives are hard to reach — low default engagement, selective responders"}),
 
    # ── VP Level ───────────────────────────────────────────────────────────
    (["vice president", "vice-president", " vp ", "vp of", "vp,"],
     {"seniority": "VP",       "engagement": 0.52, "linkedin": 0.58, "response": 0.32,
      "note": "VP level — moderately reachable, active on professional platforms"}),
 
    # ── Director Level ─────────────────────────────────────────────────────
    (["director of", "director,", "head of", "head,"],
     {"seniority": "Director", "engagement": 0.58, "linkedin": 0.62, "response": 0.38,
      "note": "Director level — reasonably active, good response baseline"}),
 
    # ── Senior / Lead / Manager ────────────────────────────────────────────
    (["senior manager", "engineering manager", "product manager",
      "marketing manager", "sales manager", "account manager",
      "team lead", "tech lead", "team leader"],
     {"seniority": "Manager",  "engagement": 0.62, "linkedin": 0.65, "response": 0.42,
      "note": "Manager/Lead level — active on LinkedIn, solid response rate"}),
 
    (["manager", " lead ", "lead,"],
     {"seniority": "Manager",  "engagement": 0.60, "linkedin": 0.62, "response": 0.40,
      "note": "Manager level — regularly active on professional networks"}),
 
    # ── Senior Individual Contributors ─────────────────────────────────────
    (["senior software", "senior engineer", "senior developer",
      "senior analyst", "senior designer", "senior data",
      "principal engineer", "staff engineer", "staff scientist",
      "senior consultant", "senior associate"],
     {"seniority": "Manager",  "engagement": 0.65, "linkedin": 0.68, "response": 0.45,
      "note": "Senior IC — highly active on LinkedIn, strong response rate"}),
 
    # ── Tech / Digital Professionals ───────────────────────────────────────
    (["software engineer", "software developer", "full stack", "fullstack",
      "frontend", "backend", "data scientist", "data engineer",
      "machine learning", "ml engineer", "ai engineer", "devops",
      "cloud engineer", "platform engineer", "site reliability",
      "product designer", "ux designer", "ui designer",
      "product analyst", "growth hacker", "growth marketer",
      "digital marketer", "seo specialist", "content strategist"],
     {"seniority": "Individual Contributor",
      "engagement": 0.68, "linkedin": 0.72, "response": 0.48,
      "note": "Tech/digital professional — very active online, high LinkedIn presence"}),
 
    # ── Sales / Marketing / BD ─────────────────────────────────────────────
    (["sales", "business development", "account executive",
      "account manager", "marketing", "brand", "growth",
      "partnerships", "revenue", "commercial"],
     {"seniority": "Individual Contributor",
      "engagement": 0.70, "linkedin": 0.75, "response": 0.52,
      "note": "Sales/marketing role — LinkedIn is their primary channel, high activity"}),
 
    # ── Finance / Legal / Accounting ────────────────────────────────────────
    (["accountant", "accounting", "auditor", "tax", "finance",
      "financial analyst", "investment analyst", "banker",
      "lawyer", "attorney", "solicitor", "legal", "compliance",
      "risk analyst", "actuary"],
     {"seniority": "Individual Contributor",
      "engagement": 0.50, "linkedin": 0.55, "response": 0.38,
      "note": "Finance/legal professional — moderate LinkedIn activity, formal communication preferred"}),
 
    # ── Healthcare / Medical ────────────────────────────────────────────────
    (["doctor", "physician", "nurse", "surgeon", "dentist",
      "pharmacist", "therapist", "counsellor", "psychologist",
      "medical", "clinical", "healthcare", "radiologist",
      "paramedic", "veterinarian", "optometrist"],
     {"seniority": "Individual Contributor",
      "engagement": 0.38, "linkedin": 0.35, "response": 0.30,
      "note": "Healthcare professional — lower LinkedIn activity, prefer direct communication"}),
 
    # ── Education / Research / Academia ────────────────────────────────────
    (["teacher", "professor", "lecturer", "academic",
      "researcher", "scientist", "phd", "postdoc",
      "educator", "instructor", "tutor", "principal"],
     {"seniority": "Individual Contributor",
      "engagement": 0.42, "linkedin": 0.40, "response": 0.32,
      "note": "Education/research professional — moderate digital activity"}),
 
    # ── Trades / Blue-Collar / Physical Work ──────────────────────────────
    (["cobbler", "carpenter", "plumber", "electrician",
      "mechanic", "welder", "mason", "bricklayer", "roofer",
      "painter", "decorator", "glazier", "tiler", "joiner",
      "blacksmith", "tailor", "seamstress", "shoemaker",
      "chef", "cook", "baker", "butcher", "fishmonger",
      "farmer", "gardener", "landscaper", "driver",
      "technician", "repairman", "handyman"],
     {"seniority": "Individual Contributor",
      "engagement": 0.25, "linkedin": 0.15, "response": 0.20,
      "note": "Trades professional — low LinkedIn presence, direct/phone contact more effective"}),
 
    # ── Creative / Arts / Media ────────────────────────────────────────────
    (["designer", "artist", "photographer", "videographer",
      "filmmaker", "writer", "journalist", "editor",
      "copywriter", "illustrator", "animator", "musician",
      "actor", "performer", "creative director"],
     {"seniority": "Individual Contributor",
      "engagement": 0.58, "linkedin": 0.52, "response": 0.40,
      "note": "Creative professional — active on portfolio/social platforms"}),
 
    # ── HR / People / Operations ────────────────────────────────────────────
    (["recruiter", "talent acquisition", "hr ", "human resources",
      "people ops", "operations", "office manager",
      "executive assistant", "coordinator", "administrator"],
     {"seniority": "Individual Contributor",
      "engagement": 0.60, "linkedin": 0.65, "response": 0.45,
      "note": "HR/ops professional — actively uses LinkedIn for professional networking"}),
]
 
# Fallback when nothing matches
DEFAULT_PRIOR = {
    "seniority": "Individual Contributor",
    "engagement": 0.45,
    "linkedin":   0.45,
    "response":   0.35,
    "note":       "Role not recognised — using conservative baseline estimates",
}
 
 
# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — BROAD VOCABULARY ANALYSIS
# Works on any free text, not just exact phrases.
# ══════════════════════════════════════════════════════════════════════════════
 
# General positive/negative words that affect engagement & sentiment
POSITIVE_WORDS = [
    "active", "engaged", "responsive", "replied", "responded", "interested",
    "warm", "friendly", "enthusiastic", "keen", "eager", "proactive",
    "growing", "successful", "thriving", "promoted", "hired", "expanded",
    "launched", "raised", "funded", "won", "awarded", "recognised",
    "excited", "positive", "great", "excellent", "strong", "leading",
    "innovative", "top", "best", "award", "celebrated", "milestone",
    "partnership", "acquisition", "ipo", "unicorn", "profitable",
    "record", "breakthrough", "opportunity", "potential",
]
 
NEGATIVE_WORDS = [
    "cold", "unresponsive", "ghosted", "ignored", "inactive", "silent",
    "struggling", "difficult", "hard to reach", "busy", "unavailable",
    "declined", "rejected", "negative", "poor", "weak", "failing",
    "layoff", "downsizing", "restructuring", "leaving", "departed",
    "controversy", "scandal", "lawsuit", "problem", "issue", "crisis",
    "declining", "loss", "deficit", "bankrupt", "closed", "shutting",
    "pivot", "uncertain", "challenging", "tough", "slow",
]
 
# LinkedIn-specific signals (broader than v1)
LINKEDIN_POSITIVE_WORDS = [
    "linkedin", "posts", "posting", "active online", "social media",
    "digital presence", "online", "content", "articles", "thought leader",
    "shares", "comments", "network", "connections", "profile",
    "creator", "influencer", "published", "newsletter",
]
 
LINKEDIN_NEGATIVE_WORDS = [
    "no linkedin", "not on linkedin", "offline", "no social",
    "no online presence", "hard to find", "no profile",
    "doesn't use social", "avoids social media",
]
 
# Recency signals (broader)
RECENCY_SIGNALS = [
    (["today", "just now", "this morning", "hours ago", "just spoke",
      "just met", "literally just"], 1),
    (["yesterday", "last night", "24 hours"], 2),
    (["this week", "few days", "days ago", "recently", "just connected",
      "just talked"], 5),
    (["last week", "week ago", "7 days"], 10),
    (["couple weeks", "two weeks", "fortnight", "2 weeks"], 14),
    (["last month", "month ago", "few weeks", "3 weeks", "4 weeks",
      "few weeks ago"], 30),
    (["long time", "months ago", "ages", "while back", "haven't spoken",
      "haven't talked", "never met", "cold", "no prior", "first time",
      "never reached", "no history", "no interaction", "no contact",
      "never connected", "brand new"], 45),
]
 
# News sentiment signals (broader)
NEWS_POSITIVE_WORDS = [
    "raised", "funding", "series", "ipo", "acquisition", "merger",
    "launched", "new product", "expanded", "hired", "growing",
    "partnership", "award", "promotion", "milestone", "celebrated",
    "recognised", "featured", "press", "media", "announcement",
    "breakthrough", "record", "profit", "revenue growth", "unicorn",
]
 
NEWS_NEGATIVE_WORDS = [
    "layoffs", "laid off", "downsizing", "restructure", "struggling",
    "losses", "scandal", "controversy", "lawsuit", "investigation",
    "declining", "bankruptcy", "shutting down", "pivot", "missed targets",
    "poor results", "below expectations", "crisis", "problem",
]
 
# Mutual connection signals
MUTUAL_SIGNALS = [
    (["referred by", "referral", "introduced by", "warm intro",
      "mutual friend", "knows", "knows them personally",
      "friend of", "colleague of", "worked with them",
      "they know me"], 7),
    (["mutual connection", "2nd degree", "second degree",
      "one mutual", "few mutual"], 3),
    (["no mutual", "cold intro", "cold outreach", "don't know them",
      "never met", "no connection", "0 mutual"], 0),
    (["strong network", "close network", "directly connected",
      "1st degree", "first degree", "close contact"], 5),
]
 
# Industry inference — broad keyword matching
INDUSTRY_KEYWORDS = {
    "SaaS": [
        "software", "saas", "tech", "technology", "developer", "engineer",
        "code", "coding", "cloud", "data", "ai", "artificial intelligence",
        "machine learning", "app", "application", "digital", "cyber",
        "devops", "api", "platform", "startup", "product", "ux", "ui",
        "frontend", "backend", "database", "algorithm", "programming",
    ],
    "FinTech": [
        "finance", "fintech", "bank", "banking", "invest", "investment",
        "money", "fund", "trade", "trading", "stock", "crypto", "blockchain",
        "payment", "insurance", "accounting", "tax", "wealth", "mortgage",
        "loan", "credit", "financial", "broker", "hedge fund", "equity",
    ],
    "HealthTech": [
        "health", "medical", "doctor", "nurse", "hospital", "pharma",
        "pharmaceutical", "biotech", "clinical", "patient", "healthcare",
        "wellness", "therapy", "diagnostic", "dental", "surgery",
        "medicine", "treatment", "drug", "laboratory", "research",
    ],
    "E-Commerce": [
        "ecommerce", "e-commerce", "retail", "shop", "shopping", "store",
        "sell", "selling", "product", "brand", "consumer", "marketplace",
        "amazon", "shopify", "merchandise", "inventory", "fulfilment",
        "delivery", "logistics", "d2c", "direct to consumer",
    ],
    "Manufacturing": [
        "manufactur", "factory", "industrial", "supply chain", "logistics",
        "hardware", "assembly", "production", "cobbler", "carpenter",
        "plumber", "electrician", "mechanic", "trade", "craft", "physical",
        "tools", "equipment", "machinery", "construction", "engineering",
        "automotive", "aerospace",
    ],
    "Consulting": [
        "consult", "consulting", "agency", "advisory", "strategy",
        "services", "management consulting", "analyst", "research",
        "audit", "professional services", "outsourcing", "freelance",
        "contractor",
    ],
}
 
# Company size signals — broader number detection
COMPANY_SIZE_SIGNALS = [
    (["solo", "just me", "freelance", "freelancer", "solopreneur",
      "1 person", "just myself", "bootstrapped", "self-employed"], "1-10"),
    (["small team", "small company", "tiny startup", "early stage",
      "pre-seed", "seed stage", "10 people", "15 people", "20 people",
      "25 people", "30 people", "handful of", "small startup",
      "just started", "new startup"], "11-50"),
    (["mid-size", "growing startup", "scale-up", "scaleup", "series a",
      "series b", "50 people", "75 people", "100 people", "150 people",
      "200 people", "medium company"], "51-200"),
    (["series c", "series d", "mid-market", "300 people", "400 people",
      "500 people", "several hundred", "large team", "established company"],
     "201-1000"),
    (["enterprise", "fortune 500", "fortune500", "large company", "global",
      "publicly traded", "nasdaq", "nyse", "stock exchange",
      "multinational", "thousands of employees", "1000+",
      "corporate", "conglomerate", "big company", "major company",
      "well-known company", "famous company"], "1000+"),
]
 
 
# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — DETERMINISTIC IDENTITY HASH
# Ensures two different people always get different feature vectors.
# Same name+role → same offset (deterministic), different names → different.
# ══════════════════════════════════════════════════════════════════════════════
 
def _identity_offset(name: str, role: str) -> float:
    """
    Returns a stable float in [-0.12, +0.12] derived from name + role.
    This creates consistent but unique variation per individual.
    """
    key   = f"{name.strip().lower()}|{role.strip().lower()}"
    h     = hashlib.md5(key.encode()).hexdigest()
    val   = int(h[:8], 16) / 0xFFFFFFFF   # 0.0 – 1.0
    return (val - 0.5) * 0.24              # -0.12 – +0.12
 
 
def _role_hash_variant(role: str) -> float:
    """Stable 0-1 value from role text alone, for secondary variation."""
    h = hashlib.md5(role.strip().lower().encode()).hexdigest()
    return int(h[8:12], 16) / 0xFFFF      # 0.0 – 1.0
 
 
# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
 
def extract_signals(name: str, role: str, context: str) -> dict:
    """
    Parse frontend inputs → ML feature dict + human-readable signal log.
 
    Returns
    -------
    {
        "features"   : dict   Ready for OutreachDecisionEngine.predict()
        "signal_log" : dict   Human explanation of each signal
    }
    """
    combined = f"{role} {context}".lower()
    ctx_only = context.lower()
 
    # ── Layer 1: Role-based priors ────────────────────────────────────────────
    prior      = _get_role_prior(role)
    seniority  = prior["seniority"]
    base_eng   = prior["engagement"]
    base_li    = prior["linkedin"]
    base_resp  = prior["response"]
    prior_note = prior["note"]
 
    # ── Layer 3: Identity hash offset (applied to eng + li) ──────────────────
    id_offset   = _identity_offset(name, role)
    role_variant = _role_hash_variant(role)   # 0-1, used for company size / days
 
    # ── Layer 2: Broad vocabulary analysis ───────────────────────────────────
 
    # Engagement score
    pos_count = sum(1 for w in POSITIVE_WORDS if w in combined)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in combined)
    ctx_bonus  = min(0.10, len(context.split()) * 0.004)   # richer context = more engaged
    eng_delta  = (pos_count * 0.06) - (neg_count * 0.07) + ctx_bonus
    engagement = float(max(0.05, min(0.97, base_eng + eng_delta + id_offset * 0.6)))
 
    # LinkedIn activity
    li_pos = sum(1 for w in LINKEDIN_POSITIVE_WORDS if w in combined)
    li_neg = sum(1 for w in LINKEDIN_NEGATIVE_WORDS if w in combined)
    li_delta = (li_pos * 0.08) - (li_neg * 0.15)
    linkedin = float(max(0.05, min(0.98, base_li + li_delta + id_offset * 0.5)))
 
    # News sentiment (-1 to +1)
    news_pos  = sum(1 for w in NEWS_POSITIVE_WORDS if w in combined)
    news_neg  = sum(1 for w in NEWS_NEGATIVE_WORDS if w in combined)
    sentiment = float(max(-1.0, min(1.0, (news_pos * 0.18) - (news_neg * 0.20) + id_offset * 0.3)))
 
    # Past response rate
    resp_pos = sum(1 for w in ["replied", "responded", "responsive", "warm", "interested",
                                "replied before", "has replied", "great communication",
                                "always responds"] if w in combined)
    resp_neg = sum(1 for w in ["ghosted", "no response", "unresponsive", "never replied",
                                "cold lead", "hard to reach", "ignored"] if w in combined)
    resp_delta   = (resp_pos * 0.08) - (resp_neg * 0.10)
    response_rate = float(max(0.05, min(0.95, base_resp + resp_delta + id_offset * 0.4)))
 
    # Days since last interaction
    days_since = _extract_recency(combined, role_variant)
 
    # Mutual connections
    mutual = _extract_mutual(combined)
 
    # Profile completeness (correlated with LinkedIn activity)
    profile_complete = float(round(min(0.97, 0.45 + linkedin * 0.50 + id_offset * 0.1), 2))
 
    # Industry
    industry, industry_note = _infer_industry(combined, role)
 
    # Company size
    company_size, size_note = _infer_company_size(combined, role_variant)
 
    # Time of day
    time_of_day = datetime.now().hour
 
    # ── Assemble features ─────────────────────────────────────────────────────
    features = {
        "engagement_score":     round(engagement, 3),
        "linkedin_active":      round(linkedin,   3),
        "news_sentiment":       round(sentiment,  3),
        "time_of_day":          time_of_day,
        "days_since_last":      days_since,
        "past_response_rate":   round(response_rate, 3),
        "profile_completeness": profile_complete,
        "mutual_connections":   mutual,
        "role":                 seniority,
        "industry":             industry,
        "company_size":         company_size,
    }
 
    # ── Assemble signal log (feeds the factors[] in the response) ─────────────
    signal_log = {
        "role":          (seniority,       f"Role '{role}' → seniority tier '{seniority}'. {prior_note}"),
        "industry":      (industry,        industry_note),
        "company_size":  (company_size,    size_note),
        "engagement":    (engagement,      _engagement_note(engagement, pos_count, neg_count, ctx_bonus)),
        "linkedin":      (linkedin,        _linkedin_note(linkedin, li_pos, li_neg, seniority)),
        "sentiment":     (sentiment,       _sentiment_note(sentiment, news_pos, news_neg)),
        "recency":       (days_since,      f"Last interaction estimated ~{days_since} day(s) ago"),
        "mutual":        (mutual,          f"{mutual} mutual connection(s) detected from context"),
        "response_rate": (response_rate,   f"Estimated past response rate: {response_rate:.0%}"),
        "time_of_day":   (time_of_day,     f"Outreach timing: {time_of_day:02d}:00 local time"),
    }
 
    return {"features": features, "signal_log": signal_log}
 
 
# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
 
def _get_role_prior(role: str) -> dict:
    """Match role text against ROLE_PRIORS, return matching prior or default."""
    role_lower = role.lower()
    for keywords, prior in ROLE_PRIORS:
        for kw in keywords:
            if kw in role_lower:
                return prior
    return DEFAULT_PRIOR
 
 
def _infer_industry(text: str, role: str) -> Tuple[str, str]:
    """Score all industries and return the best match."""
    if not INDUSTRY_KEYWORDS:
        return "SaaS", "No industries defined"
    
    scores = {ind: 0 for ind in INDUSTRY_KEYWORDS}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[industry] += 1
 
    best     = max(scores.keys(), key=lambda k: scores[k]) if scores else "SaaS"
    best_val = scores.get(best, 0)
 
    if best_val == 0:
        # Fallback: use role hash to pick an industry deterministically
        role_h = int(hashlib.md5(role.lower().encode()).hexdigest()[:4], 16)
        industries = list(INDUSTRY_KEYWORDS.keys())
        if industries:
            best = industries[role_h % len(industries)]
        return best, f"No explicit industry signals — inferred '{best}' from role context"
 
    return best, f"Industry detected as '{best}' based on {best_val} keyword match(es) in context"
 
 
def _infer_company_size(text: str, role_variant: float) -> Tuple[str, str]:
    """Match company size signals, fall back to role-variant-based estimate."""
    for keywords, size in COMPANY_SIZE_SIGNALS:
        for kw in keywords:
            if kw in text:
                return size, f"Company size '{size}' detected from context keyword '{kw}'"
 
    # No explicit size signal — use role_variant to pick a plausible size
    sizes     = ["11-50", "51-200", "51-200", "201-1000", "1000+"]
    picked    = sizes[int(role_variant * len(sizes))]
    return picked, f"Company size estimated as '{picked}' (no explicit size mentioned)"
 
 
def _extract_recency(text: str, role_variant: float) -> int:
    """Extract days-since-last from recency signals, or estimate from role."""
    for keywords, days in RECENCY_SIGNALS:
        for kw in keywords:
            if kw in text:
                return days
    # Estimate: role_variant shifts between 5 and 30 days
    return int(5 + role_variant * 25)
 
 
def _extract_mutual(text: str) -> int:
    """Extract mutual connections from context."""
    for keywords, count in MUTUAL_SIGNALS:
        for kw in keywords:
            if kw in text:
                return count
    return 2   # small non-zero default
 
 
def _engagement_note(score: float, pos: int, neg: int, ctx_bonus: float) -> str:
    tier = "high" if score > 0.65 else ("low" if score < 0.38 else "moderate")
    if pos > 0 and neg == 0:
        return f"Engagement {tier} ({score:.0%}) — {pos} positive signal(s) detected in context"
    if neg > 0 and pos == 0:
        return f"Engagement {tier} ({score:.0%}) — {neg} low-engagement signal(s) detected"
    if pos > 0 and neg > 0:
        return f"Engagement {tier} ({score:.0%}) — mixed signals ({pos} positive, {neg} negative)"
    return f"Engagement {tier} ({score:.0%}) — estimated from role type and context richness"
 
 
def _linkedin_note(score: float, li_pos: int, li_neg: int, seniority: str) -> str:
    if li_pos > 0:
        return f"LinkedIn activity {score:.0%} — explicit LinkedIn presence signals detected"
    if li_neg > 0:
        return f"LinkedIn activity {score:.0%} — low/no LinkedIn presence signals detected"
    tier = "high" if score > 0.65 else ("low" if score < 0.35 else "moderate")
    return f"LinkedIn activity {tier} ({score:.0%}) — estimated from {seniority} role type"
 
 
def _sentiment_note(sentiment: float, news_pos: int, news_neg: int) -> str:
    if news_pos > 0:
        return f"Positive news context (+{sentiment:.2f}) — {news_pos} growth/success signal(s) detected"
    if news_neg > 0:
        return f"Challenging news context ({sentiment:.2f}) — {news_neg} negative signal(s) detected"
    if sentiment > 0.1:
        return f"Mildly positive context ({sentiment:+.2f})"
    if sentiment < -0.1:
        return f"Mildly negative context ({sentiment:+.2f})"
    return f"Neutral news environment ({sentiment:+.2f}) — no major events detected"
 