"""
inference.py
────────────
Production inference module for the AI Outreach Decision Engine.

Loads saved .joblib artefacts and returns a full Strategy Card for any
prospect dict — channel recommendation, tone recommendation, per-class
probability distributions, top influencing features, contradiction alert,
and human-readable strategic rationale.

Quick start
-----------
    python inference.py                    # runs built-in demo
    ──────────────────────────────────────
    from inference import OutreachDecisionEngine
    engine = OutreachDecisionEngine()
    card   = engine.predict(prospect_dict)
    print(card)
"""

import os, json
import numpy as np
import pandas as pd
import joblib
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR       = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR  = os.path.join(_DIR, "models")

# ── Static rationale library ──────────────────────────────────────────────────
_CH_RATIONALE = {
    "LinkedIn DM":
        "High LinkedIn activity and mutual connections signal warm receptivity "
        "to a direct, conversational message.",
    "LinkedIn InMail":
        "C-Suite or low-accessibility profile; InMail bypasses connection limits "
        "and signals deliberate, high-value intent.",
    "Email":
        "Prospect is less digitally active on social; asynchronous email respects "
        "their workflow and allows thoughtful engagement.",
    "Cold Call":
        "Low engagement across all digital channels — a live, synchronous "
        "conversation is the highest-probability breakthrough.",
    "Twitter/X DM":
        "Strong news sentiment and active social presence create a timely, "
        "topical hook for a public-platform approach.",
}

_TN_RATIONALE = {
    "Formal":
        "Seniority level and neutral/negative sentiment context demand a "
        "structured, professionally framed opener.",
    "Casual":
        "High engagement score and tech-industry context make warmth and "
        "brevity more effective than formal language.",
    "Value-Led":
        "Mid-funnel signals suggest the prospect needs clear ROI framing and "
        "a tangible hook before committing attention.",
    "Curiosity-Led":
        "Low engagement history — open a knowledge loop or insight-led question "
        "to re-spark interest without a hard pitch.",
    "Direct":
        "Decision-maker with positive news context; skip preamble, lead with "
        "the offer, and respect their time.",
}

# ── Default prospect values ───────────────────────────────────────────────────
_DEFAULTS = {
    "engagement_score":     0.50,
    "linkedin_active":      0.50,
    "news_sentiment":       0.00,
    "time_of_day":          10,
    "days_since_last":      7,
    "past_response_rate":   0.30,
    "profile_completeness": 0.70,
    "mutual_connections":   3,
    "role":                 "Manager",
    "industry":             "SaaS",
    "company_size":         "51-200",
}


class OutreachDecisionEngine:
    """
    Wraps both the channel and tone prediction pipelines.
    A single .predict() call returns a complete Strategy Card.

    Parameters
    ----------
    model_dir : str
        Directory containing best_*_model.joblib artefacts.
    """

    def __init__(self, model_dir: str = MODEL_DIR):
        self._ch = joblib.load(os.path.join(model_dir, "best_channel_model.joblib"))
        self._tn = joblib.load(os.path.join(model_dir, "best_tone_model.joblib"))
        print("[OutreachDecisionEngine] Models loaded ✓")

    # ── Public API ────────────────────────────────────────────────────────────
    def predict(self, prospect: dict, top_n: int = 5) -> dict:
        """
        Returns a Strategy Card dict:

        {
          channel                : str,
          channel_confidence     : float (0–1),
          tone                   : str,
          tone_confidence        : float (0–1),
          strategic_rationale    : str,
          top_channel_features   : list[str],
          top_tone_features      : list[str],
          contradiction_alert    : bool,
          channel_probabilities  : dict[str, float],
          tone_probabilities     : dict[str, float],
        }
        """
        X = self._to_df(prospect)

        ch_pipe, ch_le = self._ch["pipeline"], self._ch["label_encoder"]
        tn_pipe, tn_le = self._tn["pipeline"], self._tn["label_encoder"]

        ch_proba = ch_pipe.predict_proba(X)[0]
        tn_proba = tn_pipe.predict_proba(X)[0]

        channel  = ch_le.classes_[int(np.argmax(ch_proba))]
        tone     = tn_le.classes_[int(np.argmax(tn_proba))]
        ch_conf  = float(np.max(ch_proba))
        tn_conf  = float(np.max(tn_proba))

        # Contradiction: senior role getting Casual tone
        contradiction = (
            prospect.get("role", "") in ("C-Suite", "VP") and tone == "Casual"
        )

        rationale = (
            f"Recommended channel: {channel} ({ch_conf*100:.1f}% confidence). "
            f"{_CH_RATIONALE.get(channel, '')}  |  "
            f"Recommended tone: {tone} ({tn_conf*100:.1f}% confidence). "
            f"{_TN_RATIONALE.get(tone, '')}"
        )
        if contradiction:
            rationale += (
                "  ⚠ CONTRADICTION ALERT: 'Casual' tone is atypical for this "
                "seniority — review before sending."
            )

        return {
            "channel":               channel,
            "channel_confidence":    round(ch_conf, 4),
            "tone":                  tone,
            "tone_confidence":       round(tn_conf, 4),
            "strategic_rationale":   rationale,
            "top_channel_features":  _top_features(ch_pipe, top_n),
            "top_tone_features":     _top_features(tn_pipe, top_n),
            "contradiction_alert":   contradiction,
            "channel_probabilities": {
                c: round(float(p), 4)
                for c, p in zip(ch_le.classes_, ch_proba)
            },
            "tone_probabilities": {
                c: round(float(p), 4)
                for c, p in zip(tn_le.classes_, tn_proba)
            },
        }

    def batch_predict(self, prospects: list) -> list:
        """Predict for a list of prospect dicts."""
        return [self.predict(p) for p in prospects]

    # ── Internal ──────────────────────────────────────────────────────────────
    def _to_df(self, prospect: dict) -> pd.DataFrame:
        row       = {**_DEFAULTS, **prospect}
        feat_cols = self._ch["feature_cols"]
        return pd.DataFrame([row])[feat_cols]


