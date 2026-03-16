import { User, Mail, Building2, MapPin, Edit3, Zap, TrendingUp, Send } from "lucide-react";

const stats = [
  { label: "Strategies Generated", value: "142", icon: Zap },
  { label: "Avg. Confidence Score", value: "84%", icon: TrendingUp },
  { label: "Outreaches Sent", value: "91", icon: Send },
];

const Profile = () => {
  return (
    <div className="flex-1 flex flex-col tron-grid-bg">
      {/* Header */}
      <header className="h-12 flex items-center border-b border-border/60 px-6 backdrop-blur-sm bg-background/80">
        <h1 className="font-display text-sm font-semibold text-foreground neon-text">NeuroStrat</h1>
        <span className="ml-2 text-xs text-muted-foreground font-body">/ Profile</span>
      </header>

      <div className="flex-1 flex justify-center py-10 px-6">
        <div className="w-full max-w-2xl space-y-5">

          {/* Profile Card */}
          <div className="bg-card border neon-border rounded-md p-6 neon-glow animate-fade-in">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                {/* Avatar */}
                <div className="w-16 h-16 rounded-xl bg-primary/15 border neon-border flex items-center justify-center neon-glow-strong shrink-0">
                  <User size={28} strokeWidth={1.5} className="text-primary" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold text-foreground neon-text">Alex Mercer</h2>
                  <p className="text-xs text-muted-foreground font-body mt-0.5">Senior Growth Strategist</p>
                  <span className="inline-flex items-center gap-1 mt-2 text-xs text-primary bg-primary/10 border border-primary/30 rounded px-2 py-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    Active
                  </span>
                </div>
              </div>
              <button className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-medium border neon-border text-primary hover:bg-primary/10 transition-all duration-200">
                <Edit3 size={12} />
                Edit
              </button>
            </div>

            {/* Info Fields */}
            <div className="space-y-3">
              {[
                { icon: Mail, label: "Email", value: "alex.mercer@neurostrat.ai" },
                { icon: Building2, label: "Company", value: "NeuroStrat Insights" },
                { icon: MapPin, label: "Location", value: "San Francisco, CA" },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex items-center gap-3 p-3 rounded bg-background/60 border border-border/40">
                  <Icon size={14} strokeWidth={1.5} className="text-muted-foreground shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-xs text-muted-foreground">{label}</span>
                    <span className="text-sm text-foreground font-body">{value}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 animate-fade-in">
            {stats.map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-card border neon-border rounded-md p-4 neon-glow text-center">
                <div className="flex items-center justify-center w-8 h-8 rounded bg-primary/15 text-primary mx-auto mb-3 neon-glow">
                  <Icon size={14} strokeWidth={1.5} />
                </div>
                <p className="font-display text-2xl font-bold text-primary neon-text">{value}</p>
                <p className="text-xs text-muted-foreground font-body mt-1">{label}</p>
              </div>
            ))}
          </div>

          {/* Plan badge */}
          <div className="bg-card border neon-border rounded-md p-4 neon-glow animate-fade-in flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-body">Current Plan</p>
              <p className="font-display text-sm font-semibold text-foreground mt-0.5">NeuroStrat Pro</p>
            </div>
            <button className="h-8 px-4 rounded text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/85 transition-all duration-200 neon-glow-strong">
              Upgrade
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Profile;
