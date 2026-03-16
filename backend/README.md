# NeuroStrat Backend

FastAPI server that connects the NeuroStrat React frontend to the AI Outreach Decision Engine ML model.

---

## Directory Structure

```
project/
├── outreach_engine/          ← ML model (existing)
│   ├── models/
│   │   ├── best_best_channel_model.joblib
│   │   └── best_tone_model.joblib
│   ├── inference.py
│   ├── feature_pipeline.py
│   └── ...
│
└── backend/                  ← This folder
    ├── app.py                ← FastAPI app, all routes
    ├── signal_extractor.py   ← Free-text → ML feature vector
    ├── response_builder.py   ← ML output → frontend JSON shape
    ├── history_store.py      ← SQLite persistence
    ├── FRONTEND_INTEGRATION.js   ← Code changes needed in the frontend
    ├── requirements.txt
    └── README.md
```

---

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn app:app --reload --port 8000
```

The server will:
- Auto-load the ML models from `../outreach_engine/models/`
- Initialise the SQLite database (`neurostrat_history.db`) on first run
- Be available at `http://localhost:8000`

### 3. Verify it's running

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","model_loaded":true}
```

---

## Frontend Integration

Open **`src/pages/Index.tsx`** and make two changes:

### Change 1 — Remove the mock

Delete the `mockResult` constant (lines ~9–16).

### Change 2 — Replace `handleGenerate`

```tsx
const handleGenerate = async (data: { name: string; role: string; context: string }) => {
  setIsLoading(true);
  setResult(null);

  try {
    const res = await fetch("http://localhost:8000/api/strategy", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? "Strategy generation failed");
    }

    const json = await res.json();
    setResult(json);
  } catch (error) {
    console.error("[NeuroStrat] Strategy API error:", error);
  } finally {
    setIsLoading(false);
  }
};
```

### Change 3 — Update the state type

Replace:
```tsx
const [result, setResult] = useState<typeof mockResult | null>(null);
```
With:
```tsx
interface StrategyResult {
  channel:     string;
  confidence:  number;
  contactName: string;
  factors:     string[];
}
const [result, setResult] = useState<StrategyResult | null>(null);
```

### Change 4 — Wire up History.tsx

Replace the static `historyItems` array with:

```tsx
import { useState, useEffect } from "react";

const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
const [loadingHistory, setLoadingHistory] = useState(true);

useEffect(() => {
  fetch("http://localhost:8000/api/history")
    .then(r => r.json())
    .then(data => setHistoryItems(data))
    .catch(err => console.error("[NeuroStrat] History error:", err))
    .finally(() => setLoadingHistory(false));
}, []);
```

---

## API Reference

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/api/health` | — | `{ status, model_loaded }` |
| `POST` | `/api/strategy` | `{ name, role, context }` | `{ channel, confidence, contactName, factors[] }` |
| `GET` | `/api/history` | `?limit=50&offset=0` | `HistoryItem[]` |
| `GET` | `/api/decision/{id}` | — | Full decision record |
| `GET` | `/api/stats` | — | `{ total_decisions, avg_confidence, channel_distribution }` |

### POST /api/strategy — full response shape

```json
{
  "channel": "LinkedIn",
  "confidence": 83,
  "contactName": "Sarah Chen",
  "factors": [
    "LinkedIn DM recommended: high platform activity and mutual connections signal warm receptivity.",
    "Use a Value-Led tone: lead with clear ROI framing and a specific outcome hook.",
    "Engagement score is high (75%) — prospect shows consistent activity signals.",
    "High LinkedIn activity (100%) — platform is actively monitored.",
    "Positive news signal detected (+0.80) — timely context strengthens outreach hook.",
    "Recent interaction (5d ago) — relationship is warm and timely."
  ],
  "_meta": {
    "raw_channel": "Twitter/X DM",
    "raw_tone": "Value-Led",
    "channel_confidence": 0.9987,
    "tone_confidence": 0.8102,
    "contradiction_alert": false,
    "channel_probabilities": { ... },
    "tone_probabilities": { ... }
  }
}
```

---

## How the Signal Extraction Works

The frontend sends free-text `{ name, role, context }`. The ML model needs 11 structured numerical and categorical features. `signal_extractor.py` bridges this gap:

| Input text | → | ML feature |
|---|---|---|
| "CEO", "Chief", "Founder" | → | `role = "C-Suite"` |
| "active on LinkedIn", "posts regularly" | → | `linkedin_active ↑ 0.40` |
| "just raised Series B" | → | `news_sentiment +0.45` |
| "just met", "this week" | → | `days_since_last = 2` |
| "referred by mutual connection" | → | `mutual_connections = 7` |
| "ghosted", "never replied" | → | `engagement_score ↓ 0.35` |
| "SaaS", "cloud", "platform" | → | `industry = "SaaS"` |
| "enterprise", "Fortune 500" | → | `company_size = "1000+"` |

---

## Interactive API Docs

With the server running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc
