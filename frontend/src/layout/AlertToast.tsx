import React, { useState, useEffect } from 'react';
import { ArrowUpRight, ArrowDownRight, X, Copy, Check, Radio } from 'lucide-react';
import { notificationService } from '../shared/services/notificationService';
import { LiquidityAlert } from '../shared/types/notification';

export const AlertToast: React.FC = () => {
  const [activeAlert, setActiveAlert] = useState<LiquidityAlert | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const unsub = notificationService.onAlert((alert) => {
      setActiveAlert(alert);
      setCopied(false);

      // Auto-dismiss after 15 seconds
      const timer = setTimeout(() => {
        setActiveAlert((current) => (current?.id === alert.id ? null : current));
      }, 15000);

      return () => clearTimeout(timer);
    });

    return () => unsub();
  }, []);

  if (!activeAlert) return null;

  const isBuy = activeAlert.direction === 'BUY';

  const handleCopy = () => {
    const text = `${activeAlert.symbol} ${activeAlert.direction} Setup:\nEntry: ${activeAlert.entryPrice}\nStop Loss: ${activeAlert.stopLoss}\nTP1: ${activeAlert.takeProfit1}\nTP2: ${activeAlert.takeProfit2}\nRisk: ${activeAlert.riskPips} pips (RR 1:${activeAlert.rrRatio})`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed top-20 right-4 sm:right-6 z-50 max-w-sm sm:max-w-md w-full bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl shadow-2xl p-4 animate-in slide-in-from-top-4 fade-in duration-200">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-black tracking-wider ${
              isBuy
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
            }`}
          >
            {isBuy ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
            {activeAlert.direction}
          </span>
          <span className="text-base font-extrabold text-white tracking-wide">
            {activeAlert.symbol}
          </span>
          <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
            {activeAlert.timeframe}
          </span>
          <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-amber-400 px-1.5 py-0.5 rounded bg-amber-500/10">
            <Radio className="w-3 h-3 animate-pulse" />
            Scanner Signal
          </span>
        </div>
        <button
          onClick={() => setActiveAlert(null)}
          title="Dismiss notification"
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Pricing row */}
      <div className="mt-3 grid grid-cols-3 gap-2 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 font-mono text-xs">
        <div>
          <span className="block text-[10px] uppercase text-slate-400">Entry</span>
          <span className="text-white font-bold">{activeAlert.entryPrice}</span>
        </div>
        <div>
          <span className="block text-[10px] uppercase text-slate-400">Stop Loss</span>
          <span className="text-rose-400 font-bold">{activeAlert.stopLoss}</span>
        </div>
        <div>
          <span className="block text-[10px] uppercase text-slate-400">TP1 (1:{activeAlert.rrRatio})</span>
          <span className="text-emerald-400 font-bold">{activeAlert.takeProfit1}</span>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-300 line-clamp-2 leading-relaxed">
        {activeAlert.reason}
      </p>

      {/* Footer controls */}
      <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between">
        <span className="text-[11px] text-slate-500">
          Risk: <span className="text-slate-300 font-semibold">{activeAlert.riskPips} pips</span>
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-400 hover:text-sky-300 rounded-md text-xs font-semibold transition-colors cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Setup Copied!</span>
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
};
