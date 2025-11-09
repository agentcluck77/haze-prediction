'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import Card from '@/components/Card';
import { formatDate } from '@/utils/psi';
import type { BenchmarkJobRequest, BenchmarkJobStatus, BenchmarkJobResponse } from '@/types/api';

interface BenchmarkTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function BenchmarkTab({ showLoading, hideLoading, showToast }: BenchmarkTabProps) {
  const [testDataPath, setTestDataPath] = useState<string>('');
  const [modelsDir, setModelsDir] = useState<string>('');
  const [modelVersion, setModelVersion] = useState<string>('');
  const [jobs, setJobs] = useState<Map<string, BenchmarkJobStatus>>(new Map());

  const showLoadingRef = useRef(showLoading);
  const hideLoadingRef = useRef(hideLoading);
  const showToastRef = useRef(showToast);

  // Update refs when callbacks change
  useEffect(() => {
    showLoadingRef.current = showLoading;
    hideLoadingRef.current = hideLoading;
    showToastRef.current = showToast;
  }, [showLoading, hideLoading, showToast]);

  const pollBenchmarkStatus = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await api.getBenchmarkStatus(jobId);
        setJobs((prevJobs) => {
          const newJobs = new Map(prevJobs);
          newJobs.set(jobId, status);
          return newJobs;
        });

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        clearInterval(interval);
        showToastRef.current(`Failed to poll benchmark status: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      }
    }, 5000); // Poll every 5 seconds
  };

  const startBenchmark = async () => {
    if (!testDataPath || !modelsDir) {
      showToastRef.current('Please fill in all required fields', 'error');
      return;
    }

    showLoadingRef.current('Starting benchmark...');
    try {
      const request: BenchmarkJobRequest = {
        test_data_path: testDataPath,
        models_dir: modelsDir,
      };
      if (modelVersion) request.model_version = modelVersion;

      const result = await api.startBenchmark(request);
      showToast('Benchmark started successfully', 'success');

      pollBenchmarkStatus(result.job_id);
    } catch (error) {
      showToastRef.current('Failed to start benchmark', 'error');
    } finally {
      hideLoadingRef.current();
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-xl font-semibold mb-4">Model Benchmarking</h2>
        
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Test Data Path *
            </label>
            <input
              type="text"
              value={testDataPath}
              onChange={(e) => setTestDataPath(e.target.value)}
              placeholder="e.g., data/test_set.csv"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Models Directory *
            </label>
            <input
              type="text"
              value={modelsDir}
              onChange={(e) => setModelsDir(e.target.value)}
              placeholder="e.g., models/phase1"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Model Version (Optional)
            </label>
            <input
              type="text"
              value={modelVersion}
              onChange={(e) => setModelVersion(e.target.value)}
              placeholder="e.g., phase1_v1.0"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm"
            />
          </div>
          <button
            onClick={startBenchmark}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
          >
            Start Benchmark
          </button>
        </div>

        {jobs.size > 0 && (
          <div className="space-y-4">
            <h3 className="font-semibold">Benchmark Jobs</h3>
            {Array.from(jobs.entries()).map(([jobId, job]) => (
              <BenchmarkJobCard key={jobId} jobId={jobId} job={job} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function BenchmarkJobCard({ jobId, job }: { jobId: string; job: BenchmarkJobStatus }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(job.status)}`}>
            {job.status.toUpperCase()}
          </span>
          <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Job ID: {jobId}</span>
        </div>
      </div>

      {job.status === 'running' && (
        <div className="mt-3">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            {job.progress.current_test || 'Running...'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            Progress: {job.progress.tests_completed || 0}/{job.progress.tests_total || 0} tests
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all"
              style={{ width: `${job.progress.percent_complete || 0}%` }}
            />
          </div>
        </div>
      )}

      {job.status === 'completed' && (
        <div className="mt-3 space-y-2 text-sm">
          <div>
            <strong>Duration:</strong> {job.duration_seconds || 0} seconds
          </div>
          <div>
            <strong>Tests Passed:</strong> {job.results.summary?.tests_passed || 0}/
            {job.results.summary?.tests_total || 0}
          </div>
          <div>
            <strong>Overall Pass:</strong> {job.results.summary?.overall_pass ? 'Yes' : 'No'}
          </div>
          <details className="mt-2">
            <summary className="cursor-pointer text-primary-600 font-medium">View Results</summary>
            <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-x-auto">
              {JSON.stringify(job.results, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {job.status === 'failed' && (
        <div className="mt-3 text-sm text-red-600 dark:text-red-400">
          <strong>Error:</strong> {job.error || 'Unknown error'}
        </div>
      )}
    </div>
  );
}

