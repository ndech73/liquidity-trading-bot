import React, { createContext, useContext, useEffect, useState } from 'react';
import { wsClient, WebSocketStatus } from '../../shared/services/websocketClient';

interface WebSocketContextType {
  isConnected: boolean;
  status: WebSocketStatus;
  requestSync: () => void;
}

const WebSocketContext = createContext<WebSocketContextType>({
  isConnected: false,
  status: 'disconnected',
  requestSync: () => {},
});

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<WebSocketStatus>(wsClient.status);

  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.onStatusChange((newStatus) => {
      setStatus(newStatus);
    });
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected: status === 'connected',
        status,
        requestSync: () => wsClient.requestSync(),
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = () => useContext(WebSocketContext);

