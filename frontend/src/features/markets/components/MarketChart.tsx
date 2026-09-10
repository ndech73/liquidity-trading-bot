import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
} from 'lightweight-charts';
import { Card } from '../../../shared/components/Card';
import { ChartToolbar } from './ChartToolbar';
import { getCandleData } from '../services/marketService';
import { Spinner } from '../../../shared/components/Spinner';

interface CandleItem {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export const MarketChart: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [timeframe, setTimeframe] = useState('M5');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastBar, setLastBar] = useState<CandleItem | null>(null);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const fetchAndRenderCandles = useCallback(async () => {
    if (!symbol) return;
    try {
      const tfParam = timeframe.toLowerCase();
      const res = await getCandleData(symbol, tfParam, 120);

      if (res && res.candles && res.candles.length > 0) {
        const candleData = res.candles.map((c: CandleItem) => ({
          time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        const volumeData = res.candles.map((c: CandleItem) => ({
          time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
          value: c.volume,
          color: c.close >= c.open ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)',
        }));

        // Sort ascending by timestamp as required by lightweight-charts
        candleData.sort((a, b) => a.time - b.time);
        volumeData.sort((a, b) => a.time - b.time);

        // Deduplicate adjacent identical timestamps
        const uniqueCandles = candleData.filter(
          (v, i, a) => i === 0 || v.time > a[i - 1].time
        );
        const uniqueVolumes = volumeData.filter(
          (v, i, a) => i === 0 || v.time > a[i - 1].time
        );

        if (candleSeriesRef.current) {
          candleSeriesRef.current.setData(uniqueCandles);
        }
        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.setData(uniqueVolumes);
        }
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }

        setLastBar(res.candles[res.candles.length - 1]);
        setError(null);
      } else {
        setError(`No candle data available from broker for ${symbol}.`);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch candlestick data.');
    } finally {
      setIsLoading(false);
    }
  }, [symbol, timeframe]);

  // Initialize Lightweight Charts instance
  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth || 800,
      height: 520,
      layout: {
        background: { type: ColorType.Solid, color: '#090d16' },
        textColor: '#94a3b8',
        fontFamily: 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(30, 41, 59, 0.45)' },
        horzLines: { color: 'rgba(30, 41, 59, 0.45)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#0284c7',
          width: 1,
          style: 2,
          labelBackgroundColor: '#0369a1',
        },
        horzLine: {
          color: '#0284c7',
          width: 1,
          style: 2,
          labelBackgroundColor: '#0369a1',
        },
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.22,
        },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#f43f5e',
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '', // overlay pane
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (container && chartRef.current) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    setIsLoading(true);
    fetchAndRenderCandles();

    // Auto-refresh every 5 seconds for live broker updates
    const interval = setInterval(fetchAndRenderCandles, 5000);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      clearInterval(interval);
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, timeframe, fetchAndRenderCandles]);

  const priceChange = lastBar ? lastBar.close - lastBar.open : 0;
  const pctChange = lastBar && lastBar.open > 0 ? (priceChange / lastBar.open) * 100 : 0;
  const isUp = priceChange >= 0;

  return (
    <Card title={`${symbol} Live Candlestick Feed`}>
      <div className="space-y-3">
        {/* Top chart header with live price metrics and timeframe buttons */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <ChartToolbar timeframe={timeframe} onTimeframeChange={setTimeframe} />
          
          {lastBar && (
            <div className="flex items-center gap-4 text-xs font-mono">
              <div className="flex items-center gap-1.5 bg-slate-900/90 px-3 py-1.5 rounded border border-slate-800">
                <span className="text-slate-400">O:</span>
                <span className="text-slate-200">{lastBar.open.toFixed(5)}</span>
                <span className="text-slate-400 ml-1">H:</span>
                <span className="text-emerald-400">{lastBar.high.toFixed(5)}</span>
                <span className="text-slate-400 ml-1">L:</span>
                <span className="text-rose-400">{lastBar.low.toFixed(5)}</span>
                <span className="text-slate-400 ml-1">C:</span>
                <span className={`font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {lastBar.close.toFixed(5)}
                </span>
                <span
                  className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    isUp ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60' : 'bg-rose-950 text-rose-300 border border-rose-800/60'
                  }`}
                >
                  {isUp ? '+' : ''}
                  {pctChange.toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Chart Canvas Container */}
        <div className="relative w-full h-[520px] rounded-lg overflow-hidden border border-slate-800 bg-[#090d16]">
          {isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#090d16]/80 backdrop-blur-xs">
              <Spinner size="lg" />
              <span className="text-xs text-slate-400 mt-2 font-mono">
                Streaming {symbol} {timeframe} candles from MT5...
              </span>
            </div>
          )}

          {error && !isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#090d16]/90 p-4 text-center">
              <p className="text-sm font-semibold text-rose-400">{error}</p>
              <button
                onClick={fetchAndRenderCandles}
                className="mt-3 px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition"
              >
                Retry Fetch
              </button>
            </div>
          )}

          <div ref={chartContainerRef} className="w-full h-full" />
        </div>
      </div>
    </Card>
  );
};
