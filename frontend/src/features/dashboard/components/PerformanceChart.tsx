import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  AreaSeries,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
} from 'lightweight-charts';
import { Card } from '../../../shared/components/Card';
import { getEquityCurve, EquityPoint } from '../services/dashboardService';
import { formatCurrency } from '../../../shared/utils/formatCurrency';
import { Spinner } from '../../../shared/components/Spinner';

export const PerformanceChart: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [currentEquity, setCurrentEquity] = useState<number | null>(null);
  const [hoveredEquity, setHoveredEquity] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await getEquityCurve();
      if (data && data.length > 0) {
        const sorted = [...data]
          .map((p: EquityPoint) => ({
            time: p.time as UTCTimestamp,
            value: p.value,
          }))
          .sort((a, b) => a.time - b.time);

        // Deduplicate timestamps
        const unique = sorted.filter(
          (v, i, a) => i === 0 || v.time > a[i - 1].time
        );

        if (seriesRef.current) {
          seriesRef.current.setData(unique);
        }
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }

        const latest = unique[unique.length - 1];
        if (latest) {
          setCurrentEquity(latest.value);
        }
      }
    } catch (e) {
      console.error('Failed to fetch equity curve:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth || 600,
      height: 220,
      layout: {
        background: { type: ColorType.Solid, color: '#090d16' },
        textColor: '#64748b',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(30, 41, 59, 0.3)' },
        horzLines: { color: 'rgba(30, 41, 59, 0.3)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#0284c7',
          width: 1,
          style: 3,
        },
        horzLine: {
          color: '#0284c7',
          width: 1,
          style: 3,
        },
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.5)',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.5)',
        scaleMargins: {
          top: 0.15,
          bottom: 0.1,
        },
      },
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: '#0ea5e9',
      topColor: 'rgba(14, 165, 233, 0.35)',
      bottomColor: 'rgba(14, 165, 233, 0.0)',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    chart.subscribeCrosshairMove((param) => {
      if (param.time && param.seriesData.get(areaSeries)) {
        const val = param.seriesData.get(areaSeries) as any;
        setHoveredEquity(val?.value ?? null);
      } else {
        setHoveredEquity(null);
      }
    });

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

    loadData();
    const interval = setInterval(loadData, 8000);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      clearInterval(interval);
      chart.remove();
      chartRef.current = null;
    };
  }, [loadData]);

  const displayEquity = hoveredEquity !== null ? hoveredEquity : currentEquity;

  return (
    <Card
      title="Cumulative Equity Curve"
      subtitle="Intraday portfolio growth & equity progression"
      action={
        displayEquity !== null ? (
          <div className="flex items-center gap-2 bg-sky-950/60 border border-sky-800/60 px-2.5 py-1 rounded">
            <span className="text-[11px] text-sky-400 font-mono">
              {hoveredEquity !== null ? 'POINT EQUITY:' : 'LIVE EQUITY:'}
            </span>
            <span className="text-xs font-mono font-bold text-sky-200">
              {formatCurrency(displayEquity)}
            </span>
          </div>
        ) : undefined
      }
    >
      <div className="relative w-full h-[220px] rounded-lg overflow-hidden border border-slate-800/80 bg-[#090d16]">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#090d16]/80 backdrop-blur-xs">
            <Spinner size="md" />
            <span className="text-xs text-slate-400 mt-2 font-mono">
              Loading equity curve...
            </span>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </Card>
  );
};
