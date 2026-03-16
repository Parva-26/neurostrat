// ─────────────────────────────────────────────────────────────────────────────
// FRONTEND INTEGRATION PATCH
// File: src/pages/Index.tsx
//
// Replace the entire handleGenerate function and the mockResult constant
// with the code below.  Everything else in Index.tsx stays the same.
// ─────────────────────────────────────────────────────────────────────────────

// ── 1. Remove this block entirely ────────────────────────────────────────────
//
// const mockResult = { ... };          ← DELETE
//
// ─────────────────────────────────────────────────────────────────────────────


// ── 2. Replace handleGenerate with this ──────────────────────────────────────

const handleGenerate = async (data: { name: string; role: string; context: string }) => {
  setIsLoading(true);
  setResult(null);      // clear any previous result while loading

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
    // json shape: { channel, confidence, contactName, factors[] }
    setResult(json);

  } catch (error) {
    console.error("[NeuroStrat] Strategy API error:", error);
    // TODO: surface this via a toast / error state if desired
    //   e.g.  toast({ title: "Error", description: String(error) });
  } finally {
    setIsLoading(false);
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// Also update the state type at the top of Index.tsx.
// Replace:
//   const [result, setResult] = useState<typeof mockResult | null>(null);
// With:
//   const [result, setResult] = useState<StrategyResult | null>(null);
//
// And add this interface above the component (or in a types.ts file):
// ─────────────────────────────────────────────────────────────────────────────

interface StrategyResult {
  channel:     string;
  confidence:  number;
  contactName: string;
  factors:     string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// HISTORY PAGE PATCH
// File: src/pages/History.tsx
//
// Replace the static historyItems array with a live fetch:
// ─────────────────────────────────────────────────────────────────────────────

// ── 1. Add to imports ─────────────────────────────────────────────────────────
import { useState, useEffect } from "react";

// ── 2. Replace the hardcoded historyItems with this inside the component ──────

const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
const [loadingHistory, setLoadingHistory] = useState(true);

useEffect(() => {
  const fetchHistory = async () => {
    try {
      const res  = await fetch("http://localhost:8000/api/history");
      const data = await res.json();
      setHistoryItems(data);
    } catch (err) {
      console.error("[NeuroStrat] History fetch error:", err);
    } finally {
      setLoadingHistory(false);
    }
  };
  fetchHistory();
}, []);

// ── 3. Optional: show a loading state in the JSX ──────────────────────────────
// In the return, wrap the items list:
//
//   {loadingHistory ? (
//     <p className="text-sm text-muted-foreground">Loading history...</p>
//   ) : historyItems.length === 0 ? (
//     <p className="text-sm text-muted-foreground">No outreach history yet.</p>
//   ) : (
//     historyItems.map((item) => ( ... existing card JSX ... ))
//   )}
