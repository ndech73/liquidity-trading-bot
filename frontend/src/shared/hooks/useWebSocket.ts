import { useEffect, useState, useCallback } from 'react';
import { wsClient, WebSocketStatus } from '../services/websocketClient';
import { WebSocketMessage } from '../types/api';

export const useWebSocket = <T = unknown>(channel?: string) => {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage<T> | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(wsClient.isConnected);
  const [status, setStatus] = useState<WebSocketStatus>(wsClient.status);

  useEffect(() => {
    const unsubMsg = wsClient.subscribe((msg) => {
      if (!channel || msg.channel === channel) {
        setLastMessage(msg as WebSocketMessage<T>);
      }
    });

    const unsubStatus = wsClient.onStatusChange((newStatus) => {
      setStatus(newStatus);
      setIsConnected(newStatus === 'connected');
    });

    return () => {
      unsubMsg();
      unsubStatus();
    };
  }, [channel]);

  const send = useCallback((data: unknown) => {
    wsClient.send(data);
  }, []);

  return { lastMessage, send, isConnected, status };
};

