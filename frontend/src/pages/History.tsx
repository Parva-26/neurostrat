import { Linkedin, Mail, Phone, CheckCircle2, Clock, Filter } from "lucide-react";
import { useState, useEffect } from "react";

interface HistoryItem {
  id: number;
  contact: string;
  role: string;
  channel: string;
  confidence: number;
  date: string;
  status: "Sent" | "Pending" | "Draft";
}

const channelIcons: Record<string, React.ReactNode> = {
  LinkedIn: <Linkedin size={14} strokeWidth={1.5} />,
  Email: <Mail size={14} strokeWidth={1.5} />,
  Phone: <Phone size={14} strokeWidth={1.5} />,
};

const statusColors: Record<string, string> = {
  Sent: "text-accent border-accent/30 bg-accent/10",
  Pending: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  Draft: "text-muted-foreground border-border bg-muted/40",
};

const History = () => {
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/history`)
      .then(r => r.json())
      .then(data => setHistoryItems(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="flex-1 flex flex-col tron-grid-bg">
      {/* Header */}
      <header className="h-12 flex items-center border-b border-border/60 px-6 backdrop-blur-sm bg-background/80">
        <h1 className="font-display text-sm font-semibold text-foreground neon-text">NeuroStrat</h1>
        <span className="ml-2 text-xs text-muted-foreground font-body">/ History</span>
      </header>

      <div className="flex-1 flex justify-center py-10 px-6">
        <div className="w-full max-w-2xl space-y-5">

          {/* Toolbar */}
          <div className="flex items-center justify-between animate-fade-in">
            <h2 className="font-display text-sm font-semibold text-foreground tracking-wide uppercase neon-text">
              Outreach History
            </h2>
            <button className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-medium border neon-border text-primary hover:bg-primary/10 transition-all duration-200">
              <Filter size={12} />
              Filter
            </button>
          </div>

          {/* History List */}
          <div className="space-y-3 animate-fade-in">
            {historyItems.map((item) => (
              <div
                key={item.id}
                className="bg-card border neon-border rounded-md p-4 neon-glow hover:neon-glow-strong transition-all duration-200 cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-display text-sm font-semibold text-foreground group-hover:text-primary transition-colors duration-200">
                        {item.contact}
                      </span>
                      <span
                        className={`inline-flex items-center text-xs border rounded px-1.5 py-0.5 font-medium ${statusColors[item.status]}`}
                      >
                        {item.status === "Sent" && <CheckCircle2 size={10} className="mr-1" />}
                        {item.status === "Pending" && <Clock size={10} className="mr-1" />}
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground font-body">{item.role}</p>
                  </div>

                  {/* Right: meta */}
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    {/* Channel pill */}
                    <div className="flex items-center gap-1.5 text-xs text-primary bg-primary/10 border border-primary/20 rounded px-2 py-0.5">
                      {channelIcons[item.channel]}
                      {item.channel}
                    </div>
                    <p className="text-xs text-muted-foreground">{item.date}</p>
                  </div>
                </div>

                {/* Confidence bar */}
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${item.confidence}%`,
                        background: "linear-gradient(90deg, hsl(185 100% 55%), hsl(165 100% 50%))",
                        boxShadow: "0 0 6px rgba(0,229,255,0.4)",
                      }}
                    />
                  </div>
                  <span className="text-xs font-display font-bold text-accent tabular-nums w-8 text-right">
                    {item.confidence}%
                  </span>
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
};

export default History;
