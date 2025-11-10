'use client';

import { useState, useEffect, useCallback } from 'react';
import Header from '@/components/Header';
import TabNavigation from '@/components/TabNavigation';
import OverviewTab from '@/components/tabs/OverviewTab';
import PredictionsTab from '@/components/tabs/PredictionsTab';
import CurrentDataTab from '@/components/tabs/CurrentDataTab';
import HistoricalTab from '@/components/tabs/HistoricalTab';
import MetricsTab from '@/components/tabs/MetricsTab';
import BenchmarkTab from '@/components/tabs/BenchmarkTab';
import MapTab from '@/components/tabs/MapTab';
import LoadingOverlay from '@/components/LoadingOverlay';
import Toast from '@/components/Toast';

type Tab = 'overview' | 'predictions' | 'current' | 'historical' | 'metrics' | 'benchmark'| 'map';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Loading...');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showLoading = useCallback((text: string = 'Loading...') => {
    setLoadingText(text);
    setLoading(true);
  }, []);

  const hideLoading = useCallback(() => {
    setLoading(false);
  }, []);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header showToast={showToast} />
      <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="container mx-auto px-4 py-6 max-w-7xl">
        {activeTab === 'overview' && <OverviewTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'predictions' && <PredictionsTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'current' && <CurrentDataTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'historical' && <HistoricalTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'metrics' && <MetricsTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'benchmark' && <BenchmarkTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
        {activeTab === 'map' && <MapTab showLoading={showLoading} hideLoading={hideLoading} showToast={showToast} />}
      </main>

      <LoadingOverlay loading={loading} text={loadingText} />
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

