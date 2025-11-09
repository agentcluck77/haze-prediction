import axios, { AxiosInstance } from 'axios';
import type {
  PredictionResponse,
  AllPredictionsResponse,
  CurrentPsiResponse,
  FiresResponse,
  WeatherResponse,
  HistoricalPredictionsResponse,
  MetricsResponse,
  DriftResponse,
  HealthResponse,
  BenchmarkJobRequest,
  BenchmarkJobResponse,
  BenchmarkJobStatus,
  Horizon,
  ConfidenceLevel,
  ErrorResponse,
} from '@/types/api';

class HazeAPI {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          const errorData = error.response.data as ErrorResponse;
          throw new Error(errorData.error || error.message);
        }
        throw error;
      }
    );
  }

  setBaseURL(url: string) {
    this.baseURL = url;
    this.client.defaults.baseURL = url;
  }

  getBaseURL(): string {
    return this.baseURL;
  }

  // Predictions
  async getPrediction(horizon: Horizon): Promise<PredictionResponse> {
    const response = await this.client.get<PredictionResponse>(`/predict/${horizon}`);
    return response.data;
  }

  async getAllPredictions(): Promise<AllPredictionsResponse> {
    const response = await this.client.get<AllPredictionsResponse>('/predict/all');
    return response.data;
  }

  // Current Data
  async getCurrentPSI(): Promise<CurrentPsiResponse> {
    const response = await this.client.get<CurrentPsiResponse>('/current/psi');
    return response.data;
  }

  async getCurrentFires(
    minConfidence?: ConfidenceLevel,
    minFrp?: number
  ): Promise<FiresResponse> {
    const params: Record<string, string | number> = {};
    if (minConfidence) params.min_confidence = minConfidence;
    if (minFrp !== undefined) params.min_frp = minFrp;

    const response = await this.client.get<FiresResponse>('/current/fires', { params });
    return response.data;
  }

  async getCurrentWeather(): Promise<WeatherResponse> {
    const response = await this.client.get<WeatherResponse>('/current/weather');
    return response.data;
  }

  // Historical
  async getHistoricalPredictions(
    horizon: Horizon,
    startDate?: string,
    endDate?: string,
    limit: number = 100
  ): Promise<HistoricalPredictionsResponse> {
    const params: Record<string, string | number> = { limit };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await this.client.get<HistoricalPredictionsResponse>(
      `/historical/${horizon}`,
      { params }
    );
    return response.data;
  }

  // Metrics
  async getMetrics(horizon: Horizon, periodDays: number = 30): Promise<MetricsResponse> {
    const response = await this.client.get<MetricsResponse>(`/metrics/${horizon}`, {
      params: { period_days: periodDays },
    });
    return response.data;
  }

  async compareMetrics(periodDays: number = 30): Promise<Record<Horizon, MetricsResponse>> {
    const response = await this.client.get<Record<Horizon, MetricsResponse>>(
      '/metrics/compare',
      {
        params: { period_days: periodDays },
      }
    );
    return response.data;
  }

  async getModelDrift(): Promise<DriftResponse> {
    const response = await this.client.get<DriftResponse>('/metrics/drift');
    return response.data;
  }

  // Benchmark
  async startBenchmark(request: BenchmarkJobRequest): Promise<BenchmarkJobResponse> {
    const response = await this.client.post<BenchmarkJobResponse>('/benchmark', request);
    return response.data;
  }

  async getBenchmarkStatus(jobId: string): Promise<BenchmarkJobStatus> {
    const response = await this.client.get<BenchmarkJobStatus>(`/benchmark/${jobId}`);
    return response.data;
  }

  // Health
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }
}

// Create singleton instance
export const api = new HazeAPI();

// Export class for testing
export default HazeAPI;