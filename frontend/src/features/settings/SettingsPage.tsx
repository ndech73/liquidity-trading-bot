import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useSettings } from './hooks/useSettings';
import { SettingsForm } from './components/SettingsForm';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';

export const SettingsPage: React.FC = () => {
  const { settings, isLoading, isSaving, error, saveSettings, refetch } = useSettings();

  if (isLoading) {
    return (
      <PageContainer title="System Settings" subtitle="Trading bot parameters and execution engine configuration">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="System Settings" subtitle="Trading bot parameters and execution engine configuration">
        <ErrorState message={error} onRetry={refetch} className="my-10" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="System Settings" subtitle="Trading bot parameters and execution engine configuration">
      {settings ? (
        <SettingsForm settings={settings} onSave={saveSettings} isSaving={isSaving} />
      ) : (
        <Spinner size="lg" className="py-20" />
      )}
    </PageContainer>
  );
};

