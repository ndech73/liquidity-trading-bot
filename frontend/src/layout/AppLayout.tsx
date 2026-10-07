import React from 'react';
import { Outlet } from 'react-router-dom';
import { Topbar } from './Topbar';
import { AlertToast } from './AlertToast';
import { useAccount } from '../shared/hooks/useAccount';

export const AppLayout: React.FC = () => {
  const { account, isWsConnected } = useAccount();

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
      <Topbar
        botStatus={account?.status || 'RUNNING'}
        accountBalance={account?.equity ?? 23.45}
        isWsConnected={isWsConnected}
      />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <AlertToast />
    </div>
  );
};
