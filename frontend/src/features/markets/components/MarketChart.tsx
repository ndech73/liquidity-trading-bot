import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  LineSeries,
  LineStyle,
  IChartApi,
  ISeriesApi,
  IPriceLine,
  Time,
  UTCTimestamp,
  createSeriesMarkers,
  ISeriesMarkersPluginApi,
  SeriesMarker,
} from 'lightweight-charts';
import { Card } from '../../../shared/components/Card';
import { ChartToolbar } from './ChartToolbar';
import { getCandleData } from '../services/marketService';
import { getLiquidityZones } from '../../analysis/services/analysisService';
import { LiquidityZone } from '../../analysis/types/analysis.types';
import { Spinner } from '../../../shared/components/Spinner';

export interface StructuralLiquidityLevel {
  id: string;
  type: 'BSL' | 'SSL';
  price: number;
  originTime: number; // Unix timestamp in seconds
  sweepTime?: number | null; // Unix timestamp in seconds
  sweepPrice?: number | null;
  status: 'ACTIVE' | 'SWEPT';
  touches: number;
}

export function consolidateLiquidityZones(
  rawZones: LiquidityZone[],
  pipSize: number = 0.0001
): StructuralLiquidityLevel[] {
  if (!rawZones || rawZones.length === 0) return [];

  const parsed = rawZones
    .map((z) => {
      const isBsl =
        z.type === 'BUY_SIDE' ||
        Boolean(z.liquidityType && z.liquidityType.toLowerCase().includes('high'));
      const type: 'BSL' | 'SSL' = isBsl ? 'BSL' : 'SSL';
      const price = z.price || (isBsl ? z.priceHigh : z.priceLow) || 0;
      if (price <= 0) return null;

      let originTime = 0;
      if (z.originTime) {
        originTime = z.originTime;
      } else if (z.createdAt) {
        const ms = new Date(z.createdAt).getTime();
        if (!isNaN(ms)) originTime = Math.floor(ms / 1000);
      }

      let sweepTime: number | null = null;
      if (z.sweepTime) {
        sweepTime = z.sweepTime;
      } else if (z.sweptAt) {
        const ms = new Date(z.sweptAt).getTime();
        if (!isNaN(ms)) sweepTime = Math.floor(ms / 1000);
      }

      const isSwept =
        z.status === 'SWEPT' ||
        z.status === 'swept' ||
        z.isSwept === true ||
        Boolean(sweepTime);

      return {
        id: z.id,
        type,
        price,
        originTime,
        sweepTime: isSwept ? sweepTime : null,
        sweepPrice: z.sweepPrice || null,
        status: (isSwept ? 'SWEPT' : 'ACTIVE') as 'ACTIVE' | 'SWEPT',
        touches: z.touches || 1,
      };
    })
    .filter((z): z is NonNullable<typeof z> => z !== null && z.originTime > 0);

  const bslList = parsed.filter((z) => z.type === 'BSL');
  const sslList = parsed.filter((z) => z.type === 'SSL');

  const consolidateGroup = (group: typeof parsed, isBslGroup: boolean): StructuralLiquidityLevel[] => {
    if (group.length === 0) return [];

    const sorted = [...group].sort((a, b) =>
      isBslGroup ? b.price - a.price : a.price - b.price
    );

    const priceThreshold = pipSize * 2.5; // Consolidate within 2.5 pips into one structural level
    const clusters: (typeof parsed)[] = [];

    for (const item of sorted) {
      const match = clusters.find((c) =>
        c.some((existing) => Math.abs(existing.price - item.price) <= priceThreshold)
      );

      if (match) {
        match.push(item);
      } else {
        clusters.push([item]);
      }
    }

    return clusters.map((cluster) => {
      const keyPrice = isBslGroup
        ? Math.max(...cluster.map((c) => c.price))
        : Math.min(...cluster.map((c) => c.price));

      const earliestOrigin = Math.min(...cluster.map((c) => c.originTime));
      const anySwept = cluster.some((c) => c.status === 'SWEPT');
      const sweepTimes = cluster.map((c) => c.sweepTime).filter((t): t is number => Boolean(t) && t! > 0);
      const earliestSweep = sweepTimes.length > 0 ? Math.min(...sweepTimes) : null;
      const sweepPrices = cluster.map((c) => c.sweepPrice).filter((p): p is number => Boolean(p));
      const avgSweepPrice = sweepPrices.length > 0 ? sweepPrices[0] : null;
      const totalTouches = cluster.reduce((acc, c) => acc + (c.touches || 1), 0);

      return {
        id: `liq-${isBslGroup ? 'bsl' : 'ssl'}-${keyPrice.toFixed(5)}-${earliestOrigin}`,
        type: isBslGroup ? 'BSL' : 'SSL',
        price: keyPrice,
        originTime: earliestOrigin,
        sweepTime: anySwept ? earliestSweep : null,
        sweepPrice: anySwept ? avgSweepPrice : null,
        status: anySwept ? 'SWEPT' : 'ACTIVE',
        touches: Math.max(totalTouches, cluster.length),
      };
    });
  };

  const consolidatedBsl = consolidateGroup(bslList, true);
  const consolidatedSsl = consolidateGroup(sslList, false);

  const activeBsl = consolidatedBsl.filter((z) => z.status === 'ACTIVE');
  const sweptBsl = consolidatedBsl
    .filter((z) => z.status === 'SWEPT')
    .sort((a, b) => (b.sweepTime || b.originTime) - (a.sweepTime || a.originTime))
    .slice(0, 4);

  const activeSsl = consolidatedSsl.filter((z) => z.status === 'ACTIVE');
  const sweptSsl = consolidatedSsl
    .filter((z) => z.status === 'SWEPT')
    .sort((a, b) => (b.sweepTime || b.originTime) - (a.sweepTime || a.originTime))
    .slice(0, 4);

  return [...activeBsl, ...sweptBsl, ...activeSsl, ...sweptSsl];
}

