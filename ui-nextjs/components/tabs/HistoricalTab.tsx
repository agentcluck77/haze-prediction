'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { formatDate } from '@/utils/psi';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { HistoricalPredictionsResponse, Horizon } from '@/types/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface HistoricalTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function HistoricalTab({ showLoading, hideLoading, showToast }: HistoricalTabProps) {
  const [horizon, setHorizon] = useState<Horizon>('24h');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [limit, setLimit] = useState<number>(100);
  const [data, setData] = useState<HistoricalPredictionsResponse | null>(null);

  const loadHistorical = async () => {
    showLoading('Loading historical data...');
    try {
      const historicalData = await api.getHistoricalPredictions(
        horizon,
        startDate || undefined,
        endDate || undefined,
        limit
      );
      setData(historicalData);
    } catch (error) {
      showToast('Failed to load historical data', 'error');
    } finally {
      hideLoading();
    }
  };

  const chartData = data?.predictions
    ? {
        labels: data.predictions.map((p) => formatDate(p.target_timestamp)),
        datasets: [
          {
            label: 'Predicted PSI',
            data: data.predictions.map((p) => p.predicted_psi),
            borderColor: 'rgb(37, 99, 235)',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            tension: 0.1,
          },
          {
            label: 'Actual PSI',
            data: data.predictions.map((p) => p.actual_psi),
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.1,
          },
        ],
      }
    : null;

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-xl font-semibold mb-4">Historical Predictions</h2>
        
        <div className="flex flex-wrap gap-2 mb-6">
          <select
            value={horizon}
            onChange={(e) => setHorizon(e.target.value as Horizon)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
          >
            <option value="24h">24 Hours</option>
            <option value="48h">48 Hours</option>
            <option value="72h">72 Hours</option>
            <option value="7d">7 Days</option>
          </select>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
          />
          <input
            type="number"
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
            placeholder="Limit"
            min="1"
            max="1000"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm w-24"
          />
          <button
            onClick={loadHistorical}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
          >
            Load
          </button>
        </div>

        {chartData && (
          <div className="mb-6" style={{ height: '400px' }}>
            <Line
              data={chartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    beginAtZero: true,
                  },
                },
              }}
            />
          </div>
        )}

        {data && data.predictions && data.predictions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Target Time</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Predicted PSI</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actual PSI</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Error</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Within CI</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Model</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {data.predictions.map((pred, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{formatDate(pred.target_timestamp)}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{pred.predicted_psi?.toFixed(1) || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{pred.actual_psi?.toFixed(1) || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{pred.absolute_error?.toFixed(1) || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{pred.within_ci ? '✓' : '✗'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{pred.model_version || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && (!data.predictions || data.predictions.length === 0) && (
          <p className="text-gray-500 dark:text-gray-400 text-center py-8">No historical data available.</p>
        )}
      </Card>
    </div>
  );
}