import React from 'react';
import { PanelLeftClose, PanelLeftOpen, Activity, Wallet, Radio } from 'lucide-react';

export interface TopbarProps {
  botStatus?: 'RUNNING' | 'PAUSED' | 'OFFLINE';
  accountBalance?: number;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
  isWsConnected?: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({
  botStatus = 'OFFLINE',
  accountBalance = 0,
  isSidebarCollapsed = false,
  onToggleSidebar,
  isWsConnected = false,
}) => {
  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            title={isSidebarCollapsed ? 'Reveal sidebar' : 'Collapse sidebar'}
            aria-label={isSidebarCollapsed ? 'Reveal sidebar' : 'Collapse sidebar'}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors hidden md:flex items-center justify-center cursor-pointer"
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen className="w-5 h-5 text-sky-400" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
        )}
        <span className="text-sm font-semibold tracking-wider uppercase text-slate-300 hidden sm:inline">
          Liquidity Trading System
        </span>
        <div className="flex items-center gap-2 px-2.5 py-1 bg-slate-800/80 border border-slate-700/50 rounded-full text-xs">
          <Activity
            className={`w-3.5 h-3.5 ${
              botStatus === 'RUNNING' ? 'text-emerald-400 animate-pulse' : 'text-amber-400'
            }`}
          />
          <span className="font-medium text-slate-300">{botStatus}</span>
        </div>
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800/80 border border-slate-700/50 rounded-full text-xs"
          title={isWsConnected ? 'WebSocket Relay Connected' : 'WebSocket Reconnecting...'}
        >
          <Radio
            className={`w-3.5 h-3.5 ${
              isWsConnected ? 'text-emerald-400 animate-pulse' : 'text-rose-400'
            }`}
          />
          <span className="font-medium text-slate-300 hidden md:inline">
            {isWsConnected ? 'RELAY LIVE' : 'WS RECONNECTING'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 sm:gap-6 text-sm">
        <div className="flex items-center gap-2 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800 text-right">
          <Wallet className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">Account Equity</span>
            <span className="font-mono font-semibold text-emerald-400 leading-tight">
              ${accountBalance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold text-xs border border-sky-500/30">
          MT5
        </div>
      </div>
    </header>
  );
};

