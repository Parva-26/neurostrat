import { useState } from "react";
import { ScenarioForm } from "@/components/ScenarioForm";
import { StrategyCard } from "@/components/StrategyCard";

const Index = () => {
  const [result, setResult] = useState<{
    channel: string;
    confidence: number;
    contactName: string;
    factors: string[];
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async (data: { name: string; role: string; context: string }) => {
    setIsLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/strategy`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data),
      });
      const json = await res.json();
      setResult(json);
    } catch (error) {
      console.error("[NeuroStrat] Error:", error);
    } finally {
    setIsLoading(false);
    }
  };

  return (
    <main className="flex-1 flex flex-col tron-grid-bg">
      {/* Header */}
      <header className="h-12 flex items-center border-b border-border/60 px-6 backdrop-blur-sm bg-background/80">
        <h1 className="font-display text-sm font-semibold text-foreground neon-text">NeuroStrat</h1>
        <span className="ml-2 text-xs text-muted-foreground font-body">/ Dashboard</span>
      </header>

      {/* Content */}
      <div className="flex-1 flex justify-center py-8 px-6">
        <div className="w-full max-w-2xl space-y-5">
          <ScenarioForm onGenerate={handleGenerate} isLoading={isLoading} />

          {isLoading && (
            <div className="bg-card border neon-border rounded-md p-6 animate-fade-in neon-glow">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Generating strategy...
              </div>
            </div>
          )}

          {result && !isLoading && (
            <StrategyCard
              channel={result.channel}
              confidence={result.confidence}
              factors={result.factors}
              contactName={result.contactName}
            />
          )}
        </div>
      </div>
    </main>
  );
};

export default Index;
