import { LiquidityAlert, SweepNotice } from '../types/notification';

type AlertListener = (alert: LiquidityAlert) => void;
type SweepListener = (sweep: SweepNotice) => void;

class NotificationService {
  private soundEnabled: boolean = true;
  private desktopEnabled: boolean = true;
  private audioCtx: AudioContext | null = null;
  private alertListeners: Set<AlertListener> = new Set();
  private sweepListeners: Set<SweepListener> = new Set();
  private recentAlerts: LiquidityAlert[] = [];
  private originalTitle: string = typeof document !== 'undefined' ? document.title : 'Liquidity Trading System';
  private titleInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      try {
        const soundPref = localStorage.getItem('liquidity_sound_enabled');
        if (soundPref !== null) this.soundEnabled = soundPref === 'true';

        const desktopPref = localStorage.getItem('liquidity_desktop_enabled');
        if (desktopPref !== null) this.desktopEnabled = desktopPref === 'true';
      } catch {
        // ignore
      }

      // Restore title on focus
      window.addEventListener('focus', () => {
        this.clearTitleFlash();
      });
    }
  }

  public get isSoundEnabled(): boolean {
    return this.soundEnabled;
  }

  public setSoundEnabled(enabled: boolean) {
    this.soundEnabled = enabled;
    try {
      localStorage.setItem('liquidity_sound_enabled', String(enabled));
    } catch {
      // ignore
    }
  }

  public get isDesktopEnabled(): boolean {
    return this.desktopEnabled;
  }

  public setDesktopEnabled(enabled: boolean) {
    this.desktopEnabled = enabled;
    try {
      localStorage.setItem('liquidity_desktop_enabled', String(enabled));
    } catch {
      // ignore
    }
  }

  public get permission(): NotificationPermission {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return 'denied';
    }
    return Notification.permission;
  }

  public async requestPermission(): Promise<NotificationPermission> {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return 'denied';
    }
    try {
      const res = await Notification.requestPermission();
      return res;
    } catch (e) {
      console.warn('[NotificationService] Permission request error:', e);
      return 'denied';
    }
  }

  /** Plays a smooth harmonic chime using HTML5 Web Audio synthesizer */
  public playChime(isSell: boolean = false) {
    if (!this.soundEnabled || typeof window === 'undefined') return;

    try {
      const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtxClass) return;

      if (!this.audioCtx || this.audioCtx.state === 'closed') {
        this.audioCtx = new AudioCtxClass();
      }

      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      const ctx = this.audioCtx;
      const now = ctx.currentTime;

      // Harmonic chord: BUY = rising major triad (523Hz -> 659Hz -> 784Hz), SELL = descending punch (784Hz -> 659Hz -> 523Hz)
      const freqs = isSell ? [783.99, 659.25, 523.25] : [523.25, 659.25, 783.99];

      freqs.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + idx * 0.1);

        gain.gain.setValueAtTime(0.001, now + idx * 0.1);
        gain.gain.exponentialRampToValueAtTime(0.18, now + idx * 0.1 + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.1 + 0.35);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + idx * 0.1);
        osc.stop(now + idx * 0.1 + 0.36);
      });
    } catch (e) {
      console.debug('[NotificationService] Audio chime suppressed:', e);
    }
  }

  /** Dispatches an actionable desktop notification and updates system state */
  public dispatchAlert(alert: LiquidityAlert) {
    // Add to in-memory history
    this.recentAlerts.unshift(alert);
    if (this.recentAlerts.length > 50) {
      this.recentAlerts.pop();
    }

    // Play synthesized sound
    this.playChime(alert.direction === 'SELL');

    // Trigger Native OS/Browser Notification
    if (this.desktopEnabled && typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        try {
          const notif = new Notification(`🚨 Liquidity Signal: ${alert.symbol} ${alert.direction}`, {
            body: `Entry: ${alert.entryPrice} | SL: ${alert.stopLoss} | TP1: ${alert.takeProfit1}\n${alert.reason}`,
            icon: '/favicon.svg',
            badge: '/favicon.svg',
            tag: alert.id,
            requireInteraction: true,
          });

          notif.onclick = () => {
            window.focus();
            notif.close();
          };
        } catch (e) {
          console.debug('[NotificationService] Desktop notification error:', e);
        }
      }
    }

    // Flash tab title if document is hidden or inactive
    if (typeof document !== 'undefined' && document.hidden) {
      this.flashTitle(`🚨 (${alert.symbol} ${alert.direction}) Signal!`);
    }

    // Notify React listeners
    this.alertListeners.forEach((fn) => {
      try {
        fn(alert);
      } catch (err) {
        console.error(err);
      }
    });
  }

  public dispatchSweep(sweep: SweepNotice) {
    this.sweepListeners.forEach((fn) => {
      try {
        fn(sweep);
      } catch (err) {
        console.error(err);
      }
    });
  }

  public onAlert(listener: AlertListener): () => void {
    this.alertListeners.add(listener);
    return () => this.alertListeners.delete(listener);
  }

  public onSweep(listener: SweepListener): () => void {
    this.sweepListeners.add(listener);
    return () => this.sweepListeners.delete(listener);
  }

  public getHistory(): LiquidityAlert[] {
    return [...this.recentAlerts];
  }

  public setHistory(alerts: LiquidityAlert[]) {
    this.recentAlerts = [...alerts];
  }

  private flashTitle(alertText: string) {
    this.clearTitleFlash();
    let isOriginal = false;
    this.titleInterval = setInterval(() => {
      if (typeof document !== 'undefined') {
        document.title = isOriginal ? this.originalTitle : alertText;
        isOriginal = !isOriginal;
      }
    }, 1000);
  }

  private clearTitleFlash() {
    if (this.titleInterval) {
      clearInterval(this.titleInterval);
      this.titleInterval = null;
    }
    if (typeof document !== 'undefined') {
      document.title = this.originalTitle;
    }
  }
}

export const notificationService = new NotificationService();
