'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApi } from '@/contexts/ApiContext';
import { api } from '@/lib/api';
import type { HealthResponse } from '@/types/api';

interface HeaderProps {
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function Header({ showToast }: HeaderProps) {
  const { baseURL, setBaseURL } = useApi();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  const loadHealth = useCallback(async () => {
    setIsChecking(true);
    try {
      const healthData = await api.getHealth();
      setHealth(healthData);
      setIsChecking(false);
      
      if (healthData.status === 'unhealthy' && healthData.issues) {
        showToast(`System unhealthy: ${healthData.issues.join(', ')}`, 'error');
      }
    } catch (error) {
      // Set health to unhealthy on error
      setHealth(prevHealth => {
        // Only show toast on first error to avoid spam
        if (!prevHealth) {
          showToast('Failed to connect to API server', 'error');
        }
        
        return { 
          status: 'unhealthy' as const, 
          timestamp: new Date().toISOString(),
          issues: [error instanceof Error ? error.message : 'Failed to connect to API']
        } as HealthResponse;
      });
      setIsChecking(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [baseURL, loadHealth]);

  const handleServerChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setBaseURL(e.target.value);
    showToast('Server changed. Refreshing...', 'info');
    loadHealth();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-4 max-w-7xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
            🌫️ Singapore Haze Prediction Dashboard
          </h1>
          
          <div className="flex items-center gap-4 flex-wrap">
            <select
              value={baseURL}
              onChange={handleServerChange}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="http://localhost:8000">Local Development</option>
              <option value="https://staging-api.hazeprediction.sg/v1">Staging</option>
              <option value="https://api.hazeprediction.sg/v1">Production</option>
            </select>
            
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-md">
              <div className={`w-2 h-2 rounded-full ${getStatusColor(health?.status || (isChecking ? 'unknown' : 'unhealthy'))} ${isChecking ? 'animate-pulse' : ''}`} />
              <span className="text-sm font-medium text-gray-700">
                {isChecking ? 'CHECKING...' : (health?.status?.toUpperCase() || 'UNKNOWN')}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

