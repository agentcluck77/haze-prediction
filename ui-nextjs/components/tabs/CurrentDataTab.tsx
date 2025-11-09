'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { formatDate } from '@/utils/psi';
import type { CurrentPsiResponse, FiresResponse, WeatherResponse, ConfidenceLevel } from '@/types/api';

interface CurrentDataTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function CurrentDataTab({ showLoading, hideLoading, showToast }: CurrentDataTabProps) {
  const [psi, setPsi] = useState<CurrentPsiResponse | null>(null);
  const [fires, setFires] = useState<FiresResponse | null>(null);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [minConfidence, setMinConfidence] = useState<ConfidenceLevel | ''>('');
  const [minFrp, setMinFrp] = useState<string>('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    showLoading('Loading current data...');
    try {
      const [psiData, firesData, weatherData] = await Promise.all([
        api.getCurrentPSI().catch(() => null),
        api.getCurrentFires().catch(() => null),
        api.getCurrentWeather().catch(() => null),
      ]);

      if (psiData) setPsi(psiData);
      if (firesData) setFires(firesData);
      if (weatherData) setWeather(weatherData);
    } catch (error) {
      showToast('Failed to load current data', 'error');
    } finally {
      hideLoading();
    }
  };

  const loadFires = async () => {
    showLoading('Loading fires...');
    try {
      const firesData = await api.getCurrentFires(
        minConfidence || undefined,
        minFrp ? parseFloat(minFrp) : undefined
      );
      setFires(firesData);
    } catch (error) {
      showToast('Failed to load fires', 'error');
    } finally {
      hideLoading();
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current PSI */}
        <Card>
          <h2 className="text-xl font-semibold mb-4">Current PSI Readings</h2>
          {psi && (
            <div className="space-y-4">
              <div className="text-sm text-gray-500">
                Last Updated: {formatDate(psi.update_timestamp || psi.timestamp)}
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PSI 24h</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PM2.5 24h</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PM10 24h</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {['national', 'north', 'south', 'east', 'west', 'central'].map((region) => (
                      <tr key={region}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 uppercase">{region}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{psi.readings.psi_24h?.[region as keyof typeof psi.readings.psi_24h] || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{psi.readings.pm25_24h?.[region as keyof typeof psi.readings.pm25_24h] || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{psi.readings.pm10_24h?.[region as keyof typeof psi.readings.pm10_24h] || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {psi.health_advisory && (
                <div className="p-3 bg-yellow-50 rounded border border-yellow-200 text-sm text-yellow-800">
                  {psi.health_advisory}
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Active Fires */}
        <Card>
          <h2 className="text-xl font-semibold mb-4">Active Fire Detections</h2>
          <div className="flex gap-2 mb-4 flex-wrap">
            <select
              value={minConfidence}
              onChange={(e) => setMinConfidence(e.target.value as ConfidenceLevel | '')}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">All Confidence</option>
              <option value="h">High</option>
              <option value="n">Normal</option>
              <option value="l">Low</option>
            </select>
            <input
              type="number"
              value={minFrp}
              onChange={(e) => setMinFrp(e.target.value)}
              placeholder="Min FRP (MW)"
              min="0"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm flex-1 min-w-[120px]"
            />
            <button
              onClick={loadFires}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
            >
              Filter
            </button>
          </div>
          {fires && (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">
                Total: <span className="font-semibold">{fires.count}</span> fires detected
              </div>
              <div className="max-h-96 overflow-y-auto">
                {fires.fires && fires.fires.length > 0 ? (
                  <div className="space-y-2">
                    {fires.fires.slice(0, 50).map((fire, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded border border-gray-200">
                        <div className="font-medium text-sm">
                          {fire.latitude?.toFixed(4)}, {fire.longitude?.toFixed(4)}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          FRP: {fire.frp?.toFixed(1)} MW | Confidence: {fire.confidence?.toUpperCase()} | 
                          Distance: {fire.distance_to_singapore_km?.toFixed(1)} km
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No fires detected in the last 24 hours.</p>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Weather Conditions */}
      <Card>
        <h2 className="text-xl font-semibold mb-4">Weather Conditions</h2>
        {weather && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Temperature</div>
              <div className="text-2xl font-semibold">{weather.temperature_2m?.toFixed(1) || '-'}°C</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Humidity</div>
              <div className="text-2xl font-semibold">{weather.relative_humidity_2m?.toFixed(1) || '-'}%</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Wind Speed</div>
              <div className="text-2xl font-semibold">{weather.wind_speed_10m?.toFixed(1) || '-'} km/h</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Wind Direction</div>
              <div className="text-2xl font-semibold">{weather.wind_direction_10m?.toFixed(0) || '-'}°</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Wind Gusts</div>
              <div className="text-2xl font-semibold">{weather.wind_gusts_10m?.toFixed(1) || '-'} km/h</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Pressure</div>
              <div className="text-2xl font-semibold">{weather.pressure_msl?.toFixed(1) || '-'} hPa</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Cloud Cover</div>
              <div className="text-2xl font-semibold">{weather.cloud_cover || '-'}%</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-500 mb-1">Precipitation</div>
              <div className="text-2xl font-semibold">{weather.precipitation_1h?.toFixed(1) || '-'} mm</div>
            </div>
          </div>
        )}
        {weather && (
          <div className="mt-4 text-sm text-gray-500">
            <strong>Location:</strong> {weather.location || 'Singapore'} | 
            <strong className="ml-2">Timestamp:</strong> {formatDate(weather.timestamp)}
          </div>
        )}
      </Card>
    </div>
  );
}

