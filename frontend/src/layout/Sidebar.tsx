import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  Zap,
  ScanSearch,
  Fingerprint,
  Trophy,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

export const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/markets', label: 'Markets', icon: TrendingUp },
  { path: '/trades', label: 'Active Trades', icon: Zap },
  { path: '/analysis', label: 'Analysis Engine', icon: ScanSearch },
  { path: '/forensics', label: 'Forensics', icon: Fingerprint },
  { path: '/performance', label: 'Performance', icon: Trophy },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export interface SidebarProps {
  isCollapsed?: boolean;
  onToggle?: () => void;
  onExpand?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed = false,
  onToggle,
  onExpand,
}) => {
  const handleItemClick = () => {
    if (isCollapsed && onExpand) {
      onExpand();
    }
  };

  return (
    <aside
      className={`bg-slate-950 border-r border-slate-800 hidden md:flex flex-col h-screen sticky top-0 transition-all duration-300 ease-in-out shrink-0 z-30 ${
        isCollapsed ? 'w-18' : 'w-64'
      }`}
    >
      {/* Header */}
      <div
        className={`h-16 border-b border-slate-800 flex items-center transition-all duration-300 ${
          isCollapsed ? 'justify-center px-2' : 'justify-between px-5'
        }`}
      >
        {isCollapsed ? (
          <button
            onClick={onToggle || onExpand}
            title="Reveal sidebar"
            aria-label="Reveal sidebar"
            className="w-10 h-10 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 flex items-center justify-center text-sky-400 transition-colors group cursor-pointer"
          >
            <PanelLeftOpen className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-sky-500 flex items-center justify-center text-slate-950 font-black text-sm shadow-sm shadow-sky-500/30">
                L
              </div>
              <span className="font-bold text-base text-slate-100 tracking-tight">LiquidityBot</span>
            </div>
            {onToggle && (
              <button
                onClick={onToggle}
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-colors cursor-pointer"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            )}
          </>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={handleItemClick}
              title={isCollapsed ? `${item.label} (Click to reveal)` : undefined}
              className={({ isActive }) =>
                `flex items-center rounded-lg text-sm font-medium transition-all group relative cursor-pointer ${
                  isCollapsed ? 'justify-center py-3 px-2' : 'gap-3 px-3.5 py-2.5'
                } ${
                  isActive
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/25 shadow-xs shadow-sky-500/10'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent'
                }`
              }
            >
              <Icon className="w-5 h-5 shrink-0 transition-transform group-hover:scale-105" />
              {!isCollapsed && (
                <span className="truncate transition-opacity duration-200">{item.label}</span>
              )}

              {/* Floating tooltip when collapsed */}
              {isCollapsed && (
                <div className="pointer-events-none absolute left-full ml-3 px-2.5 py-1.5 bg-slate-900 text-slate-100 text-xs rounded-md shadow-xl border border-slate-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50 flex items-center gap-1.5">
                  <span className="font-semibold">{item.label}</span>
                  <span className="text-[10px] text-sky-400 font-normal">• Click to reveal</span>
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        className={`p-3.5 border-t border-slate-800 text-slate-500 text-xs transition-all duration-300 ${
          isCollapsed ? 'flex justify-center' : ''
        }`}
      >
        {isCollapsed ? (
          <div
            title="Engine v0.1.0 • Wine MT5 Bridge Active"
            className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 animate-pulse"
          />
        ) : (
          <div className="truncate">
            Engine v0.1.0 • Wine MT5 Bridge
          </div>
        )}
      </div>
    </aside>
  );
};
