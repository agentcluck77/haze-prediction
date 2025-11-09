// API Client for Singapore Haze Prediction API
class HazeAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    setBaseURL(url) {
        this.baseURL = url;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: response.statusText }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Predictions
    async getPrediction(horizon) {
        return this.request(`/predict/${horizon}`);
    }

    async getAllPredictions() {
        return this.request('/predict/all');
    }

    // Current Data
    async getCurrentPSI() {
        return this.request('/current/psi');
    }

    async getCurrentFires(minConfidence = null, minFrp = null) {
        const params = new URLSearchParams();
        if (minConfidence) params.append('min_confidence', minConfidence);
        if (minFrp !== null) params.append('min_frp', minFrp);
        const query = params.toString();
        return this.request(`/current/fires${query ? '?' + query : ''}`);
    }

    async getCurrentWeather() {
        return this.request('/current/weather');
    }

    // Historical
    async getHistoricalPredictions(horizon, startDate = null, endDate = null, limit = 100) {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('limit', limit);
        const query = params.toString();
        return this.request(`/historical/${horizon}?${query}`);
    }

    // Metrics
    async getMetrics(horizon, periodDays = 30) {
        return this.request(`/metrics/${horizon}?period_days=${periodDays}`);
    }

    async compareMetrics(periodDays = 30) {
        return this.request(`/metrics/compare?period_days=${periodDays}`);
    }

    async getModelDrift() {
        return this.request('/metrics/drift');
    }

    // Benchmark
    async startBenchmark(testDataPath, modelsDir, modelVersion = null) {
        const body = {
            test_data_path: testDataPath,
            models_dir: modelsDir
        };
        if (modelVersion) body.model_version = modelVersion;
        return this.request('/benchmark', {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }

    async getBenchmarkStatus(jobId) {
        return this.request(`/benchmark/${jobId}`);
    }

    // Health
    async getHealth() {
        return this.request('/health');
    }
}

// Initialize API client
const api = new HazeAPI();

