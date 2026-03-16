import { User, History, Settings } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

const navItems = [
  { icon: User, label: "Profile", to: "/profile" },
  { icon: History, label: "History", to: "/history" },
  { icon: Settings, label: "Settings", to: "/settings" },
];

export function AppSidebar() {
  const navigate = useNavigate();

  return (
    <aside className="flex flex-col items-center w-14 min-h-screen bg-sidebar border-r border-border/40 py-6 gap-6 shrink-0">
      {/* Logo — routes to About page */}
      <button
        onClick={() => navigate("/about")}
        className="flex items-center justify-center w-8 h-8 rounded bg-primary/20 border neon-border mb-4 neon-glow-strong hover:bg-primary/30 transition-all duration-200"
        title="About NeuroStrat"
      >
        <span className="font-display text-sm font-bold text-primary neon-text">N</span>
      </button>

      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.to}
            title={item.label}
            className={({ isActive }) =>
              `flex items-center justify-center w-10 h-10 rounded transition-all duration-200 ${
                isActive
                  ? "bg-primary/20 text-primary neon-glow"
                  : "text-sidebar-muted hover:text-foreground hover:bg-muted/50"
              }`
            }
          >
            <item.icon size={18} strokeWidth={1.5} />
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
