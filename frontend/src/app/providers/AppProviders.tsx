import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { WebSocketProvider } from './WebSocketProvider';

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <BrowserRouter>
      <WebSocketProvider>
        {children}
      </WebSocketProvider>
    </BrowserRouter>
  );
};
