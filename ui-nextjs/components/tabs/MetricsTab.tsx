'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { formatDate } from '@/utils/psi';
import type { MetricsResponse, DriftResponse, Horizon } from '@/types/api';
import 'katex/dist/katex.min.css';
import katex from 'katex';

interface MetricsTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function MetricsTab({ showLoading, hideLoading, showToast }: MetricsTabProps) {
  const [allMetrics, setAllMetrics] = useState<Record<Horizon, MetricsResponse | null>>({
    '24h': null,
    '48h': null,
    '72h': null,
    '7d': null,
  });
  const [customMetrics, setCustomMetrics] = useState<MetricsResponse | null>(null);
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-12-31');
  const [drift, setDrift] = useState<DriftResponse | null>(null);
  const [expandedExplanations, setExpandedExplanations] = useState<Set<string>>(new Set());
  const [expandedBands, setExpandedBands] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadAllMetrics();
  }, []);

  const loadAllMetrics = async () => {
    const horizons: Horizon[] = ['24h', '48h', '72h', '7d'];
    const promises = horizons.map(async (h) => {
      try {
        const data = await api.getMetrics(h, 30);
        return { horizon: h, data };
      } catch (error) {
        showToast(`Failed to load ${h} metrics`, 'error');
        return { horizon: h, data: null };
      }
    });

    const results = await Promise.all(promises);
    const newMetrics: Record<Horizon, MetricsResponse | null> = {
      '24h': null,
      '48h': null,
      '72h': null,
      '7d': null,
    };

    results.forEach(({ horizon, data }) => {
      newMetrics[horizon] = data;
    });

    setAllMetrics(newMetrics);
  };

  const loadCustomMetrics = async () => {
    showLoading('Loading custom metrics...');
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate
      });
      const response = await fetch(`${api.getBaseURL()}/metrics/24h?${params}`);
      if (!response.ok) throw new Error('Failed to fetch metrics');
      const metricsData = await response.json();
      setCustomMetrics(metricsData);
    } catch (error) {
      showToast('Failed to load custom metrics', 'error');
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

  const toggleExplanation = (key: string) => {
    setExpandedExplanations(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleBandMetrics = (key: string) => {
    setExpandedBands(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const LaTeX = ({ children, block = false }: { children: string; block?: boolean }) => {
    try {
      const html = katex.renderToString(children, {
        displayMode: block,
        throwOnError: false,
        output: 'html',
      });
      return <span dangerouslySetInnerHTML={{ __html: html }} />;
    } catch (e) {
      return <span>{children}</span>;
    }
  };

  const renderMetricsCard = (horizon: Horizon, metrics: MetricsResponse | null) => {
    const horizonLabels: Record<Horizon, string> = {
      '24h': '24 Hours',
      '48h': '48 Hours',
      '72h': '72 Hours',
      '7d': '7 Days',
    };

    return (
      <Card>
        <h3 className="text-lg font-semibold mb-3">{horizonLabels[horizon]}</h3>
        {metrics ? (
          <div className="space-y-3">
            <div className="text-xs text-gray-600">
              Sample Size: {metrics.sample_size} | Last: {formatDate(metrics.last_validated)}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">MAE</div>
                <div className="text-xl font-bold text-primary-600">
                  {metrics.regression_metrics.mae?.toFixed(2) || '-'}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">RMSE</div>
                <div className="text-xl font-bold text-primary-600">
                  {metrics.regression_metrics.rmse?.toFixed(2) || '-'}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">R²</div>
                <div className="text-xl font-bold text-primary-600">
                  {metrics.regression_metrics.r2?.toFixed(3) || '-'}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">MAPE</div>
                <div className="text-xl font-bold text-primary-600">
                  {metrics.regression_metrics.mape?.toFixed(2) || '-'}%
                </div>
              </div>
            </div>

            {metrics.alert_metrics && (
              <div className="pt-2 border-t border-gray-200">
                <div className="text-xs font-semibold mb-1">Alert Metrics</div>
                <div className="grid grid-cols-3 gap-1 text-xs">
                  <div>
                    <span className="text-gray-500">Precision:</span>{' '}
                    <span className="font-semibold">{(metrics.alert_metrics.precision * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Recall:</span>{' '}
                    <span className="font-semibold">{(metrics.alert_metrics.recall * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500">F1:</span>{' '}
                    <span className="font-semibold">{metrics.alert_metrics.f1_score?.toFixed(3) || '-'}</span>
                  </div>
                </div>

                {metrics.category_accuracy?.by_category && (
                  <div className="mt-2">
                    <button
                      onClick={() => toggleBandMetrics(horizon)}
                      className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
                    >
                      {expandedBands.has(horizon) ? '▼' : '▶'} Per-Band Metrics
                    </button>

                    {expandedBands.has(horizon) && (
                      <div className="mt-2 space-y-1">
                        {[
                          { name: 'Good', range: '0-50' },
                          { name: 'Moderate', range: '51-100' },
                          { name: 'Unhealthy', range: '101-200' },
                          { name: 'Very Unhealthy', range: '201-300' },
                          { name: 'Hazardous', range: '300+' }
                        ].map(({ name, range }) => {
                          const bandData = metrics.category_accuracy.by_category[name];
                          if (!bandData) return null;

                          return (
                            <div key={name} className="text-xs p-2 bg-white border border-gray-200 rounded">
                              <div className="font-semibold text-gray-700 mb-1">{name} ({range} PSI)</div>
                              <div className="grid grid-cols-4 gap-1 text-xs">
                                <div>
                                  <span className="text-gray-500">P:</span> {(bandData.precision * 100).toFixed(1)}%
                                </div>
                                <div>
                                  <span className="text-gray-500">R:</span> {(bandData.recall * 100).toFixed(1)}%
                                </div>
                                <div>
                                  <span className="text-gray-500">F1:</span> {bandData.f1_score.toFixed(3)}
                                </div>
                                <div>
                                  <span className="text-gray-500">n=</span>{bandData.support}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-gray-500">Loading...</div>
        )}
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Fixed Horizons Grid */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Model Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderMetricsCard('24h', allMetrics['24h'])}
          {renderMetricsCard('48h', allMetrics['48h'])}
          {renderMetricsCard('72h', allMetrics['72h'])}
          {renderMetricsCard('7d', allMetrics['7d'])}
        </div>
      </div>

      {/* Custom Date Range Section */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Custom Date Range Metrics</h2>
        <Card>
          <div className="space-y-3 mb-4">
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
              <button
                onClick={loadCustomMetrics}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
              >
                Load Metrics
              </button>
            </div>
          </div>

          {customMetrics && (
            <div className="space-y-4">
              <div className="text-sm text-gray-600">
                Date Range: {startDate} to {endDate} | Sample Size: {customMetrics.sample_size} |
                Last Validated: {formatDate(customMetrics.last_validated)}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">MAE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {customMetrics.regression_metrics.mae?.toFixed(2) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">RMSE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {customMetrics.regression_metrics.rmse?.toFixed(2) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">R²</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {customMetrics.regression_metrics.r2?.toFixed(3) || '-'}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">MAPE</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {customMetrics.regression_metrics.mape?.toFixed(2) || '-'}%
                  </div>
                </div>
              </div>

              {customMetrics.alert_metrics && (
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">Alert Metrics</h3>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Precision:</span>{' '}
                      <span className="font-semibold">{(customMetrics.alert_metrics.precision * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Recall:</span>{' '}
                      <span className="font-semibold">{(customMetrics.alert_metrics.recall * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">F1 Score:</span>{' '}
                      <span className="font-semibold">{customMetrics.alert_metrics.f1_score?.toFixed(3) || '-'}</span>
                    </div>
                  </div>

                  {customMetrics.category_accuracy?.by_category && (
                    <div className="mt-3">
                      <button
                        onClick={() => toggleBandMetrics('custom')}
                        className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
                      >
                        {expandedBands.has('custom') ? '▼' : '▶'} Per-Band Metrics
                      </button>

                      {expandedBands.has('custom') && (
                        <div className="mt-2 space-y-1">
                          {[
                            { name: 'Good', range: '0-50' },
                            { name: 'Moderate', range: '51-100' },
                            { name: 'Unhealthy', range: '101-200' },
                            { name: 'Very Unhealthy', range: '201-300' },
                            { name: 'Hazardous', range: '300+' }
                          ].map(({ name, range }) => {
                            const bandData = customMetrics.category_accuracy.by_category[name];
                            if (!bandData) return null;

                            return (
                              <div key={name} className="text-xs p-2 bg-white border border-gray-200 rounded">
                                <div className="font-semibold text-gray-700 mb-1">{name} ({range} PSI)</div>
                                <div className="grid grid-cols-4 gap-1 text-xs">
                                  <div>
                                    <span className="text-gray-500">P:</span> {(bandData.precision * 100).toFixed(1)}%
                                  </div>
                                  <div>
                                    <span className="text-gray-500">R:</span> {(bandData.recall * 100).toFixed(1)}%
                                  </div>
                                  <div>
                                    <span className="text-gray-500">F1:</span> {bandData.f1_score.toFixed(3)}
                                  </div>
                                  <div>
                                    <span className="text-gray-500">n=</span>{bandData.support}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Model Drift Analysis */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Model Drift Analysis</h2>
        <Card>
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
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Metric</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Baseline</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Current</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Change</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Significant</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {Object.entries(drift.metrics_change).map(([metric, change]) => (
                        <tr key={metric}>
                          <td className="px-3 py-2 text-gray-900 dark:text-gray-100">{metric}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{change.baseline?.toFixed(2) || '-'}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{change.current?.toFixed(2) || '-'}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{change.change_percent?.toFixed(2) || '-'}%</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{change.significant ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {drift.recommendation && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded border border-blue-200 dark:border-blue-800 text-sm text-blue-800 dark:text-blue-200">
                  {drift.recommendation}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Metric Explanations */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Metric Explanations</h2>
        <Card>
          <div className="space-y-2">
            {/* MAE */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('mae')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">MAE (Mean Absolute Error)</span>
                <span>{expandedExplanations.has('mae') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('mae') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Average magnitude of prediction errors, measured in PSI units.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'\\text{MAE} = \\frac{1}{n} \\sum_{i=1}^{n} |y_i - \\hat{y}_i|'}</LaTeX>
                  </div>
                  <p className="mt-2 text-xs">where <LaTeX>{'y_i'}</LaTeX> is actual PSI and <LaTeX>{'\\hat{y}_i'}</LaTeX> is predicted PSI</p>
                </div>
              )}
            </div>

            {/* RMSE */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('rmse')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">RMSE (Root Mean Square Error)</span>
                <span>{expandedExplanations.has('rmse') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('rmse') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Square root of average squared prediction errors, penalizes larger errors more heavily.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'\\text{RMSE} = \\sqrt{\\frac{1}{n} \\sum_{i=1}^{n} (y_i - \\hat{y}_i)^2}'}</LaTeX>
                  </div>
                </div>
              )}
            </div>

            {/* R² */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('r2')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">R² (Coefficient of Determination)</span>
                <span>{expandedExplanations.has('r2') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('r2') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Proportion of variance in PSI explained by the model. Ranges from 0 to 1, higher is better.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'R^2 = 1 - \\frac{\\sum_{i=1}^{n} (y_i - \\hat{y}_i)^2}{\\sum_{i=1}^{n} (y_i - \\bar{y})^2}'}</LaTeX>
                  </div>
                  <p className="mt-2 text-xs">where <LaTeX>{'\\bar{y}'}</LaTeX> is the mean of actual values</p>
                </div>
              )}
            </div>

            {/* MAPE */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('mape')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">MAPE (Mean Absolute Percentage Error)</span>
                <span>{expandedExplanations.has('mape') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('mape') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Average percentage difference between predicted and actual values.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'\\text{MAPE} = \\frac{100\\%}{n} \\sum_{i=1}^{n} \\left|\\frac{y_i - \\hat{y}_i}{y_i}\\right|'}</LaTeX>
                  </div>
                </div>
              )}
            </div>

            {/* Precision */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('precision')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">Precision (Alert Accuracy)</span>
                <span>{expandedExplanations.has('precision') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('precision') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Proportion of predicted high-PSI alerts that were actually high PSI.</p>
                  <p className="mb-2 text-xs text-gray-600">Threshold: 100 PSI (Unhealthy threshold). This is a weighted average across all PSI categories.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'\\text{Precision} = \\frac{\\text{True Positives}}{\\text{True Positives} + \\text{False Positives}}'}</LaTeX>
                  </div>
                </div>
              )}
            </div>

            {/* Recall */}
            <div className="border-b border-gray-200">
              <button
                onClick={() => toggleExplanation('recall')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">Recall (Alert Sensitivity)</span>
                <span>{expandedExplanations.has('recall') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('recall') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Proportion of actual high-PSI events that were correctly predicted.</p>
                  <p className="mb-2 text-xs text-gray-600">Threshold: 100 PSI (Unhealthy threshold). This is a weighted average across all PSI categories.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'\\text{Recall} = \\frac{\\text{True Positives}}{\\text{True Positives} + \\text{False Negatives}}'}</LaTeX>
                  </div>
                </div>
              )}
            </div>

            {/* F1 Score */}
            <div>
              <button
                onClick={() => toggleExplanation('f1')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">F1 Score (Balanced Alert Performance)</span>
                <span>{expandedExplanations.has('f1') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('f1') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-2">Harmonic mean of precision and recall, balances both metrics.</p>
                  <div className="bg-gray-50 p-3 rounded text-center">
                    <LaTeX block>{'F_1 = 2 \\cdot \\frac{\\text{Precision} \\cdot \\text{Recall}}{\\text{Precision} + \\text{Recall}}'}</LaTeX>
                  </div>
                </div>
              )}
            </div>

            {/* PSI Bands */}
            <div>
              <button
                onClick={() => toggleExplanation('psi-bands')}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
              >
                <span className="font-semibold">PSI Bands</span>
                <span>{expandedExplanations.has('psi-bands') ? '−' : '+'}</span>
              </button>
              {expandedExplanations.has('psi-bands') && (
                <div className="px-4 pb-4 text-sm text-gray-700">
                  <p className="mb-3">PSI values are categorized into 5 health bands:</p>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                      <span className="font-medium">Good</span>
                      <span className="text-gray-600">0-50 PSI</span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-yellow-50 rounded">
                      <span className="font-medium">Moderate</span>
                      <span className="text-gray-600">51-100 PSI</span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-orange-50 rounded">
                      <span className="font-medium">Unhealthy</span>
                      <span className="text-gray-600">101-200 PSI</span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-red-50 rounded">
                      <span className="font-medium">Very Unhealthy</span>
                      <span className="text-gray-600">201-300 PSI</span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-purple-50 rounded">
                      <span className="font-medium">Hazardous</span>
                      <span className="text-gray-600">300+ PSI</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}