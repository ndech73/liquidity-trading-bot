import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Zap, ScanSearch, Trophy } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Dash', icon: LayoutDashboard },
  { path: '/markets', label: 'Markets', icon: TrendingUp },
  { path: '/trades', label: 'Trades', icon: Zap },
  { path: '/analysis', label: 'Analysis', icon: ScanSearch },
  { path: '/performance', label: 'Stats', icon: Trophy },
];

export const MobileNavigation: React.FC = () => {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-slate-900 border-t border-slate-800 flex items-center justify-around z-40 px-2">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-full py-1 text-xs transition-colors ${
                isActive ? 'text-sky-400 font-semibold' : 'text-slate-400 hover:text-slate-200'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            <span className="mt-1 text-[11px]">{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
};
