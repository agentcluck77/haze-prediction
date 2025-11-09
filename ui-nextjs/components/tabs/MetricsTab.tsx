'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { formatDate } from '@/utils/psi';
import type { MetricsResponse, DriftResponse, Horizon } from '@/types/api';

interface MetricsTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function MetricsTab({ showLoading, hideLoading, showToast }: MetricsTabProps) {
  const [horizon, setHorizon] = useState<Horizon>('24h');
  const [periodDays, setPeriodDays] = useState<number>(30);
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-12-31');
  const [useDateRange, setUseDateRange] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [drift, setDrift] = useState<DriftResponse | null>(null);

  const loadMetrics = async () => {
    showLoading('Loading metrics...');
    try {
      // Build params based on whether using date range or period
      let metricsData;
      if (useDateRange) {
        // Call with date range
        const params = new URLSearchParams({
          period_days: periodDays.toString(),
          start_date: startDate,
          end_date: endDate
        });
        const response = await fetch(`${api.getBaseURL()}/metrics/${horizon}?${params}`);
        if (!response.ok) throw new Error('Failed to fetch metrics');
        metricsData = await response.json();
      } else {
        metricsData = await api.getMetrics(horizon, periodDays);
      }
      setMetrics(metricsData);
    } catch (error) {
      showToast('Failed to load metrics', 'error');
    } finally {
      hideLoading();
    }
  };

  const loadDrift = async () => {
    showLoading('Checking model drift...');
    try {
      const driftData = await api.getModelDrift();
      setDrift(driftData);
    } catch (error) {
      showToast('Failed to check drift', 'error');
    } finally {
      hideLoading();
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Performance Metrics */}
        <Card>
          <h2 className="text-xl font-semibold mb-4">Model Performance Metrics</h2>
          <div className="space-y-3 mb-4">
            <div className="flex gap-2 flex-wrap items-center">
              <select
                value={horizon}
                onChange={(e) => setHorizon(e.target.value as Horizon)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="24h">24 Hours</option>
                <option value="48h">48 Hours</option>
                <option value="72h">72 Hours</option>
                <option value="7d">7 Days</option>
              </select>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={useDateRange}
                  onChange={(e) => setUseDateRange(e.target.checked)}
                  className="rounded"
                />
                Use date range
              </label>
            </div>

            {useDateRange ? (
              <div className="flex gap-2 flex-wrap items-center">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
                <span className="text-sm text-gray-500">to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
            ) : (
              <input
                type="number"
                value={periodDays}
                onChange={(e) => setPeriodDays(parseInt(e.target.value) || 30)}
                placeholder="Period (days)"
                min="7"
                max="365"
                className="px-3 py-2 border border-gray-300 rounded-md text-sm w-32"
              />
            )}

            <button
              onClick={loadMetrics}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
            >
              Load Metrics
            </button>
          </div>

          {metrics && (
            <div className="space-y-4">
              <div className="text-sm text-gray-600">
                {useDateRange ? (
                  <>Date Range: {startDate} to {endDate} | </>
                ) : (
                  <>Period: {metrics.period_days} days | </>
                )}
                Sample Size: {metrics.sample_size} |
                Last Validated: {formatDate(metrics.last_validated)}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-500 mb-1">MAE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {metrics.regression_metrics.mae?.toFixed(2) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-500 mb-1">RMSE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {metrics.regression_metrics.rmse?.toFixed(2) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-500 mb-1">R²</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {metrics.regression_metrics.r2?.toFixed(3) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-500 mb-1">MAPE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {metrics.regression_metrics.mape?.toFixed(2) || '-'}%
                  </div>
                </div>
              </div>

              {metrics.alert_metrics && (
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">Alert Metrics</h3>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">Precision:</span>{' '}
                      <span className="font-semibold">{(metrics.alert_metrics.precision * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Recall:</span>{' '}
                      <span className="font-semibold">{(metrics.alert_metrics.recall * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">F1 Score:</span>{' '}
                      <span className="font-semibold">{metrics.alert_metrics.f1_score?.toFixed(3) || '-'}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Model Drift Analysis */}
        <Card>
          <h2 className="text-xl font-semibold mb-4">Model Drift Analysis</h2>
          <button
            onClick={loadDrift}
            className="mb-4 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
          >
            Check Drift
          </button>

          {drift && (
            <div className="space-y-4">
              <div className="text-sm">
                <div><strong>Drift Detected:</strong> {drift.drift_detected ? 'Yes' : 'No'}</div>
                <div><strong>Baseline Period:</strong> {drift.baseline_period || '-'}</div>
                <div><strong>Current Period:</strong> {drift.current_period || '-'}</div>
              </div>

              {drift.metrics_change && (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Baseline</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Current</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Significant</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(drift.metrics_change).map(([metric, change]) => (
                        <tr key={metric}>
                          <td className="px-3 py-2 text-gray-900">{metric}</td>
                          <td className="px-3 py-2 text-gray-700">{change.baseline?.toFixed(2) || '-'}</td>
                          <td className="px-3 py-2 text-gray-700">{change.current?.toFixed(2) || '-'}</td>
                          <td className="px-3 py-2 text-gray-700">{change.change_percent?.toFixed(2) || '-'}%</td>
                          <td className="px-3 py-2 text-gray-700">{change.significant ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {drift.recommendation && (
                <div className="p-3 bg-blue-50 rounded border border-blue-200 text-sm text-blue-800">
                  {drift.recommendation}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

