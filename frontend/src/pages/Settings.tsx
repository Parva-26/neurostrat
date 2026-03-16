import { useState } from "react";
import { Bell, Moon, Globe, Key, Trash2, ChevronRight } from "lucide-react";

interface ToggleProps {
  enabled: boolean;
  onToggle: () => void;
}

function Toggle({ enabled, onToggle }: ToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-300 focus:outline-none ${
        enabled ? "bg-primary neon-glow" : "bg-muted"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-300 ${
          enabled ? "translate-x-[18px]" : "translate-x-[3px]"
        }`}
      />
    </button>
  );
}

interface SettingRowProps {
  icon: React.ElementType;
  label: string;
  desc: string;
  control: React.ReactNode;
}

function SettingRow({ icon: Icon, label, desc, control }: SettingRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-border/30 last:border-b-0">
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded bg-primary/10 flex items-center justify-center text-primary shrink-0">
          <Icon size={13} strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground font-display">{label}</p>
          <p className="text-xs text-muted-foreground font-body">{desc}</p>
        </div>
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

const Settings = () => {
  const [notifications, setNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [telemetry, setTelemetry] = useState(false);

  return (
    <div className="flex-1 flex flex-col tron-grid-bg">
      {/* Header */}
      <header className="h-12 flex items-center border-b border-border/60 px-6 backdrop-blur-sm bg-background/80">
        <h1 className="font-display text-sm font-semibold text-foreground neon-text">NeuroStrat</h1>
        <span className="ml-2 text-xs text-muted-foreground font-body">/ Settings</span>
      </header>

      <div className="flex-1 flex justify-center py-10 px-6">
        <div className="w-full max-w-2xl space-y-5">

          {/* Preferences */}
          <section className="bg-card border neon-border rounded-md p-5 neon-glow animate-fade-in">
            <h2 className="font-display text-xs font-semibold text-foreground tracking-widest uppercase mb-4 neon-text">
              Preferences
            </h2>
            <SettingRow
              icon={Bell}
              label="Notifications"
              desc="Receive alerts for new strategy insights"
              control={<Toggle enabled={notifications} onToggle={() => setNotifications((v) => !v)} />}
            />
            <SettingRow
              icon={Moon}
              label="Dark Mode"
              desc="Always use TRON dark theme"
              control={<Toggle enabled={darkMode} onToggle={() => setDarkMode((v) => !v)} />}
            />
            <SettingRow
              icon={Globe}
              label="Usage Analytics"
              desc="Help us improve by sharing anonymous telemetry"
              control={<Toggle enabled={telemetry} onToggle={() => setTelemetry((v) => !v)} />}
            />
          </section>

          {/* API & Integrations */}
          <section className="bg-card border neon-border rounded-md p-5 neon-glow animate-fade-in">
            <h2 className="font-display text-xs font-semibold text-foreground tracking-widest uppercase mb-4 neon-text">
              API & Integrations
            </h2>
            <button className="w-full flex items-center justify-between py-3 border-b border-border/30 group">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded bg-primary/10 flex items-center justify-center text-primary">
                  <Key size={13} strokeWidth={1.5} />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground font-display group-hover:text-primary transition-colors">API Keys</p>
                  <p className="text-xs text-muted-foreground font-body">Manage your API credentials</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-muted-foreground group-hover:text-primary transition-colors" />
            </button>
            <button className="w-full flex items-center justify-between py-3 group">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded bg-primary/10 flex items-center justify-center text-primary">
                  <Globe size={13} strokeWidth={1.5} />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground font-display group-hover:text-primary transition-colors">CRM Integration</p>
                  <p className="text-xs text-muted-foreground font-body">Connect Salesforce, HubSpot & more</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-muted-foreground group-hover:text-primary transition-colors" />
            </button>
          </section>

          {/* Danger Zone */}
          <section className="bg-card border border-destructive/30 rounded-md p-5 animate-fade-in">
            <h2 className="font-display text-xs font-semibold text-destructive tracking-widest uppercase mb-4">
              Danger Zone
            </h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground font-display">Delete Account</p>
                <p className="text-xs text-muted-foreground font-body">Permanently remove your account and all data</p>
              </div>
              <button className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-medium border border-destructive/50 text-destructive hover:bg-destructive/10 transition-all duration-200">
                <Trash2 size={12} />
                Delete
              </button>
            </div>
          </section>

          {/* Version */}
          <p className="text-center text-xs text-muted-foreground/40 font-body pb-4">
            NeuroStrat Insights v1.0.0
          </p>

        </div>
      </div>
    </div>
  );
};

export default Settings;
