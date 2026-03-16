import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Zap } from "lucide-react";

interface ScenarioFormProps {
  onGenerate: (data: { name: string; role: string; context: string }) => void;
  isLoading: boolean;
}

export function ScenarioForm({ onGenerate, isLoading }: ScenarioFormProps) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [context, setContext] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate({ name, role, context });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card border neon-border rounded-md p-6 animate-fade-in neon-glow">
      <h2 className="font-display text-sm font-semibold text-foreground tracking-wide uppercase mb-5 neon-text">
        New Outreach Scenario
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div className="space-y-1.5">
          <Label htmlFor="contact-name" className="text-xs font-medium text-muted-foreground">
            Contact Name
          </Label>
          <Input
            id="contact-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Sarah Chen"
            className="h-9 text-sm bg-background/60 border-border/50 text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:ring-primary/30"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="role" className="text-xs font-medium text-muted-foreground">
            Role
          </Label>
          <Input
            id="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. VP of Engineering"
            className="h-9 text-sm bg-background/60 border-border/50 text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:ring-primary/30"
          />
        </div>
      </div>

      <div className="space-y-1.5 mb-5">
        <Label htmlFor="context" className="text-xs font-medium text-muted-foreground">
          Context
        </Label>
        <Textarea
          id="context"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Describe the outreach scenario, prior interactions, goals..."
          rows={3}
          className="text-sm bg-background/60 border-border/50 text-foreground placeholder:text-muted-foreground/60 resize-none focus:border-primary focus:ring-primary/30"
        />
      </div>

      <Button
        type="submit"
        disabled={isLoading || !name.trim() || !role.trim()}
        className="h-9 px-5 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/85 transition-all duration-200 neon-glow-strong hover:shadow-[0_0_16px_rgba(0,200,255,0.4)]"
      >
        <Zap size={14} className="mr-1.5" />
        Generate Strategy
      </Button>
    </form>
  );
}
