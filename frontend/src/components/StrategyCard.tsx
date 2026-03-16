import { Mail, Linkedin, Phone, CheckCircle2 } from "lucide-react";

const channelIcons: Record<string, React.ReactNode> = {
  Email: <Mail size={18} strokeWidth={1.5} />,
  LinkedIn: <Linkedin size={18} strokeWidth={1.5} />,
  Phone: <Phone size={18} strokeWidth={1.5} />,
};

interface StrategyCardProps {
  channel: string;
  confidence: number;
  factors: string[];
  contactName: string;
}

export function StrategyCard({ channel, confidence, factors, contactName }: StrategyCardProps) {
  return (
    <div className="bg-card border neon-border rounded-md p-6 animate-fade-in neon-glow">
      <h2 className="font-display text-sm font-semibold text-foreground tracking-wide uppercase mb-5 neon-text">
        Strategy Recommendation
      </h2>

      {/* Contact */}
      <p className="text-xs text-muted-foreground mb-4">
        Analysis for <span className="font-medium text-primary">{contactName}</span>
      </p>

      {/* Chosen Channel */}
      <div className="flex items-center gap-3 mb-5">
        <div className="flex items-center justify-center w-9 h-9 rounded bg-primary/15 text-primary neon-glow">
          {channelIcons[channel] || <Mail size={18} />}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Recommended Channel</p>
          <p className="text-base font-display font-semibold text-foreground">{channel}</p>
        </div>
      </div>

      {/* Confidence Score */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-xs text-muted-foreground">Confidence Score</p>
          <p className="text-sm font-display font-bold text-accent neon-text">{confidence}%</p>
        </div>
        <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${confidence}%`,
              background: "linear-gradient(90deg, hsl(195 100% 50%), hsl(170 100% 45%))",
              boxShadow: "0 0 8px rgba(0, 200, 255, 0.5)",
            }}
          />
        </div>
      </div>

      {/* Factors */}
      <div>
        <p className="text-xs text-muted-foreground mb-2">Top Influencing Factors</p>
        <ul className="space-y-1.5">
          {factors.map((factor, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground">
              <CheckCircle2 size={14} className="text-accent mt-0.5 shrink-0" />
              <span>{factor}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
