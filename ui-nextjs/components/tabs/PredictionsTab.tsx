'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { getPSICategory, formatDate } from '@/utils/psi';
import type { PredictionResponse, AllPredictionsResponse, Horizon } from '@/types/api';

interface PredictionsTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function PredictionsTab({ showLoading, hideLoading, showToast }: PredictionsTabProps) {
  const [selectedHorizon, setSelectedHorizon] = useState<Horizon | 'all'>('24h');
  const [prediction, setPrediction] = useState<PredictionResponse | AllPredictionsResponse | null>(null);

  const showLoadingRef = useRef(showLoading);
  const hideLoadingRef = useRef(hideLoading);
  const showToastRef = useRef(showToast);

  // Update refs when callbacks change
  useEffect(() => {
    showLoadingRef.current = showLoading;
    hideLoadingRef.current = hideLoading;
    showToastRef.current = showToast;
  }, [showLoading, hideLoading, showToast]);

  useEffect(() => {
    let mounted = true;

    const loadPrediction = async () => {
      if (!mounted) return;
      showLoadingRef.current('Loading prediction...');
      try {
        const data = selectedHorizon === 'all'
          ? await api.getAllPredictions()
          : await api.getPrediction(selectedHorizon);
        if (!mounted) return;
        setPrediction(data);
      } catch (error) {
        if (!mounted) return;
        showToastRef.current('Failed to load prediction', 'error');
      } finally {
        if (mounted) hideLoadingRef.current();
      }
    };

    loadPrediction();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHorizon]);

  const horizons: (Horizon | 'all')[] = ['24h', '48h', '72h', '7d', 'all'];

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-xl font-semibold mb-4">PSI Predictions</h2>
        
        <div className="flex flex-wrap gap-2 mb-6">
          {horizons.map((horizon) => (
            <button
              key={horizon}
              onClick={() => setSelectedHorizon(horizon)}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                selectedHorizon === horizon
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {horizon === 'all' ? 'All Horizons' : horizon}
            </button>
          ))}
        </div>

        {prediction && (
          <div className="space-y-6">
            {selectedHorizon === 'all' && '24h' in prediction ? (
              // Display all horizons
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(['24h', '48h', '72h', '7d'] as Horizon[]).map((horizon) => {
                  const pred = (prediction as AllPredictionsResponse)[horizon];
                  if (!pred) return null;
                  return <PredictionCard key={horizon} prediction={pred} horizon={horizon} />;
                })}
              </div>
            ) : (
              // Display single horizon
              <PredictionCard prediction={prediction as PredictionResponse} horizon={selectedHorizon as Horizon} />
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function PredictionCard({ prediction, horizon }: { prediction: PredictionResponse; horizon: Horizon }) {
  const category = getPSICategory(prediction.prediction);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Prediction</div>
          <div className={`text-2xl font-bold ${category.color}`}>
            {prediction.prediction?.toFixed(1) || '-'}
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Confidence Interval</div>
          <div className="text-lg font-semibold">
            [{prediction.confidence_interval?.[0]?.toFixed(1)}, {prediction.confidence_interval?.[1]?.toFixed(1)}]
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Model Version</div>
          <div className="text-lg font-semibold">{prediction.model_version || '-'}</div>
        </div>
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Target Time</div>
          <div className="text-sm font-semibold">{formatDate(prediction.target_timestamp)}</div>
        </div>
      </div>

      {prediction.features && (
        <div>
          <h3 className="font-semibold mb-2">Input Features</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(prediction.features).map(([key, value]) => (
              <div key={key} className="p-2 bg-gray-50 rounded text-sm">
                <div className="text-gray-500 text-xs">{key.replace(/_/g, ' ')}</div>
                <div className="font-semibold">{typeof value === 'number' ? value.toFixed(2) : value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {prediction.shap_explanation && (
        <div className="p-4 bg-blue-50 rounded">
          <h3 className="font-semibold mb-2">SHAP Explanation</h3>
          <div className="text-sm mb-2">
            <strong>Base Value:</strong> {prediction.shap_explanation.base_value?.toFixed(2)}
          </div>
          <div className="text-sm">
            <strong>Top Contributing Factors:</strong>
            <ul className="list-disc list-inside mt-1 space-y-1">
              {prediction.shap_explanation.top_factors?.slice(0, 5).map((factor, idx) => (
                <li key={idx}>
                  {factor.feature}: {factor.contribution?.toFixed(2)} ({factor.impact})
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {prediction.health_advisory && (
        <div className="p-4 bg-yellow-50 rounded border border-yellow-200">
          <div className="text-sm font-medium text-yellow-800">{prediction.health_advisory}</div>
        </div>
      )}
    </div>
  );
}

