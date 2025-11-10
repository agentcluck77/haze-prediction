// TypeScript types based on OpenAPI specification

export type Horizon = '24h' | '48h' | '72h' | '7d';
export type ModelVersion = 'phase1_linear' | 'phase2_xgboost';
export type ConfidenceLevel = 'l' | 'n' | 'h';
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';
export type ApiStatus = 'operational' | 'degraded' | 'down';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface PredictionResponse {
  prediction: number;
  confidence_interval: [number, number];
  features?: Record<string, number>;
  timestamp: string;
  target_timestamp: string;
  horizon: Horizon;
  model_version: ModelVersion;
  health_advisory?: string;
  shap_explanation?: {
    base_value: number;
    top_factors: Array<{
      feature: string;
      value: number;
      contribution: number;
      impact: 'increases' | 'decreases';
    }>;
  };
}

export interface AllPredictionsResponse {
  '24h': PredictionResponse;
  '48h': PredictionResponse;
  '72h': PredictionResponse;
  '7d': PredictionResponse;
}

export interface RegionalReadings {
  national: number;
  north: number;
  south: number;
  east: number;
  west: number;
  central: number;
}

export interface CurrentPsiResponse {
  timestamp: string;
  update_timestamp: string;
  readings: {
    psi_24h: RegionalReadings;
    pm25_24h?: RegionalReadings;
    pm10_24h?: RegionalReadings;
    o3_sub_index?: RegionalReadings;
    co_sub_index?: RegionalReadings;
  };
  health_advisory: string;
}

export interface FireDetection {
  latitude: number;
  longitude: number;
  frp: number;
  brightness: number;
  confidence: ConfidenceLevel;
  acq_date: string;
  acq_time: string;
  satellite: string;
  distance_to_singapore_km: number;
}

export interface FiresResponse {
  count: number;
  timestamp: string;
  fires: FireDetection[];
  summary?: {
    total_frp: number;
    high_confidence_count: number;
    avg_distance_km: number;
  };
}

export interface WeatherResponse {
  timestamp: string;
  location: string;
  temperature_2m: number;
  relative_humidity_2m: number;
  wind_speed_10m: number;
  wind_direction_10m: number;
  wind_gusts_10m?: number;
  pressure_msl: number;
  cloud_cover?: number;
  precipitation_1h?: number;
}

export interface HistoricalPrediction {
  prediction_timestamp: string;
  target_timestamp: string;
  predicted_psi: number;
  actual_psi: number | null;
  absolute_error: number | null;
  within_ci: boolean | null;
  model_version: string;
}

export interface HistoricalPredictionsResponse {
  horizon: Horizon;
  count: number;
  start_date?: string;
  end_date?: string;
  predictions: HistoricalPrediction[];
}

export interface RegressionMetrics {
  mae: number;
  rmse: number;
  r2: number;
  mape: number;
}

export interface AlertMetrics {
  threshold: number;
  precision: number;
  recall: number;
  f1_score: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
}

export interface CategoryAccuracy {
  overall: number;
  by_category: Record<string, {
    precision: number;
    recall: number;
    f1_score: number;
    support: number;
  }>;
}

export interface Calibration {
  ci_coverage_95: number;
  well_calibrated: boolean;
}

export interface MetricsResponse {
  horizon: Horizon;
  period_days: number;
  sample_size: number;
  last_validated: string;
  regression_metrics: RegressionMetrics;
  alert_metrics: AlertMetrics;
  category_accuracy: CategoryAccuracy;
  calibration: Calibration;
}

export interface DriftResponse {
  drift_detected: boolean;
  baseline_period: string;
  current_period: string;
  metrics_change: Record<string, {
    baseline: number;
    current: number;
    change_percent: number;
    significant: boolean;
  }>;
  recommendation: string;
}

export interface ApiStatusDetail {
  status: ApiStatus;
  last_check: string;
  response_time_ms: number;
}

export interface HealthResponse {
  status: HealthStatus;
  timestamp: string;
  uptime_seconds?: number;
  last_update?: {
    fires: string;
    weather: string;
    psi: string;
    predictions: string;
  };
  api_status?: {
    firms: ApiStatusDetail;
    open_meteo: ApiStatusDetail;
    psi: ApiStatusDetail;
  };
  database?: {
    status: 'connected' | 'disconnected' | 'degraded';
    connection_pool_usage?: string;
  };
  model?: {
    version: string;
    loaded: boolean;
    last_prediction: string;
  };
  issues?: string[];
}

export interface BenchmarkJobRequest {
  test_data_path: string;
  models_dir: string;
  model_version?: string;
}

export interface BenchmarkJobResponse {
  job_id: string;
  status: 'queued' | 'running';
  status_url: string;
  estimated_duration_minutes: number;
}

export interface BenchmarkProgress {
  current_test: string;
  tests_completed: number;
  tests_total: number;
  percent_complete: number;
}

export interface BenchmarkJobRunning {
  job_id: string;
  status: 'running';
  progress: BenchmarkProgress;
  started_at: string;
  elapsed_seconds: number;
}

export interface BenchmarkResults {
  summary: {
    tests_passed: number;
    tests_total: number;
    pass_rate: number;
    overall_pass: boolean;
    test_samples: number;
    models_evaluated: string[];
  };
  regression: Record<string, {
    mae: number;
    rmse: number;
    r2: number;
    meets_mae_target: boolean;
    meets_rmse_target: boolean;
    status: string;
  }>;
  alerts: {
    precision: number;
    recall: number;
    f1_score: number;
    meets_target: boolean;
    status: string;
  };
  categories: {
    overall_accuracy: number;
    by_category: Record<string, number>;
  };
  seasonal?: Record<string, {
    mae: number;
    rmse: number;
    alert_precision?: number;
  }>;
  calibration: Record<string, {
    ci_coverage: number;
    well_calibrated: boolean;
    status: string;
  }>;
}

export interface BenchmarkJobCompleted {
  job_id: string;
  status: 'completed';
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  results: BenchmarkResults;
}

export interface BenchmarkJobFailed {
  job_id: string;
  status: 'failed';
  started_at: string;
  failed_at: string;
  duration_seconds: number;
  error: string;
  error_details?: {
    type: string;
    traceback: string;
  };
}

export type BenchmarkJobStatus = BenchmarkJobRunning | BenchmarkJobCompleted | BenchmarkJobFailed;

export interface ErrorResponse {
  error: string;
  details?: Record<string, unknown>;
}