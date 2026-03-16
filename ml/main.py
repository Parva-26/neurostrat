"""
main.py
-------
Orchestration script — run this to execute the full pipeline:
  1. Generate synthetic dataset
  2. Train & evaluate all models
  3. Run inference demo on sample prospects
  4. Print a summary dashboard to terminal
"""

import os, sys, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import generate_dataset
from train_evaluate import train_and_evaluate
from inference      import OutreachDecisionEngine


def print_banner():
    banner = r"""
  ███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗ ███████╗████████╗██████╗  █████╗ ████████╗
  ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝
  ██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║███████╗   ██║   ██████╔╝███████║   ██║
  ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║╚════██║   ██║   ██╔══██╗██╔══██║   ██║
  ██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   ██║  ██║██║  ██║   ██║
  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝

  AI OUTREACH DECISION ENGINE  |  Team: Heisenbug  |  LOC 8.0
    """
    print(banner)


def main():
    print_banner()

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print("► Step 1/3 — Generating dataset (3,000 synthetic outreach cases) ...")
    df = generate_dataset(n_samples=3000)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/outreach_dataset.csv", index=False)
    print(f"  Dataset: {df.shape[0]} rows × {df.shape[1]} cols")

    # ── 2. Train ──────────────────────────────────────────────────────────────
    print("\n► Step 2/3 — Training models ...")
    train_and_evaluate(df)

    # ── 3. Inference demo ─────────────────────────────────────────────────────
    print("\n► Step 3/3 — Running inference on sample prospects ...")
    engine = OutreachDecisionEngine()

    prospects = [
        {
            "role": "C-Suite", "industry": "FinTech", "company_size": "1000+",
            "engagement_score": 0.72, "linkedin_active": 0.85,
            "news_sentiment": 0.60, "time_of_day": 9,
            "days_since_last": 3,  "past_response_rate": 0.45,
            "profile_completeness": 0.90, "mutual_connections": 8,
        },
        {
            "role": "VP", "industry": "SaaS", "company_size": "201-1000",
            "engagement_score": 0.55, "linkedin_active": 0.65,
            "news_sentiment": 0.30, "time_of_day": 14,
            "days_since_last": 10, "past_response_rate": 0.30,
            "profile_completeness": 0.80, "mutual_connections": 5,
        },
        {
            "role": "Manager", "industry": "E-Commerce", "company_size": "51-200",
            "engagement_score": 0.25, "linkedin_active": 0.28,
            "news_sentiment": -0.20, "time_of_day": 16,
            "days_since_last": 35, "past_response_rate": 0.10,
            "profile_completeness": 0.50, "mutual_connections": 1,
        },
    ]

    print("\n" + "═" * 70)
    print("  STRATEGY CARDS")
    print("═" * 70)

    for i, p in enumerate(prospects, 1):
        card = engine.predict(p)
        alert = " ⚠ CONTRADICTION" if card["contradiction_alert"] else ""
        print(f"""
  ┌─ Prospect #{i}: {p['role']} @ {p['industry']} ({p['company_size']}) ─{'─'*10}
  │  Channel : {card['channel']:<22} ({card['channel_confidence']*100:.1f}% confidence)
  │  Tone    : {card['tone']:<22} ({card['tone_confidence']*100:.1f}% confidence){alert}
  │  Rationale: {card['strategic_rationale'][:110]}...
  │  Top channel signals: {', '.join(card['top_channel_features'][:3])}
  └{'─'*65}""")

    print("\n  All results saved to results/  |  Models saved to models/")
    print("  Run `python inference.py` for full JSON strategy cards.\n")


if __name__ == "__main__":
    main()
