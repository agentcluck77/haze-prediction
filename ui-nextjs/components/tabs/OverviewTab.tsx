'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { getPSICategory, formatDate } from '@/utils/psi';
import type { CurrentPsiResponse, AllPredictionsResponse, FiresResponse, WeatherResponse } from '@/types/api';

interface OverviewTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function OverviewTab({ showLoading, hideLoading, showToast }: OverviewTabProps) {
  const [psi, setPsi] = useState<CurrentPsiResponse | null>(null);
  const [predictions, setPredictions] = useState<AllPredictionsResponse | null>(null);
  const [fires, setFires] = useState<FiresResponse | null>(null);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);

  const loadData = useCallback(async () => {
    showLoading('Loading overview data...');
    try {
      const [psiData, predictionsData, firesData, weatherData] = await Promise.all([
        api.getCurrentPSI().catch(() => null),
        api.getAllPredictions().catch(() => null),
        api.getCurrentFires().catch(() => null),
        api.getCurrentWeather().catch(() => null),
      ]);

      if (psiData) setPsi(psiData);
      if (predictionsData) setPredictions(predictionsData);
      if (firesData) setFires(firesData);
      if (weatherData) setWeather(weatherData);
    } catch (error) {
      showToast('Failed to load overview data', 'error');
    } finally {
      hideLoading();
    }
  }, [showLoading, hideLoading, showToast]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [loadData]);
  
  const nationalPSI = psi?.readings?.psi_24h?.national || 0;
  const category = getPSICategory(nationalPSI);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Current PSI Card */}
        <Card className={`${category.bgColor} border-2`}>
          <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">Current PSI</h2>
          <div className={`text-6xl font-bold ${category.color} mb-2`}>
            {nationalPSI || '-'}
          </div>
          <div className={`text-2xl font-semibold ${category.color} mb-4`}>
            {category.label}
          </div>
          
          {psi?.readings?.psi_24h && (
            <div className="grid grid-cols-3 gap-2 mt-4">
              {['north', 'south', 'east', 'west', 'central'].map((region) => (
                <div key={region} className="bg-white dark:bg-gray-800 bg-opacity-50 rounded p-2 text-center">
                  <div className="text-xs text-gray-600 dark:text-gray-400 uppercase">{region}</div>
                  <div className={`text-lg font-semibold ${category.color}`}>
                    {psi.readings.psi_24h[region as keyof typeof psi.readings.psi_24h] || '-'}
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {psi?.health_advisory && (
            <div className="mt-4 p-3 bg-white dark:bg-gray-800 bg-opacity-70 rounded text-sm text-gray-700 dark:text-gray-300">
              {psi.health_advisory}
            </div>
          )}
        </Card>

        {/* Predictions Summary */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Predictions Summary</h2>
          <div className="grid grid-cols-2 gap-4">
            {predictions && ['24h', '48h', '72h', '7d'].map((horizon) => {
              const pred = predictions[horizon as keyof typeof predictions];
              if (!pred) return null;
              return (
                <div key={horizon} className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{horizon}</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {pred.prediction?.toFixed(1) || '-'}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    [{pred.confidence_interval?.[0]?.toFixed(1)}, {pred.confidence_interval?.[1]?.toFixed(1)}]
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Active Fires */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Active Fires (24h)</h2>
          <div className="text-5xl font-bold text-red-600 mb-4">
            {fires?.count || 0}
          </div>
          {fires?.summary && (
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-500 dark:text-gray-400">Total FRP</div>
                <div className="font-semibold">{fires.summary.total_frp?.toFixed(1) || 0} MW</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">High Confidence</div>
                <div className="font-semibold">{fires.summary.high_confidence_count || 0}</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">Avg Distance</div>
                <div className="font-semibold">{fires.summary.avg_distance_km?.toFixed(1) || 0} km</div>
              </div>
            </div>
          )}
        </Card>

        {/* Weather Conditions */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Current Weather</h2>
          {weather && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Temperature</div>
                <div className="text-xl font-semibold">{weather.temperature_2m?.toFixed(1) || '-'}°C</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Humidity</div>
                <div className="text-xl font-semibold">{weather.relative_humidity_2m?.toFixed(1) || '-'}%</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Wind Speed</div>
                <div className="text-xl font-semibold">{weather.wind_speed_10m?.toFixed(1) || '-'} km/h</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Wind Direction</div>
                <div className="text-xl font-semibold">{weather.wind_direction_10m?.toFixed(0) || '-'}°</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Pressure</div>
                <div className="text-xl font-semibold">{weather.pressure_msl?.toFixed(1) || '-'} hPa</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Cloud Cover</div>
                <div className="text-xl font-semibold">{weather.cloud_cover || '-'}%</div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}