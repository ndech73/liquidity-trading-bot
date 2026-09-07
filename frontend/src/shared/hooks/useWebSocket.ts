import { useEffect, useState } from 'react';
import { wsClient } from '../services/websocketClient';
import { WebSocketMessage } from '../types/api';

export const useWebSocket = (channel?: string) => {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((msg) => {
      if (!channel || msg.channel === channel) {
        setLastMessage(msg);
      }
    });
    return () => unsubscribe();
  }, [channel]);

  return { lastMessage, send: wsClient.send.bind(wsClient) };
};
