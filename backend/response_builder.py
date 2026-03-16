"""
response_builder.py
───────────────────
Converts the ML model's raw Strategy Card dict into the exact JSON
shape the NeuroStrat frontend expects.

Frontend contract (from StrategyCard.tsx + History.tsx):
  POST /api/strategy  →  { channel, confidence, contactName, factors[] }
  GET  /api/history   →  HistoryItem[]

ML model outputs:
  channel                 : "LinkedIn DM" | "LinkedIn InMail" | "Email"
                            | "Cold Call" | "Twitter/X DM"
  channel_confidence      : float 0–1
  tone                    : "Formal" | "Casual" | "Value-Led" | ...
  tone_confidence         : float 0–1
  top_channel_features    : list[str]   (raw feature names)
  channel_probabilities   : dict
  tone_probabilities      : dict
  strategic_rationale     : str
  contradiction_alert     : bool

This module handles:
  1. Channel name normalisation  (ML labels → frontend icon keys)
  2. Confidence humanisation     (float → capped int %)
  3. Factor generation           (ML features + signal_log → plain English)
  4. History record assembly
"""

from datetime import datetime
from typing import Optional


# ── Channel normalisation ─────────────────────────────────────────────────────
# Maps ML model channel labels → frontend channel keys.
# Frontend only has icons for "LinkedIn", "Email", "Phone".
# "Twitter/X" will gracefully fall back to the Mail icon via StrategyCard.tsx.

CHANNEL_NORMALISE = {
    "LinkedIn DM":    "LinkedIn",
    "LinkedIn InMail": "LinkedIn",
    "Email":          "Email",
    "Cold Call":      "Phone",
    "Twitter/X DM":   "Twitter/X",
}

# ── Human-readable rationale by channel & tone ────────────────────────────────

CHANNEL_FACTOR = {
    "LinkedIn DM": (
        "LinkedIn DM recommended: high platform activity and mutual connections "
        "signal warm receptivity on this channel."
    ),
    "LinkedIn InMail": (
        "LinkedIn InMail recommended: C-Suite or low-accessibility profile — "
        "InMail bypasses connection limits and signals deliberate intent."
    ),
    "Email":   "Email recommended: prospect is less active on social; async email suits their workflow.",
    "Cold Call": (
        "Direct call recommended: low digital engagement across all channels — "
        "a live conversation is the highest-probability breakthrough."
    ),
    "Twitter/X DM": (
        "Twitter/X DM recommended: recent news or trending context creates a "
        "timely, topical hook for a public-platform approach."
    ),
}

TONE_FACTOR = {
    "Formal":        "Use a Formal tone: seniority level demands a structured, professional opener.",
    "Casual":        "Use a Casual tone: high engagement + tech context make warmth and brevity most effective.",
    "Value-Led":     "Use a Value-Led tone: lead with clear ROI framing and a specific outcome hook.",
    "Curiosity-Led": "Use a Curiosity-Led tone: low prior engagement — open a knowledge loop to re-spark interest.",
    "Direct":        "Use a Direct tone: decision-maker with positive context — skip preamble, lead with the offer.",
}

SIGNAL_FACTOR_TEMPLATES = {
    "engagement":    {
        "high":   "Engagement score is high ({val:.0%}) — prospect shows consistent activity signals.",
        "medium": "Engagement score is moderate ({val:.0%}) — approach with a value-first hook.",
        "low":    "Engagement score is low ({val:.0%}) — personalised re-engagement strategy needed.",
    },
    "linkedin":  {
        "high":   "High LinkedIn activity ({val:.0%}) — platform is actively monitored.",
        "medium": "Moderate LinkedIn activity ({val:.0%}) — message may have short visibility window.",
        "low":    "Low LinkedIn activity ({val:.0%}) — LinkedIn may not be the primary communication channel.",
    },
    "sentiment": {
        "positive": "Positive news signal detected ({val:+.2f}) — timely context strengthens outreach hook.",
        "neutral":  "Neutral news environment ({val:+.2f}) — lead with prospect-specific value.",
        "negative": "Challenging news context ({val:+.2f}) — approach with empathy and problem-solving framing.",
    },
    "recency":   {
        "fresh":  "Recent interaction ({val}d ago) — relationship is warm and timely.",
        "medium": "Last interaction {val} days ago — a light re-engagement opener is appropriate.",
        "stale":  "No recent contact ({val}d) — cold outreach framing with clear value proposition required.",
    },
    "mutual":    {
        "warm":   "{val} mutual connection(s) — leverage shared network for a warm introduction.",
        "cold":   "No mutual connections — cold outreach; credibility must be established quickly.",
    },
    "response_rate": {
        "high":   "Strong historical response rate ({val:.0%}) — prospect is reachable.",
        "low":    "Low historical response rate ({val:.0%}) — message must earn attention in the first line.",
    },
}


