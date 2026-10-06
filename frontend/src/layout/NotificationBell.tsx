import React, { useState, useEffect, useRef } from 'react';
import {
  Bell,
  BellOff,
  Volume2,
  VolumeX,
  ShieldCheck,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  Copy,
  Check,
  Send,
  Sparkles,
} from 'lucide-react';
import { notificationService } from '../shared/services/notificationService';
import { LiquidityAlert } from '../shared/types/notification';
import { ENV } from '../config/env';

export const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission>(() => notificationService.permission);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => notificationService.isSoundEnabled);
  const [alerts, setAlerts] = useState<LiquidityAlert[]>(() => notificationService.getHistory());
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Subscribe to live incoming alerts
  useEffect(() => {
    const unsub = notificationService.onAlert((newAlert) => {
      setAlerts((prev) => [newAlert, ...prev.slice(0, 49)]);
      setUnreadCount((c) => c + 1);
    });

    // Fetch initial alert history from backend
    fetch(`${ENV.API_URL}/notifications/alerts`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.alerts && Array.isArray(data.alerts)) {
          setAlerts(data.alerts);
          notificationService.setHistory(data.alerts);
        }
      })
      .catch(() => {});

    return () => unsub();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleToggleOpen = () => {
    setIsOpen((prev) => {
      if (!prev) setUnreadCount(0);
      return !prev;
    });
  };

  const handleRequestPermission = async () => {
    const res = await notificationService.requestPermission();
    setPermission(res);
  };

  const handleToggleSound = () => {
    const next = !soundEnabled;
    notificationService.setSoundEnabled(next);
    setSoundEnabled(next);
    if (next) {
      notificationService.playChime(false);
    }
  };

  const handleTriggerTest = async () => {
    setIsTesting(true);
    try {
      await fetch(`${ENV.API_URL}/notifications/test`, { method: 'POST' });
    } catch {
      // Fallback local test dispatch
      notificationService.dispatchAlert({
        id: `local-test-${Date.now()}`,
        symbol: 'GBPUSD',
        timeframe: '15m',
        direction: 'BUY',
        entryPrice: 1.30542,
        stopLoss: 1.30320,
        takeProfit1: 1.30808,
        takeProfit2: 1.31208,
        riskPips: 22.2,
        rrRatio: 1.2,
        setupType: 'Liquidity Raid Reversal (Test)',
        reason: 'Sell-side liquidity swept on GBPUSD 15m with strong bullish rejection.',
        timestamp: new Date().toISOString(),
        isTest: true,
      });
    } finally {
      setTimeout(() => setIsTesting(false), 500);
    }
  };

  const handleCopySetup = (alert: LiquidityAlert) => {
    const text = `${alert.symbol} ${alert.direction} Setup:\nEntry: ${alert.entryPrice}\nStop Loss: ${alert.stopLoss}\nTP1: ${alert.takeProfit1}\nTP2: ${alert.takeProfit2}\nRisk: ${alert.riskPips} pips (RR 1:${alert.rrRatio})`;
    navigator.clipboard.writeText(text);
    setCopiedId(alert.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={handleToggleOpen}
        title="Liquidity Alerts & Notifications"
        aria-label="Liquidity Alerts & Notifications"
        className="relative w-9 h-9 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/50 flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer"
      >
        <Bell className="w-4 h-4 text-amber-400" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-slate-900 animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="p-3.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span className="font-semibold text-sm text-slate-200">Liquidity Alerts</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Scanner Mode
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleToggleSound}
                title={soundEnabled ? 'Mute alert sounds' : 'Enable alert sounds'}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
              >
                {soundEnabled ? (
                  <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <VolumeX className="w-3.5 h-3.5 text-slate-500" />
                )}
              </button>
              <button
                onClick={handleTriggerTest}
                disabled={isTesting}
                title="Send test alert notification"
                className="flex items-center gap-1 px-2 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-400 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3 h-3" />
                <span>Test</span>
              </button>
            </div>
          </div>

          {/* Browser Permission Prompt Banner */}
          {permission !== 'granted' && (
            <div className="p-3 bg-amber-950/40 border-b border-amber-800/40 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-amber-300">
                <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
                <span>Enable browser push notifications to get alerted instantly.</span>
              </div>
              <button
                onClick={handleRequestPermission}
                className="shrink-0 px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-md transition-colors cursor-pointer"
              >
                Allow
              </button>
            </div>
          )}

          {permission === 'granted' && (
            <div className="px-3.5 py-1.5 bg-slate-950/40 border-b border-slate-800/50 flex items-center justify-between text-[11px] text-slate-400">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Browser notifications active</span>
              </div>
              <span className="text-slate-500">Alerts: {alerts.length}</span>
            </div>
          )}

          {/* Alerts List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-1">
            {alerts.length === 0 ? (
              <div className="py-8 px-4 text-center">
                <BellOff className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-50" />
                <p className="text-sm font-medium text-slate-400">No signals detected yet</p>
                <p className="text-xs text-slate-500 mt-1">
                  The scanner is actively monitoring the watchlist for liquidity pool raids.
                </p>
              </div>
            ) : (
              alerts.map((alert) => {
                const isBuy = alert.direction === 'BUY';
                const timeAgo = formatTimeAgo(alert.timestamp);

                return (
                  <div
                    key={alert.id}
                    className="p-3 hover:bg-slate-800/40 rounded-lg transition-colors flex flex-col gap-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`flex items-center gap-0.5 px-2 py-0.5 rounded text-xs font-bold ${
                            isBuy
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {isBuy ? (
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          ) : (
                            <ArrowDownRight className="w-3.5 h-3.5" />
                          )}
                          {alert.direction}
                        </span>
                        <span className="font-bold text-slate-200 text-sm tracking-wide">
                          {alert.symbol}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {alert.timeframe}
                        </span>
                        {alert.isTest && (
                          <span className="text-[10px] px-1 rounded bg-purple-500/20 text-purple-300">
                            TEST
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500">{timeAgo}</span>
                    </div>

                    {/* Trade Price Details */}
                    <div className="grid grid-cols-3 gap-2 bg-slate-950/50 p-2 rounded border border-slate-800/60 font-mono text-[11px]">
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">Entry</span>
                        <span className="text-slate-200 font-semibold">{alert.entryPrice}</span>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">Stop Loss</span>
                        <span className="text-rose-400">{alert.stopLoss}</span>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">TP1 (1:{alert.rrRatio})</span>
                        <span className="text-emerald-400">{alert.takeProfit1}</span>
                      </div>
                    </div>

                    {/* Setup Reason & Action */}
                    <div className="flex items-center justify-between text-xs pt-0.5">
                      <p className="text-[11px] text-slate-400 truncate max-w-[240px]" title={alert.reason}>
                        {alert.reason}
                      </p>
                      <button
                        onClick={() => handleCopySetup(alert)}
                        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800/60 hover:bg-slate-700 transition-colors cursor-pointer shrink-0"
                        title="Copy setup levels to clipboard"
                      >
                        {copiedId === alert.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function formatTimeAgo(isoString: string): string {
  try {
    const elapsed = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (elapsed < 60) return `${Math.max(1, elapsed)}s ago`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ago`;
    if (elapsed < 86400) return `${Math.floor(elapsed / 3600)}h ago`;
    return `${Math.floor(elapsed / 86400)}d ago`;
  } catch {
    return 'recently';
  }
}
