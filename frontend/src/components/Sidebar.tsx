import { useState } from "react";
import { ParentResponse } from "../apis";
import { 
  LayoutDashboard, 
  Users, 
  ShieldAlert, 
  Gamepad, 
  Settings, 
  LogOut, 
  Menu, 
  X, 
  Shield 
} from "lucide-react";

interface SidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
  parent: ParentResponse | null;
  onLogout: () => void;
  unreadAlertsCount: number;
}

export default function Sidebar({
  activeView,
  onNavigate,
  parent,
  onLogout,
  unreadAlertsCount,
}: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false);

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "alerts", label: "Alerts", icon: ShieldAlert, badge: unreadAlertsCount },
    { id: "children", label: "Children", icon: Users },
    { id: "debug", label: "Test Chat Room", icon: Gamepad },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  const handleNavigate = (view: string) => {
    onNavigate(view);
    setIsOpen(false);
  };

  return (
    <>
      {/* Mobile Top Navbar */}
      <header className="lg:hidden flex items-center justify-between bg-slate-900 border-b border-slate-800 px-4 py-3 sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm text-white tracking-tight">TellMom</span>
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-slate-400 hover:text-white transition-colors"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Sidebar Overlay for Mobile */}
      {isOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Content panel */}
      <aside
        className={`fixed lg:sticky top-[53px] lg:top-0 left-0 bottom-0 w-64 bg-slate-950 border-r border-slate-800/80 z-40 flex flex-col justify-between transform lg:transform-none transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        } h-[calc(100vh-53px)] lg:h-screen`}
      >
        <div className="p-4 space-y-6">
          {/* Logo (Desktop only) */}
          <div className="hidden lg:flex items-center gap-2 px-2 py-1.5">
            <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center shadow-lg shadow-violet-500/10">
              <Shield className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-bold text-base text-white tracking-tight">TellMom</span>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeView === item.id || (item.id === "alerts" && activeView.startsWith("alert-"));
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigate(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                    isActive
                      ? "bg-violet-600/10 text-violet-400 border border-violet-500/15"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/30 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && item.badge > 0 ? (
                    <span className="bg-red-500/10 text-red-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full border border-red-500/20">
                      {item.badge}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer Profile & Logout */}
        <div className="p-4 border-t border-slate-900 bg-slate-950/60 flex flex-col gap-3">
          <div className="px-2">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Logged in as</span>
            <span className="text-xs text-slate-350 font-medium truncate block max-w-full">
              {parent?.email ?? "parent@example.com"}
            </span>
          </div>

          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-red-400 hover:bg-red-950/15 border border-transparent hover:border-red-950/10 transition-all"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </aside>
    </>
  );
}
