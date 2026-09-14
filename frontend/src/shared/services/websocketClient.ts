import { ENV } from '../../config/env';
import { WebSocketMessage } from '../types/api';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
type MessageHandler = (data: WebSocketMessage) => void;
type StatusListener = (status: WebSocketStatus) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectInterval = 3000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private isExplicitlyClosed = false;
  private _status: WebSocketStatus = 'disconnected';

  public get status(): WebSocketStatus {
    return this._status;
  }

  public get isConnected(): boolean {
    return this._status === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }

  private setStatus(newStatus: WebSocketStatus) {
    if (this._status !== newStatus) {
      this._status = newStatus;
      this.statusListeners.forEach((listener) => listener(newStatus));
    }
  }

  private candidateIndex = 0;

  private getCandidateUrls(primaryUrl?: string): string[] {
    const urls: string[] = [];
    if (primaryUrl) urls.push(primaryUrl);
    if (ENV.WS_URL && !urls.includes(ENV.WS_URL)) urls.push(ENV.WS_URL);

    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const candidates = [
        'ws://127.0.0.1:8000/ws',
        'ws://127.0.0.1:8000/api/ws',
        `${protocol}//${window.location.host}/ws`,
        `${protocol}//${window.location.host}/api/ws`,
      ];
      candidates.forEach((u) => {
        if (!urls.includes(u)) urls.push(u);
      });
    }
    return urls;
  }

  public connect(requestedUrl?: string) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const candidates = this.getCandidateUrls(requestedUrl);
    const targetUrl = candidates[this.candidateIndex % candidates.length] || ENV.WS_URL;

    this.isExplicitlyClosed = false;
    this.setStatus('connecting');

    try {
      this.ws = new WebSocket(targetUrl);

      this.ws.onopen = () => {
        this.setStatus('connected');
        console.info('[WebSocket] Connected to', targetUrl);
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handlers.forEach((handler) => handler(payload));
        } catch (e) {
          console.error('[WebSocket] Message parse error:', e);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.setStatus('disconnected');
        if (!this.isExplicitlyClosed) {
          this.candidateIndex++;
          console.warn('[WebSocket] Disconnected. Cycling to next endpoint in', this.reconnectInterval, 'ms');
          if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
          this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectInterval);
        }
      };

      this.ws.onerror = (err) => {
        this.setStatus('error');
        console.error('[WebSocket] Socket error on', targetUrl, err);
      };
    } catch (err) {
      this.setStatus('error');
      console.error('[WebSocket] Connection attempt failed for', targetUrl, err);
      if (!this.isExplicitlyClosed) {
        this.candidateIndex++;
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectInterval);
      }
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ action: 'ping' });
      }
    }, 15000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  public subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  public onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this._status);
    return () => this.statusListeners.delete(listener);
  }

  public send(data: unknown) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  public requestSync() {
    this.send({ action: 'sync' });
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }
}

export const wsClient = new WebSocketClient();

