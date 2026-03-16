"""
data_generator.py
-----------------
Generates a realistic synthetic dataset of B2B outreach cases.
Mimics real-world signal distributions: engagement decay, role-based
response rates, time-of-day patterns, and news sentiment effects.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

np.random.seed(42)

# ── Constants ────────────────────────────────────────────────────────────────
ROLES = ["C-Suite", "VP", "Director", "Manager", "Individual Contributor"]
INDUSTRIES = ["SaaS", "FinTech", "HealthTech", "E-Commerce", "Manufacturing", "Consulting"]
CHANNELS = ["LinkedIn DM", "Email", "LinkedIn InMail", "Cold Call", "Twitter/X DM"]
TONES = ["Formal", "Casual", "Value-Led", "Curiosity-Led", "Direct"]
COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"]


def _channel_label(row: dict) -> str:
    """
    Deterministic channel assignment based on domain knowledge:
    - C-Suite → InMail (gated, signals exclusivity)
    - High engagement + SaaS → LinkedIn DM
    - Low engagement + large company → Email
    - Positive news sentiment → Twitter/X (topical hook)
    - Default fallback logic
    """
    role, eng, news, size, active = (
        row["role"], row["engagement_score"],
        row["news_sentiment"], row["company_size_code"],
        row["linkedin_active"]
    )

    if role == 0 and eng > 0.6:          # C-Suite, active
        return "LinkedIn InMail"
    if role == 0 and eng <= 0.6:         # C-Suite, passive
        return "Email"
    if news > 0.5 and active > 0.7:      # trending news + active
        return "Twitter/X DM"
    if eng > 0.65 and active > 0.5:      # high engagement
        return "LinkedIn DM"
    if size >= 3:                         # large company
        return "Email"
    if eng < 0.3 and active < 0.3:       # hard-to-reach
        return "Cold Call"
    return "LinkedIn DM"


def _tone_label(row: dict) -> str:
    """
    Tone selected by role + context:
    - C-Suite → Formal or Direct
    - Positive sentiment + tech industry → Casual
    - Low engagement → Curiosity-Led (re-engage hook)
    - Mid-funnel signals → Value-Led
    """
    role, eng, industry, sentiment = (
        row["role"], row["engagement_score"],
        row["industry_code"], row["news_sentiment"]
    )

    if role == 0:
        return "Formal" if sentiment < 0 else "Direct"
    if role == 1:
        return "Value-Led"
    if eng < 0.35:
        return "Curiosity-Led"
    if industry in [0, 1] and sentiment > 0.3:   # SaaS / FinTech
        return "Casual"
    return "Value-Led"


def generate_dataset(n_samples: int = 3000) -> pd.DataFrame:
    """
    Produce n_samples rows of synthetic outreach cases.
    Injects ≈8% noise to prevent perfect separability.
    """
    roles       = np.random.choice(len(ROLES),      n_samples, p=[0.08, 0.15, 0.22, 0.30, 0.25])
    industries  = np.random.choice(len(INDUSTRIES), n_samples)
    comp_sizes  = np.random.choice(len(COMPANY_SIZES), n_samples, p=[0.15, 0.25, 0.30, 0.20, 0.10])

    # Engagement score: C-Suite naturally lower (harder to reach)
    base_eng    = np.random.beta(2, 3, n_samples)
    role_penalty = np.array([0.25, 0.10, 0.05, 0.0, -0.05])[roles]
    engagement  = np.clip(base_eng - role_penalty + np.random.normal(0, 0.05, n_samples), 0, 1)

    # LinkedIn activity score
    linkedin_active = np.random.beta(3, 2, n_samples)
    linkedin_active += np.random.normal(0, 0.07, n_samples)
    linkedin_active  = np.clip(linkedin_active, 0, 1)

    # News sentiment: real-valued [-1, 1]
    news_sentiment  = np.random.uniform(-1, 1, n_samples)

    # Time of day: 0-23 hour bucket
    time_of_day     = np.random.choice(24, n_samples)

    # Days since last interaction
    days_since_last = np.random.exponential(scale=14, size=n_samples).astype(int)
    days_since_last = np.clip(days_since_last, 0, 90)

    # Past response rate (0-1)
    past_response   = np.random.beta(2, 5, n_samples)

    # Profile completeness (0-1)
    profile_complete = np.random.beta(5, 2, n_samples)

    # Mutual connections (0-50)
    mutual_connections = np.random.poisson(lam=5, size=n_samples)

    # Build raw dict for label generation
    raw = {
        "role": roles,
        "engagement_score": engagement,
        "linkedin_active": linkedin_active,
        "news_sentiment": news_sentiment,
        "company_size_code": comp_sizes,
        "industry_code": industries,
    }

    # Generate labels with ≈8% noise injection
    channels, tones = [], []
    for i in range(n_samples):
        row = {k: v[i] for k, v in raw.items()}
        ch  = _channel_label(row)
        to  = _tone_label(row)
        # Random noise
        if np.random.random() < 0.08:
            ch = np.random.choice(CHANNELS)
        if np.random.random() < 0.08:
            to = np.random.choice(TONES)
        channels.append(ch)
        tones.append(to)

    df = pd.DataFrame({
        # Raw features
        "engagement_score":    engagement,
        "linkedin_active":     linkedin_active,
        "news_sentiment":      news_sentiment,
        "time_of_day":         time_of_day,
        "days_since_last":     days_since_last,
        "past_response_rate":  past_response,
        "profile_completeness": profile_complete,
        "mutual_connections":  mutual_connections,
        # Categorical (raw strings for preprocessing)
        "role":                [ROLES[r]       for r in roles],
        "industry":            [INDUSTRIES[i]  for i in industries],
        "company_size":        [COMPANY_SIZES[c] for c in comp_sizes],
        # Targets
        "best_channel":        channels,
        "tone":                tones,
    })

    return df


if __name__ == "__main__":
    df = generate_dataset(3000)
    df.to_csv("data/outreach_dataset.csv", index=False)
    print(f"Dataset saved → {df.shape[0]} rows × {df.shape[1]} cols")
    print("\nChannel distribution:\n", df["best_channel"].value_counts())
    print("\nTone distribution:\n",    df["tone"].value_counts())
