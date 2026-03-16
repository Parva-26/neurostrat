import { Zap, Brain, Target, Shield, ChevronRight } from "lucide-react";

const pillars = [
  {
    icon: Brain,
    title: "AI-Powered Intelligence",
    desc: "Leveraging cutting-edge neural models to decode outreach intent and predict optimal contact strategies.",
  },
  {
    icon: Target,
    title: "Precision Targeting",
    desc: "Multi-dimensional signal analysis across CRM, social, and behavioural data to hit the right channel at the right time.",
  },
  {
    icon: Shield,
    title: "Trusted & Secure",
    desc: "Enterprise-grade data governance — your prospect intelligence stays private, encrypted, and under your control.",
  },
  {
    icon: Zap,
    title: "Instant Insight",
    desc: "Sub-second strategy generation. From scenario input to actionable recommendation in one click.",
  },
];

const About = () => {
  return (
    <div className="flex-1 flex flex-col tron-grid-bg">
      {/* Header */}
      <header className="h-12 flex items-center border-b border-border/60 px-6 backdrop-blur-sm bg-background/80">
        <h1 className="font-display text-sm font-semibold text-foreground neon-text">NeuroStrat</h1>
        <span className="ml-2 text-xs text-muted-foreground font-body">/ About</span>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        {/* Hero */}
        <div className="text-center max-w-2xl mb-16">
          {/* Animated logo mark */}
          <div className="flex items-center justify-center mb-8">
            <div className="relative">
              <div className="w-20 h-20 rounded-xl bg-primary/15 border neon-border flex items-center justify-center neon-glow-strong">
                <span className="font-display text-4xl font-bold text-primary neon-text">N</span>
              </div>
              {/* Orbit ring */}
              <div
                className="absolute inset-0 rounded-xl"
                style={{
                  boxShadow: "0 0 0 6px rgba(0,229,255,0.06), 0 0 0 12px rgba(0,229,255,0.02)",
                }}
              />
            </div>
          </div>

          <h2 className="font-display text-4xl font-bold text-foreground mb-4 neon-text tracking-tight">
            NeuroStrat Insights
          </h2>
          <p className="text-lg text-muted-foreground font-body leading-relaxed">
            The next-generation outreach intelligence platform. We fuse neural signal processing with
            real-world CRM data to surface the exact strategy your team needs — faster than any analyst ever could.
          </p>

          <div className="mt-8 flex items-center justify-center gap-3">
            <a
              href="/"
              className="inline-flex items-center gap-1.5 h-9 px-5 rounded text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/85 transition-all duration-200 neon-glow-strong"
            >
              Open Dashboard <ChevronRight size={14} />
            </a>
            <a
              href="mailto:hello@neurostrat.ai"
              className="inline-flex items-center gap-1.5 h-9 px-5 rounded text-sm font-medium border neon-border text-primary hover:bg-primary/10 transition-all duration-200"
            >
              Contact Us
            </a>
          </div>
        </div>

        {/* Pillars grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
          {pillars.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="bg-card border neon-border rounded-md p-5 neon-glow group hover:neon-glow-strong transition-all duration-300"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded bg-primary/15 flex items-center justify-center text-primary group-hover:neon-glow transition-all duration-300">
                  <Icon size={16} strokeWidth={1.5} />
                </div>
                <h3 className="font-display text-sm font-semibold text-foreground">{title}</h3>
              </div>
              <p className="text-xs text-muted-foreground font-body leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        {/* Version badge */}
        <p className="mt-12 text-xs text-muted-foreground/50 font-body">
          NeuroStrat Insights v1.0 · Built with AI-first architecture
        </p>
      </div>
    </div>
  );
};

export default About;
