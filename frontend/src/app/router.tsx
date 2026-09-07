import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '../layout/AppLayout';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { MarketsPage } from '../features/markets/MarketsPage';
import { TradesPage } from '../features/trades/TradesPage';
import { AnalysisPage } from '../features/analysis/AnalysisPage';
import { ForensicsPage } from '../features/forensics/ForensicsPage';
import { PerformancePage } from '../features/performance/PerformancePage';
import { SettingsPage } from '../features/settings/SettingsPage';

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/markets" element={<MarketsPage />} />
        <Route path="/trades" element={<TradesPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/forensics" element={<ForensicsPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
};