interface CandleItem {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeOverlayProps {
  openPrice?: number;
  closePrice?: number | null;
  stopLoss?: number | null;
  takeProfit?: number | null;
  orderType?: string;
  ticket?: number;
  entryTimestamp?: string | null;
  exitTimestamp?: string | null;
}

export interface MarketChartProps {
  symbol: string;
  title?: string;
  isSidebarCollapsed?: boolean;
  tradeOverlay?: TradeOverlayProps;
  className?: string;
}

export const MarketChart: React.FC<MarketChartProps> = ({
  symbol,
  title,
  isSidebarCollapsed,
  tradeOverlay,
  className = '',
}) => {
  const [timeframe, setTimeframe] = useState('M15');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastBar, setLastBar] = useState<CandleItem | null>(null);
  const [zones, setZones] = useState<LiquidityZone[]>([]);
  const [showLiquidity, setShowLiquidity] = useState(true);
  const [showTargets, setShowTargets] = useState(true);

  // Standard height (comfortable 520px, focus is maximum horizontal width)
  const chartHeight = 520;

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const liquiditySeriesRef = useRef<ISeriesApi<'Line'>[]>([]);
  const candleTimesRef = useRef<number[]>([]);
  const latestCloseRef = useRef<number>(0);

  // Keep state and props mirrored in refs for zero-recreation callbacks
  const zonesRef = useRef<LiquidityZone[]>([]);
  zonesRef.current = zones;
  const overlayRef = useRef<TradeOverlayProps | undefined>(tradeOverlay);
  overlayRef.current = tradeOverlay;
  const showLiquidityRef = useRef(showLiquidity);
  showLiquidityRef.current = showLiquidity;
  const showTargetsRef = useRef(showTargets);
  showTargetsRef.current = showTargets;

  // Snaps any ISO/date/timestamp to the closest existing candle timestamp
  const snapToCandleTime = useCallback(
    (target: string | number | undefined | null, candleTimes: number[]): Time | null => {
      if (!target || candleTimes.length === 0) return null;
      let targetSec: number;
      if (typeof target === 'number') {
        targetSec = target > 1e11 ? Math.floor(target / 1000) : Math.floor(target);
      } else {
        const parsed = new Date(target).getTime();
        if (isNaN(parsed)) return null;
        targetSec = Math.floor(parsed / 1000);
      }
      if (targetSec <= 0) return null;

      let closest = candleTimes[0];
      let minDiff = Math.abs(candleTimes[0] - targetSec);
      for (let i = 1; i < candleTimes.length; i++) {
        const diff = Math.abs(candleTimes[i] - targetSec);
        if (diff < minDiff) {
          minDiff = diff;
          closest = candleTimes[i];
        }
        if (diff === 0) break;
      }
      return closest as Time;
    },
    []
  );

