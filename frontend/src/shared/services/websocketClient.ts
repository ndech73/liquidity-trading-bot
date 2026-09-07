import { ENV } from '../../config/env';
import { WebSocketMessage } from '../types/api';

type MessageHandler = (data: WebSocketMessage) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectInterval = 3000;
  private isExplicitlyClosed = false;

  public connect(url: string = ENV.WS_URL) {
    this.isExplicitlyClosed = false;
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.info('[WebSocket] Connected to', url);
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
        if (!this.isExplicitlyClosed) {
          console.warn('[WebSocket] Disconnected. Reconnecting in', this.reconnectInterval, 'ms');
          setTimeout(() => this.connect(url), this.reconnectInterval);
        }
      };

      this.ws.onerror = (err) => {
        console.error('[WebSocket] Socket error:', err);
      };
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err);
    }
  }

  public subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  public send(data: unknown) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WebSocketClient();
