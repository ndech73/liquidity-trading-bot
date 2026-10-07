import React, { useState, useEffect } from 'react';
import {
  Bell,
  Volume2,
  VolumeX,
  ShieldCheck,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  Copy,
  Check,
  Send,
  Radio,
  Filter,
  Trash2,
  Clock,
  Activity,
  Layers,
} from 'lucide-react';
import { notificationService } from '../../shared/services/notificationService';
import { LiquidityAlert, SweepNotice } from '../../shared/types/notification';
import { ENV } from '../../config/env';

const MONITORED_PAIRS = ['EURJPY', 'USDCHF', 'NZDUSD', 'USDCAD', 'GBPUSD', 'EURUSD'];

export const NotificationCenterPage: React.FC = () => {
  const [alerts, setAlerts] = useState<LiquidityAlert[]>(() => notificationService.getHistory());
  const [sweeps, setSweeps] = useState<SweepNotice[]>([]);
  const [permission, setPermission] = useState<NotificationPermission>(() => notificationService.permission);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => notificationService.isSoundEnabled);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'SWEEPS'>('ALL');
  const [scannerStatus, setScannerStatus] = useState<{
    mode: string;
    auto_trade_enabled: boolean;
    watchlist: string[];
  }>({
    mode: 'ALERT_SCANNER',
    auto_trade_enabled: false,
    watchlist: MONITORED_PAIRS,
  });

  // Subscribe to live notifications & fetch initial state
  useEffect(() => {
    const unsubAlert = notificationService.onAlert((newAlert) => {
      setAlerts((prev) => [newAlert, ...prev.slice(0, 99)]);
    });

    const unsubSweep = notificationService.onSweep((newSweep) => {
      setSweeps((prev) => [newSweep, ...prev.slice(0, 49)]);
    });

    // Fetch initial alerts
    fetch(`${ENV.API_URL}/notifications/alerts`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.alerts && Array.isArray(data.alerts)) {
          setAlerts(data.alerts);
          notificationService.setHistory(data.alerts);
        }
      })
      .catch(() => {});

    // Fetch scanner status
    fetch(`${ENV.API_URL}/notifications/status`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.status === 'ok') {
          setScannerStatus(data);
        }
      })
      .catch(() => {});

    return () => {
      unsubAlert();
      unsubSweep();
    };
  }, []);

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
      // Local fallback test
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
        setupType: 'Liquidity Sweep Reversal (Test)',
        reason: 'Sell-side liquidity pool raid on GBPUSD 15m with strong rejection candle.',
        timestamp: new Date().toISOString(),
        isTest: true,
      });
    } finally {
      setTimeout(() => setIsTesting(false), 500);
    }
  };

  const handleCopySetup = (alert: LiquidityAlert) => {
    const text = `🚨 ${alert.symbol} ${alert.direction} SETUP (${alert.timeframe})\nEntry: ${alert.entryPrice}\nStop Loss: ${alert.stopLoss}\nTake Profit 1: ${alert.takeProfit1} (1:${alert.rrRatio} RR)\nTake Profit 2: ${alert.takeProfit2}\nRisk: ${alert.riskPips} pips\nStrategy: ${alert.reason}`;
    navigator.clipboard.writeText(text);
    setCopiedId(alert.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'BUY') return a.direction === 'BUY';
    if (filter === 'SELL') return a.direction === 'SELL';
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6 animate-in fade-in duration-200">
      {/* Top Banner / Hero */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
                <Radio className="w-3.5 h-3.5 animate-pulse" />
                SCANNER ACTIVE
              </span>
              <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
                Discretionary Mode
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Liquidity Signal Scanner
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Scanning 6 currency pairs 24/7 for Smart Money liquidity raids & high-probability rejection entries.
            </p>
          </div>

          {/* Quick Action Controls */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {permission !== 'granted' ? (
              <button
                onClick={handleRequestPermission}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-md cursor-pointer"
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Enable Push Notifications</span>
              </button>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold rounded-xl">
                <ShieldCheck className="w-4 h-4" />
                <span>Push Active</span>
              </div>
            )}

            <button
              onClick={handleToggleSound}
              title={soundEnabled ? 'Mute alert sounds' : 'Enable alert sounds'}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-semibold transition-colors cursor-pointer ${
                soundEnabled
                  ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200'
                  : 'bg-slate-900 border-slate-800 text-slate-500'
              }`}
            >
              {soundEnabled ? (
                <>
                  <Volume2 className="w-4 h-4 text-emerald-400" />
                  <span>Sound On</span>
                </>
              ) : (
                <>
                  <VolumeX className="w-4 h-4 text-slate-500" />
                  <span>Sound Muted</span>
                </>
              )}
            </button>

            <button
              onClick={handleTriggerTest}
              disabled={isTesting}
              title="Test notification and chime sound"
              className="flex items-center gap-1.5 px-3.5 py-2 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-400 text-xs font-bold rounded-xl transition-colors cursor-pointer disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Test Signal</span>
            </button>
          </div>
        </div>

        {/* Watchlist strip */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <Layers className="w-4 h-4 text-slate-500" />
            <span className="font-semibold text-slate-300">Monitored Pairs:</span>
            <div className="flex flex-wrap items-center gap-1.5">
              {(scannerStatus.watchlist || MONITORED_PAIRS).map((pair) => (
                <span
                  key={pair}
                  className="px-2 py-0.5 rounded-md bg-slate-800/80 text-slate-300 font-mono text-[11px] border border-slate-700/50"
                >
                  {pair}
                </span>
              ))}
            </div>
          </div>
          <span className="text-slate-500 font-mono text-[11px]">
            Execution: Discretionary (Auto-Trade Disabled)
          </span>
        </div>
      </div>

      {/* Main Alert Feed Section */}
      <div className="space-y-4">
        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
          <div className="flex items-center gap-1.5">
            <Filter className="w-4 h-4 text-slate-400 ml-1" />
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Filter:</span>
            {(['ALL', 'BUY', 'SELL', 'SWEEPS'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  filter === tab
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {tab === 'SWEEPS' ? `Raw Sweeps (${sweeps.length})` : tab}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>
              Total Signals: <strong className="text-white font-mono">{alerts.length}</strong>
            </span>
            {alerts.length > 0 && (
              <button
                onClick={() => {
                  setAlerts([]);
                  notificationService.setHistory([]);
                }}
                title="Clear alerts display"
                className="flex items-center gap-1 text-slate-500 hover:text-rose-400 transition-colors ml-3 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Content Stream */}
        {filter === 'SWEEPS' ? (
          /* Raw Liquidity Sweeps Stream */
          <div className="space-y-3">
            {sweeps.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center">
                <Activity className="w-10 h-10 text-slate-600 mx-auto mb-3 opacity-50" />
                <h3 className="text-base font-bold text-slate-300">No sweep breaches detected recently</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  When price sweeps an established buy-side or sell-side liquidity pool, it will appear here immediately.
                </p>
              </div>
            ) : (
              sweeps.map((s) => (
                <div
                  key={s.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 rounded text-xs font-extrabold font-mono ${
                        s.side === 'BUY' || s.side === 'BUYSIDE'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {s.side}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{s.symbol}</span>
                        <span className="text-xs font-mono text-slate-400">[{s.timeframe}]</span>
                        <span className="text-xs text-slate-400">{s.liquidityType}</span>
                      </div>
                      <div className="text-xs font-mono text-slate-400 mt-0.5">
                        Level: <span className="text-slate-300">{s.levelPrice}</span> | Sweep Price:{' '}
                        <span className="text-amber-400 font-bold">{s.sweepPrice}</span>
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-slate-500 font-mono shrink-0">
                    {formatTimeAgo(s.occurredAt)}
                  </span>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Actionable Trade Signals Stream */
          <div className="space-y-3">
            {filteredAlerts.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center">
                <Bell className="w-10 h-10 text-slate-600 mx-auto mb-3 opacity-50" />
                <h3 className="text-base font-bold text-slate-300">No signals detected yet</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  The scanner is actively analyzing M15 and H1 market structure across all 6 pairs. When liquidity is swept with confirmation, high-confluence setups will be pushed here instantly with full entry/exit parameters.
                </p>
                <div className="mt-4">
                  <button
                    onClick={handleTriggerTest}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-400 text-xs font-bold rounded-xl transition-colors cursor-pointer"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send a Test Notification</span>
                  </button>
                </div>
              </div>
            ) : (
              filteredAlerts.map((alert) => {
                const isBuy = alert.direction === 'BUY';

                return (
                  <div
                    key={alert.id}
                    className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-4 sm:p-5 transition-all shadow-lg flex flex-col gap-3 group"
                  >
                    {/* Header line */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-black tracking-wider ${
                            isBuy
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                          }`}
                        >
                          {isBuy ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                          {alert.direction}
                        </span>

                        <span className="text-lg font-extrabold text-white tracking-wide">
                          {alert.symbol}
                        </span>

                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/50">
                          {alert.timeframe}
                        </span>

                        <span className="hidden sm:inline text-xs text-slate-400">
                          {alert.setupType}
                        </span>

                        {alert.isTest && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            TEST
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTimeAgo(alert.timestamp)}
                        </span>
                      </div>
                    </div>

                    {/* Trade Levels Pricing Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 font-mono text-xs">
                      <div>
                        <span className="block text-[10px] uppercase font-bold tracking-wider text-slate-500">
                          Entry Price
                        </span>
                        <span className="text-white font-bold text-sm">{alert.entryPrice}</span>
                      </div>

                      <div>
                        <span className="block text-[10px] uppercase font-bold tracking-wider text-rose-400/80">
                          Stop Loss (SL)
                        </span>
                        <span className="text-rose-400 font-bold text-sm">{alert.stopLoss}</span>
                        <span className="text-[10px] text-slate-500 block">
                          ({alert.riskPips} pips)
                        </span>
                      </div>

                      <div>
                        <span className="block text-[10px] uppercase font-bold tracking-wider text-emerald-400/80">
                          Take Profit 1
                        </span>
                        <span className="text-emerald-400 font-bold text-sm">{alert.takeProfit1}</span>
                        <span className="text-[10px] text-slate-500 block">
                          (1:{alert.rrRatio} RR)
                        </span>
                      </div>

                      <div>
                        <span className="block text-[10px] uppercase font-bold tracking-wider text-emerald-400/80">
                          Take Profit 2 (Runner)
                        </span>
                        <span className="text-emerald-400 font-bold text-sm">{alert.takeProfit2}</span>
                        <span className="text-[10px] text-slate-500 block">
                          (1:3.0 RR)
                        </span>
                      </div>
                    </div>

                    {/* Reason text & Copy button */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                      <p className="text-xs text-slate-300 leading-relaxed max-w-2xl">
                        {alert.reason}
                      </p>

                      <button
                        onClick={() => handleCopySetup(alert)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 transition-colors shrink-0 cursor-pointer self-start sm:self-center"
                      >
                        {copiedId === alert.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied to Clipboard!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Parameters</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
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
