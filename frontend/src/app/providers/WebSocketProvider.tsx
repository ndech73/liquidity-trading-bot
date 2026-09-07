import React, { createContext, useContext, useEffect, useState } from 'react';
import { wsClient } from '../../shared/services/websocketClient';

interface WebSocketContextType {
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType>({ isConnected: false });

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    wsClient.connect();
    setIsConnected(true);
    return () => {
      setIsConnected(false);
      wsClient.disconnect();
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = () => useContext(WebSocketContext);