def build_strategy_response(
    contact_name: str,
    ml_card: dict,
    signal_log: dict,
) -> dict:
    """
    Assemble the final POST /api/strategy response body.

    Parameters
    ----------
    contact_name : str      From the original form submission.
    ml_card      : dict     Raw output from OutreachDecisionEngine.predict().
    signal_log   : dict     From signal_extractor.extract_signals()["signal_log"].

    Returns
    -------
    dict matching { channel, confidence, contactName, factors[] }
    """
    raw_channel = ml_card["channel"]
    raw_tone    = ml_card["tone"]
    ch_conf     = ml_card["channel_confidence"]
    tn_conf     = ml_card["tone_confidence"]

    channel    = CHANNEL_NORMALISE.get(raw_channel, raw_channel)
    confidence = _humanise_confidence(ch_conf, tn_conf)

    factors = _build_factors(raw_channel, raw_tone, signal_log, ml_card)

    return {
        "channel":      channel,
        "confidence":   confidence,
        "contactName":  contact_name,
        "factors":      factors,
        # Extra metadata (frontend can safely ignore, useful for debugging)
        "_meta": {
            "raw_channel":          raw_channel,
            "raw_tone":             raw_tone,
            "channel_confidence":   round(ch_conf, 4),
            "tone_confidence":      round(tn_conf, 4),
            "contradiction_alert":  ml_card.get("contradiction_alert", False),
            "channel_probabilities": ml_card.get("channel_probabilities", {}),
            "tone_probabilities":    ml_card.get("tone_probabilities", {}),
        },
    }


def build_history_record(
    request_data: dict,
    response_data: dict,
    record_id: int,
) -> dict:
    """
    Build a HistoryItem matching the frontend's History.tsx interface.

    interface HistoryItem {
      id: number;
      contact: string;
      role: string;
      channel: string;
      confidence: number;
      date: string;
      status: string;
    }
    """
    now    = datetime.now()
    today  = now.date()

    # Human-friendly date string
    created_at = datetime.fromisoformat(response_data.get("created_at", now.isoformat()))
    if created_at.date() == today:
        date_str = f"Today, {created_at.strftime('%I:%M %p')}"
    elif (today - created_at.date()).days == 1:
        date_str = f"Yesterday, {created_at.strftime('%I:%M %p')}"
    else:
        date_str = created_at.strftime("%b %d, %I:%M %p")

    return {
        "id":         record_id,
        "contact":    request_data.get("name", "Unknown"),
        "role":       request_data.get("role", ""),
        "channel":    response_data.get("channel", "Email"),
        "confidence": response_data.get("confidence", 0),
        "date":       date_str,
        "status":     "Sent",
    }


# ── Factor generation helpers ─────────────────────────────────────────────────

def _humanise_confidence(ch_conf: float, tn_conf: float) -> int:
    """
    Blend channel + tone confidence into a single 0-100 integer.
    Applies a slight regression toward the mean to avoid unrealistic 99%s
    when the model is very certain on one dimension.
    """
    blended = (ch_conf * 0.65) + (tn_conf * 0.35)      # channel is primary signal
    humanised = int(round(blended * 100))
    return max(45, min(97, humanised))                  # clamp: feels realistic


def _build_factors(
    channel: str,
    tone: str,
    signal_log: dict,
    ml_card: dict,
) -> list[str]:
    """
    Produce ≤6 plain-English factor strings.
    Order: channel reason → tone reason → top signal insights.
    """
    factors: list[str] = []

    # 1. Channel rationale
    if channel in CHANNEL_FACTOR:
        factors.append(CHANNEL_FACTOR[channel])

    # 2. Tone rationale
    if tone in TONE_FACTOR:
        factors.append(TONE_FACTOR[tone])

    # 3. Signal-derived insights (pick the most informative ones)
    eng   = signal_log.get("engagement",    (0.5, ""))[0]
    li    = signal_log.get("linkedin",      (0.5, ""))[0]
    sent  = signal_log.get("sentiment",     (0.0, ""))[0]
    days  = signal_log.get("recency",       (14,  ""))[0]
    mutu  = signal_log.get("mutual",        (3,   ""))[0]
    resp  = signal_log.get("response_rate", (0.3, ""))[0]

    tmpl = SIGNAL_FACTOR_TEMPLATES

    # Engagement
    tier = "high" if eng > 0.6 else ("low" if eng < 0.35 else "medium")
    factors.append(tmpl["engagement"][tier].format(val=eng))

    # LinkedIn — only if it meaningfully steers the recommendation
    if channel in ("LinkedIn DM", "LinkedIn InMail"):
        tier = "high" if li > 0.6 else ("low" if li < 0.35 else "medium")
        factors.append(tmpl["linkedin"][tier].format(val=li))

    # Sentiment — only if non-neutral
    if abs(sent) > 0.2:
        tier = "positive" if sent > 0 else "negative"
        factors.append(tmpl["sentiment"][tier].format(val=sent))

    # Recency
    tier = "fresh" if days <= 7 else ("stale" if days >= 30 else "medium")
    factors.append(tmpl["recency"][tier].format(val=days))

    # Mutual connections — only if informative
    if mutu >= 5:
        factors.append(tmpl["mutual"]["warm"].format(val=mutu))
    elif mutu == 0:
        factors.append(tmpl["mutual"]["cold"].format(val=mutu))

    # Response rate — only if strongly high or low
    if resp > 0.55 or resp < 0.15:
        tier = "high" if resp >= 0.55 else "low"
        factors.append(tmpl["response_rate"][tier].format(val=resp))

    # Contradiction alert
    if ml_card.get("contradiction_alert"):
        factors.append(
            "⚠ Note: Tone may feel informal for this seniority level — "
            "consider a more structured opener."
        )

    return factors[:6]          # cap at 6 to keep the UI clean