  // Updates pinpoint candle markers and clean, discrete trade/target price lines
  const renderMarkingsAndLines = useCallback(() => {
    if (!candleSeriesRef.current) return;
    const series = candleSeriesRef.current;
    const candleTimes = candleTimesRef.current;
    const isJpy = symbol.toUpperCase().includes('JPY');
    const pipMult = isJpy ? 100 : 10000;
    const overlay = overlayRef.current;
    const activeZones = zonesRef.current;
    const liquidityVisible = showLiquidityRef.current;
    const targetsVisible = showTargetsRef.current;
    const currentClose = latestCloseRef.current;

    // 1. Clean existing lines & liquidity series
    priceLinesRef.current.forEach((line) => {
      try {
        series.removePriceLine(line);
      } catch {
        // ignore
      }
    });
    priceLinesRef.current = [];

    if (chartRef.current && liquiditySeriesRef.current.length > 0) {
      liquiditySeriesRef.current.forEach((s) => {
        try {
          chartRef.current?.removeSeries(s);
        } catch {
          // ignore
        }
      });
      liquiditySeriesRef.current = [];
    }

    const markers: SeriesMarker<Time>[] = [];

    // 2. Trade Overlay Mode (Entry, SL, TP, Exit)
    if (overlay) {
      const isBuy = overlay.orderType === 'BUY';
      const entryTime =
        snapToCandleTime(overlay.entryTimestamp, candleTimes) ||
        (candleTimes.length > 20 ? (candleTimes[candleTimes.length - 20] as Time) : null);

      // Pinpoint Entry Marker & Solid Entry Line
      if (overlay.openPrice && overlay.openPrice > 0) {
        const entryLine = series.createPriceLine({
          price: overlay.openPrice,
          color: '#38bdf8', // sky-400
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: `ENTRY ${overlay.orderType ?? ''} (#${overlay.ticket ?? ''}): ${overlay.openPrice.toFixed(5)}`,
        });
        priceLinesRef.current.push(entryLine);

        if (entryTime) {
          markers.push({
            time: entryTime,
            position: isBuy ? 'belowBar' : 'aboveBar',
            shape: isBuy ? 'arrowUp' : 'arrowDown',
            color: '#38bdf8',
            text: `ENTRY ${overlay.orderType ?? ''} @ ${overlay.openPrice.toFixed(5)}`,
            size: 2,
            id: `trade-entry-${overlay.ticket ?? 'current'}`,
          });
        }
      }

      // Pinpoint Stop Loss Marker & Dashed Red Line
      if (overlay.stopLoss && overlay.stopLoss > 0) {
        const slPips = overlay.openPrice
          ? (Math.abs(overlay.openPrice - overlay.stopLoss) * pipMult).toFixed(1)
          : '0.0';
        const slLine = series.createPriceLine({
          price: overlay.stopLoss,
          color: '#f43f5e', // rose-500
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `🛑 STOP LOSS: ${overlay.stopLoss.toFixed(5)} (-${slPips} pips)`,
        });
        priceLinesRef.current.push(slLine);

        if (entryTime) {
          markers.push({
            time: entryTime,
            position: isBuy ? 'belowBar' : 'aboveBar',
            shape: 'square',
            color: '#f43f5e',
            text: `🛑 SL @ ${overlay.stopLoss.toFixed(5)}`,
            size: 1.5,
            id: `trade-sl-${overlay.ticket ?? 'current'}`,
          });
        }
      }

      // Pinpoint Take Profit Marker & Dashed Green Line
      if (overlay.takeProfit && overlay.takeProfit > 0) {
        const tpPips = overlay.openPrice
          ? (Math.abs(overlay.takeProfit - overlay.openPrice) * pipMult).toFixed(1)
          : '0.0';
        const tpLine = series.createPriceLine({
          price: overlay.takeProfit,
          color: '#10b981', // emerald-500
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `🎯 TAKE PROFIT: ${overlay.takeProfit.toFixed(5)} (+${tpPips} pips)`,
        });
        priceLinesRef.current.push(tpLine);

        if (entryTime) {
          markers.push({
            time: entryTime,
            position: isBuy ? 'aboveBar' : 'belowBar',
            shape: 'square',
            color: '#10b981',
            text: `🎯 TP @ ${overlay.takeProfit.toFixed(5)}`,
            size: 1.5,
            id: `trade-tp-${overlay.ticket ?? 'current'}`,
          });
        }
      }

      // Pinpoint Exit Marker & Dotted Purple Line
      if (overlay.closePrice && overlay.closePrice > 0) {
        const exitTime =
          snapToCandleTime(overlay.exitTimestamp, candleTimes) ||
          (candleTimes.length > 0 ? (candleTimes[candleTimes.length - 1] as Time) : null);

        const exitLine = series.createPriceLine({
          price: overlay.closePrice,
          color: '#c084fc', // purple-400
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          title: `🏁 CLOSED: ${overlay.closePrice.toFixed(5)}`,
        });
        priceLinesRef.current.push(exitLine);

        if (exitTime) {
          markers.push({
            time: exitTime,
            position: 'inBar',
            shape: 'circle',
            color: '#c084fc',
            text: `🏁 CLOSED @ ${overlay.closePrice.toFixed(5)}`,
            size: 2,
            id: `trade-exit-${overlay.ticket ?? 'current'}`,
          });
        }
      }
    }

    // 3. Structural Liquidity Levels (Origin -> Forward Extension -> Sweep)
    if (liquidityVisible && activeZones && activeZones.length > 0 && candleTimes.length > 0) {
      const pipSize = isJpy ? 0.01 : 0.0001;
      const structuralLevels = consolidateLiquidityZones(activeZones, pipSize);
      const firstCandleTime = candleTimes[0];
      const lastCandleTime = candleTimes[candleTimes.length - 1];

      structuralLevels.forEach((level) => {
        const isBsl = level.type === 'BSL';
        const isActive = level.status === 'ACTIVE';

        // 3a. Locate origin candle time (clamped if originated before loaded series)
        const originBarTime = snapToCandleTime(level.originTime, candleTimes);
        let startSec: number;
        if (originBarTime) {
          startSec = typeof originBarTime === 'number' ? originBarTime : Number(originBarTime);
        } else if (level.originTime <= firstCandleTime) {
          startSec = firstCandleTime;
        } else {
          return;
        }

        // 3b. Locate sweep candle time or current live candle
        let endSec: number;
        if (!isActive && level.sweepTime) {
          const sweepBarTime = snapToCandleTime(level.sweepTime, candleTimes);
          endSec = sweepBarTime
            ? (typeof sweepBarTime === 'number' ? sweepBarTime : Number(sweepBarTime))
            : lastCandleTime;
        } else {
          endSec = lastCandleTime;
        }

        if (endSec < startSec) endSec = startSec;

        // 3c. Draw horizontal line segment from origin to sweep/end
        const segmentTimes = candleTimes.filter((t) => t >= startSec && t <= endSec);
        if (segmentTimes.length === 1 && endSec > startSec) {
          segmentTimes.push(endSec);
        }

        if (segmentTimes.length >= 2 && chartRef.current) {
          const lineData = segmentTimes.map((t) => ({
            time: t as UTCTimestamp,
            value: level.price,
          }));

          const color = isActive
            ? isBsl ? '#f43f5e' : '#10b981'
            : isBsl ? 'rgba(244, 63, 94, 0.45)' : 'rgba(16, 185, 129, 0.45)';

          const lineWidth = isActive ? 2 : 1;
          const lineStyle = isActive ? LineStyle.Solid : LineStyle.Dashed;

          const lineSeries = chartRef.current.addSeries(LineSeries, {
            color,
            lineWidth,
            lineStyle,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
          });
          lineSeries.setData(lineData);
          liquiditySeriesRef.current.push(lineSeries);
        }

        // 3d. Single clean origin marker at originating candle
        const originColor = isActive
          ? isBsl ? '#f43f5e' : '#10b981'
          : isBsl ? 'rgba(244, 63, 94, 0.65)' : 'rgba(16, 185, 129, 0.65)';

        markers.push({
          time: startSec as Time,
          position: isBsl ? 'aboveBar' : 'belowBar',
          shape: 'circle',
          color: originColor,
          text: `${isBsl ? 'BSL' : 'SSL'} ${level.price.toFixed(5)}${
            level.touches > 1 ? ` (${level.touches}x)` : ''
          }`,
          size: 1.5,
          id: `orig-${level.id}`,
        });

        // 3e. Single clean sweep marker at sweep candle (ONLY when swept)
        if (!isActive && level.sweepTime && endSec !== startSec) {
          markers.push({
            time: endSec as Time,
            position: isBsl ? 'aboveBar' : 'belowBar',
            shape: 'circle',
            color: '#f59e0b', // amber
            text: 'SWEPT',
            size: 2,
            id: `sweep-${level.id}`,
          });
        }
      });

      // 4. Clean Key Targets (ONLY the immediate nearest active BSL & SSL, not dozens of cluttering lines!)
      if (targetsVisible && !overlay && currentClose > 0) {
        const unswept = structuralLevels.filter((z) => z.status === 'ACTIVE');

        // Nearest active BSL above price
        const nearestBsl = unswept
          .filter((z) => z.type === 'BSL' && z.price > currentClose)
          .sort((a, b) => a.price - b.price)[0];

        if (nearestBsl) {
          const bslPrice = nearestBsl.price;
          const diffPips = ((bslPrice - currentClose) * pipMult).toFixed(1);
          const bslLine = series.createPriceLine({
            price: bslPrice,
            color: '#f43f5e',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `🎯 NEAREST BSL: ${bslPrice.toFixed(5)} (+${diffPips} pips)`,
          });
          priceLinesRef.current.push(bslLine);
        }

        // Nearest active SSL below price
        const nearestSsl = unswept
          .filter((z) => z.type === 'SSL' && z.price < currentClose)
          .sort((a, b) => b.price - a.price)[0];

        if (nearestSsl) {
          const sslPrice = nearestSsl.price;
          const diffPips = ((currentClose - sslPrice) * pipMult).toFixed(1);
          const sslLine = series.createPriceLine({
            price: sslPrice,
            color: '#10b981',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `🛡️ NEAREST SSL: ${sslPrice.toFixed(5)} (-${diffPips} pips)`,
          });
          priceLinesRef.current.push(sslLine);
        }
      }
    }

    // Collision prevention: consolidate text for markers on the exact same candle & side
    const consolidatedMarkers: SeriesMarker<Time>[] = [];
    const markerMap = new Map<string, SeriesMarker<Time>>();

    for (const m of markers) {
      const key = `${m.time}_${m.position}`;
      if (!markerMap.has(key)) {
        markerMap.set(key, m);
        consolidatedMarkers.push(m);
      } else {
        const existing = markerMap.get(key)!;
        if (existing.text && m.text && !existing.text.includes(m.text)) {
          existing.text = `${existing.text} | ${m.text}`;
        }
      }
    }

    // Sort markers in strictly ascending order by timestamp as required by Lightweight Charts
    consolidatedMarkers.sort((a, b) => (a.time as number) - (b.time as number));

    if (markersPluginRef.current) {
      markersPluginRef.current.setMarkers(consolidatedMarkers);
    }
  }, [symbol, snapToCandleTime]);

