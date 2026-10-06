import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { MobileNavigation } from './MobileNavigation';
import { AlertToast } from './AlertToast';
import { useAccount } from '../shared/hooks/useAccount';

export const AppLayout: React.FC = () => {
  const { account, isWsConnected } = useAccount();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem('liquidity_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const handleToggle = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('liquidity_sidebar_collapsed', String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  const handleExpand = () => {
    setIsCollapsed(false);
    try {
      localStorage.setItem('liquidity_sidebar_collapsed', 'false');
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar
        isCollapsed={isCollapsed}
        onToggle={handleToggle}
        onExpand={handleExpand}
      />
      <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0 transition-all duration-300">
        <Topbar
          botStatus={account?.status || 'OFFLINE'}
          accountBalance={account?.equity ?? 0}
          isWsConnected={isWsConnected}
        />
        <main className="flex-1 overflow-y-auto">
          <Outlet context={{ isSidebarCollapsed: isCollapsed }} />
        </main>
      </div>
      <AlertToast />
      <MobileNavigation />
    </div>
  );
};
