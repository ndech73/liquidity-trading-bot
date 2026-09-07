import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useSettings } from './hooks/useSettings';
import { SettingsForm } from './components/SettingsForm';
import { Spinner } from '../../shared/components/Spinner';

export const SettingsPage: React.FC = () => {
  const { settings } = useSettings();

  return (
    <PageContainer title="System Settings" subtitle="Trading bot parameters and execution engine configuration">
      {settings ? <SettingsForm settings={settings} /> : <Spinner size="lg" className="py-20" />}
    </PageContainer>
  );
};