  // Load and apply candle data without recreating chart canvas
  const loadCandleData = useCallback(async () => {
    if (!symbol) return;
    try {
      const tfParam = timeframe.toLowerCase();
      const [res, zonesData] = await Promise.all([
        getCandleData(symbol, tfParam, 120),
        getLiquidityZones(symbol, tfParam).catch(() => []),
      ]);

      const fetchedZones = zonesData || [];
      zonesRef.current = fetchedZones;
      setZones(fetchedZones);

      if (res && res.candles && res.candles.length > 0) {
        const candleData = res.candles.map((c: CandleItem) => ({
          time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        candleData.sort((a, b) => (a.time as number) - (b.time as number));
        const uniqueCandles = candleData.filter(
          (v, i, a) => i === 0 || (v.time as number) > (a[i - 1].time as number)
        );

        candleTimesRef.current = uniqueCandles.map((c) => c.time as number);
        const last = uniqueCandles[uniqueCandles.length - 1];
        if (last) {
          latestCloseRef.current = last.close;
        }

        if (candleSeriesRef.current) {
          candleSeriesRef.current.setData(uniqueCandles);
          renderMarkingsAndLines();
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
  }, [symbol, timeframe, renderMarkingsAndLines]);

  // Initialize Lightweight Charts instance (runs ONCE per symbol/timeframe)
  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth || 800,
      height: chartHeight,
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
          top: 0.08,
          bottom: 0.08,
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

    const markersPlugin = createSeriesMarkers(candleSeries);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    markersPluginRef.current = markersPlugin;

    // Handle container resize cleanly (dynamic full-width expansion)
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
    loadCandleData();

    // Auto-refresh candles every 5 seconds without canvas recreation
    const interval = setInterval(loadCandleData, 5000);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      clearInterval(interval);
      liquiditySeriesRef.current.forEach((s) => {
        try {
          chart.removeSeries(s);
        } catch {
          // ignore
        }
      });
      liquiditySeriesRef.current = [];
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      markersPluginRef.current = null;
    };
  }, [symbol, timeframe, loadCandleData]);

  // Update markings and lines when toggles or overlay change (NO chart recreation)
  useEffect(() => {
    renderMarkingsAndLines();
  }, [showLiquidity, showTargets, zones, tradeOverlay, renderMarkingsAndLines]);

  // Adjust chart width immediately when sidebar collapse state toggles
  useEffect(() => {
    const timer = setTimeout(() => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [isSidebarCollapsed]);

  const handleFitContent = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  };

  const priceChange = lastBar ? lastBar.close - lastBar.open : 0;
  const pctChange = lastBar && lastBar.open > 0 ? (priceChange / lastBar.open) * 100 : 0;
  const isUp = priceChange >= 0;

  const pipSize = symbol.toUpperCase().includes('JPY') ? 0.01 : 0.0001;
  const structuralLevels = consolidateLiquidityZones(zones, pipSize);
  const activeBslCount = structuralLevels.filter((z) => z.type === 'BSL' && z.status === 'ACTIVE').length;
  const activeSslCount = structuralLevels.filter((z) => z.type === 'SSL' && z.status === 'ACTIVE').length;
  const sweptCount = structuralLevels.filter((z) => z.status === 'SWEPT').length;

  return (
    <Card title={title || `${symbol} Candlestick Feed & Liquidity Map`} className={`w-full ${className}`}>
      <div className="space-y-3 w-full">
        {/* Top chart header with live price metrics, size controls and toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <ChartToolbar
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            showLiquidity={showLiquidity}
            onToggleLiquidity={() => setShowLiquidity((prev) => !prev)}
            showTargets={showTargets}
            onToggleTargets={() => setShowTargets((prev) => !prev)}
            onFitContent={handleFitContent}
          />

          {lastBar && (
            <div className="flex items-center gap-3 text-xs font-mono w-full justify-between sm:justify-start">
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

              {structuralLevels.length > 0 && (
                <div className="hidden md:flex items-center gap-3 text-[11px] text-slate-400 font-sans">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span>Active BSL ({activeBslCount})</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>Active SSL ({activeSslCount})</span>
                  </div>
                  {sweptCount > 0 && (
                    <div className="flex items-center gap-1 text-amber-400">
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      <span>Swept ({sweptCount})</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chart Canvas Container — 100% full width, comfortable 520px height, rock solid */}
        <div
          ref={chartContainerRef}
          style={{ height: `${chartHeight}px` }}
          className="relative w-full rounded-lg overflow-hidden border border-slate-800 bg-[#090d16]"
        >
          {isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#090d16]/80 backdrop-blur-xs">
              <Spinner size="lg" />
              <span className="text-xs text-slate-400 mt-2 font-mono">
                Streaming {symbol} {timeframe} candles & pinpoint liquidity levels...
              </span>
            </div>
          )}

          {error && !isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#090d16]/90 p-4 text-center">
              <p className="text-sm font-semibold text-rose-400">{error}</p>
              <button
                onClick={loadCandleData}
                className="mt-3 px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition cursor-pointer"
              >
                Retry Fetch
              </button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
