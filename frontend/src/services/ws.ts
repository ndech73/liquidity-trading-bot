import { wsClient } from '../shared/services/websocketClient';
import { ENV } from '../config/env';

// Unified WebSocket: provides backward compatibility while using the shared singleton socket manager
export function connectMarketSocket(url: string = ENV.WS_URL) {
  wsClient.connect(url);
  return wsClient;
}

export { wsClient };
export default wsClient;