# ── Feature importance helper (module-level) ──────────────────────────────────
def _top_features(pipe, n: int = 5) -> list:
    try:
        clf = pipe.named_steps["clf"]
        imp = clf.feature_importances_
        try:
            names = pipe.named_steps["pre"].get_feature_names_out().tolist()
        except Exception:
            try:
                names = pipe.named_steps["preprocessor"].get_feature_names_out().tolist()
            except Exception:
                names = [f"f{i}" for i in range(len(imp))]
        top_idx = np.argsort(imp)[::-1][:n]
        return [
            f"{names[i].split('__')[-1]} ({imp[i]:.4f})"
            for i in top_idx
        ]
    except Exception:
        return []


# ── CLI demo ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = OutreachDecisionEngine()

    sample_prospects = [
        {   # High-value C-Suite target, active on LinkedIn, positive news
            "role": "C-Suite", "industry": "FinTech", "company_size": "1000+",
            "engagement_score": 0.72, "linkedin_active": 0.85,
            "news_sentiment": 0.60,   "time_of_day": 9,
            "days_since_last": 3,     "past_response_rate": 0.45,
            "profile_completeness": 0.90, "mutual_connections": 8,
        },
        {   # Mid-level VP, warm but not yet engaged
            "role": "VP", "industry": "SaaS", "company_size": "201-1000",
            "engagement_score": 0.55, "linkedin_active": 0.65,
            "news_sentiment": 0.30,   "time_of_day": 14,
            "days_since_last": 10,    "past_response_rate": 0.30,
            "profile_completeness": 0.80, "mutual_connections": 5,
        },
        {   # Cold, disengaged manager — re-engagement scenario
            "role": "Manager", "industry": "E-Commerce", "company_size": "51-200",
            "engagement_score": 0.25, "linkedin_active": 0.28,
            "news_sentiment": -0.20,  "time_of_day": 16,
            "days_since_last": 35,    "past_response_rate": 0.10,
            "profile_completeness": 0.50, "mutual_connections": 1,
        },
        {   # Individual contributor, highly active, strong sentiment signal
            "role": "Individual Contributor", "industry": "HealthTech",
            "company_size": "11-50",
            "engagement_score": 0.68, "linkedin_active": 0.72,
            "news_sentiment": 0.75,   "time_of_day": 10,
            "days_since_last": 5,     "past_response_rate": 0.55,
            "profile_completeness": 0.88, "mutual_connections": 12,
        },
    ]

    print("\n" + "═" * 72)
    print("  STRATEGY CARDS  —  AI Outreach Decision Engine")
    print("═" * 72)

    for i, p in enumerate(sample_prospects, 1):
        card    = engine.predict(p)
        alert   = "  ⚠ CONTRADICTION" if card["contradiction_alert"] else ""
        ch_bar  = " | ".join(f"{k}: {v*100:.0f}%" for k, v in card["channel_probabilities"].items())
        tn_bar  = " | ".join(f"{k}: {v*100:.0f}%" for k, v in card["tone_probabilities"].items())

        print(f"""
┌─ Prospect #{i}: {p['role']} @ {p['industry']} ({p['company_size']}) {'─'*10}
│  Channel : {card['channel']:<22} ({card['channel_confidence']*100:.1f}% conf){alert}
│  Tone    : {card['tone']:<22} ({card['tone_confidence']*100:.1f}% conf)
│  Top signals : {' | '.join(card['top_channel_features'][:3])}
│
│  Channel probs  → {ch_bar}
│  Tone probs     → {tn_bar}
│
│  Rationale:
│    {card['strategic_rationale'][:110]}
└{'─'*69}""")

    print("\n  Full JSON for Prospect #1:")
    print(json.dumps(engine.predict(sample_prospects[0]), indent=2))
