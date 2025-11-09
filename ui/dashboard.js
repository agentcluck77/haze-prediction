// Dashboard Main Logic
let currentCharts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeServerSelect();
    loadHealth();
    loadOverview();
    
    // Auto-refresh every 5 minutes
    setInterval(() => {
        if (document.querySelector('.tab-content.active').id === 'overview') {
            loadOverview();
        }
        loadHealth();
    }, 300000);
});

// Tab Navigation
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Update active states
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            // Load data for the active tab
            loadTabData(tabName);
        });
    });
}

function loadTabData(tabName) {
    switch(tabName) {
        case 'overview':
            loadOverview();
            break;
        case 'predictions':
            loadPredictions('24h');
            break;
        case 'current':
            loadCurrentData();
            break;
        case 'historical':
            loadHistorical();
            break;
        case 'metrics':
            loadMetrics();
            break;
        case 'benchmark':
            // Benchmark tab doesn't auto-load
            break;
    }
}

// Server Selection
function initializeServerSelect() {
    const serverSelect = document.getElementById('serverSelect');
    serverSelect.addEventListener('change', (e) => {
        api.setBaseURL(e.target.value);
        showToast('Server changed. Refreshing...', 'info');
        loadHealth();
        if (document.querySelector('.tab-content.active').id === 'overview') {
            loadOverview();
        }
    });

    // Refresh All button
    document.getElementById('refreshAllBtn').addEventListener('click', () => {
        const activeTab = document.querySelector('.tab-content.active').id;
        loadTabData(activeTab);
        showToast('Refreshing data...', 'info');
    });
}

// Health Check
async function loadHealth() {
    try {
        const health = await api.getHealth();
        const indicator = document.getElementById('healthIndicator');
        const statusDot = document.getElementById('statusDot');
        const healthStatus = document.getElementById('healthStatus');

        statusDot.className = `status-dot ${health.status}`;
        healthStatus.textContent = health.status.toUpperCase();
        
        if (health.status === 'unhealthy' && health.issues) {
            showToast(`System unhealthy: ${health.issues.join(', ')}`, 'error');
        }
    } catch (error) {
        document.getElementById('statusDot').className = 'status-dot unhealthy';
        document.getElementById('healthStatus').textContent = 'ERROR';
        showToast('Failed to check system health', 'error');
    }
}

// Overview Tab
async function loadOverview() {
    showLoading('Loading overview data...');
    try {
        const [psi, predictions, fires, weather] = await Promise.all([
            api.getCurrentPSI().catch(() => null),
            api.getAllPredictions().catch(() => null),
            api.getCurrentFires().catch(() => null),
            api.getCurrentWeather().catch(() => null)
        ]);

        if (psi) displayCurrentPSI(psi);
        if (predictions) displayPredictionsSummary(predictions);
        if (fires) displayFiresSummary(fires);
        if (weather) displayWeatherInfo(weather);
    } catch (error) {
        showToast('Failed to load overview data', 'error');
    } finally {
        hideLoading();
    }
}

function displayCurrentPSI(data) {
    const national = data.readings?.psi_24h?.national || '-';
    const category = getPSICategory(national);
    
    document.getElementById('currentPsiValue').textContent = national;
    document.getElementById('currentPsiCategory').textContent = category.label;
    document.getElementById('currentPsiCategory').className = `psi-category ${category.class}`;
    document.getElementById('healthAdvisory').textContent = data.health_advisory || '-';

    // Display regional readings
    const regionsDiv = document.getElementById('psiRegions');
    if (data.readings?.psi_24h) {
        const regions = ['north', 'south', 'east', 'west', 'central'];
        regionsDiv.innerHTML = regions.map(region => `
            <div class="psi-region">
                <div class="psi-region-label">${region.toUpperCase()}</div>
                <div class="psi-region-value">${data.readings.psi_24h[region] || '-'}</div>
            </div>
        `).join('');
    }
}

function displayPredictionsSummary(data) {
    const summaryDiv = document.getElementById('predictionsSummary');
    const horizons = ['24h', '48h', '72h', '7d'];
    
    summaryDiv.innerHTML = horizons.map(horizon => {
        const pred = data[horizon];
        if (!pred) return '';
        
        return `
            <div class="prediction-card">
                <div class="prediction-horizon">${horizon}</div>
                <div class="prediction-value">${pred.prediction?.toFixed(1) || '-'}</div>
                <div class="prediction-ci">[${pred.confidence_interval?.[0]?.toFixed(1) || '-'}, ${pred.confidence_interval?.[1]?.toFixed(1) || '-'}]</div>
            </div>
        `;
    }).join('');
}

function displayFiresSummary(data) {
    document.getElementById('fireCount').textContent = data.count || 0;
    
    const summaryDiv = document.getElementById('fireSummary');
    if (data.summary) {
        summaryDiv.innerHTML = `
            <div class="fire-stat">
                <div class="fire-stat-label">Total FRP</div>
                <div class="fire-stat-value">${data.summary.total_frp?.toFixed(1) || 0} MW</div>
            </div>
            <div class="fire-stat">
                <div class="fire-stat-label">High Confidence</div>
                <div class="fire-stat-value">${data.summary.high_confidence_count || 0}</div>
            </div>
            <div class="fire-stat">
                <div class="fire-stat-label">Avg Distance</div>
                <div class="fire-stat-value">${data.summary.avg_distance_km?.toFixed(1) || 0} km</div>
            </div>
        `;
    }
}

function displayWeatherInfo(data) {
    const weatherDiv = document.getElementById('weatherInfo');
    weatherDiv.innerHTML = `
        <div class="weather-item">
            <div class="weather-label">Temperature</div>
            <div class="weather-value">${data.temperature_2m?.toFixed(1) || '-'}°C</div>
        </div>
        <div class="weather-item">
            <div class="weather-label">Humidity</div>
            <div class="weather-value">${data.relative_humidity_2m?.toFixed(1) || '-'}%</div>
        </div>
        <div class="weather-item">
            <div class="weather-label">Wind Speed</div>
            <div class="weather-value">${data.wind_speed_10m?.toFixed(1) || '-'} km/h</div>
        </div>
        <div class="weather-item">
            <div class="weather-label">Wind Direction</div>
            <div class="weather-value">${data.wind_direction_10m?.toFixed(0) || '-'}°</div>
        </div>
        <div class="weather-item">
            <div class="weather-label">Pressure</div>
            <div class="weather-value">${data.pressure_msl?.toFixed(1) || '-'} hPa</div>
        </div>
    `;
}

// Predictions Tab
function loadPredictions(horizon) {
    showLoading('Loading predictions...');
    
    // Update active horizon button
    document.querySelectorAll('.horizon-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.horizon === horizon);
    });

    const loadPromise = horizon === 'all' 
        ? api.getAllPredictions()
        : api.getPrediction(horizon);

    loadPromise.then(data => {
        displayPredictionDetails(data, horizon);
    }).catch(error => {
        showToast('Failed to load predictions', 'error');
    }).finally(() => {
        hideLoading();
    });
}

// Initialize horizon buttons
document.querySelectorAll('.horizon-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        loadPredictions(btn.dataset.horizon);
    });
});

function displayPredictionDetails(data, horizon) {
    const detailsDiv = document.getElementById('predictionDetails');
    
    if (horizon === 'all') {
        // Display all horizons
        const horizons = ['24h', '48h', '72h', '7d'];
        detailsDiv.innerHTML = horizons.map(h => {
            const pred = data[h];
            if (!pred) return '';
            return createPredictionCard(pred, h);
        }).join('');
    } else {
        // Display single horizon
        detailsDiv.innerHTML = createPredictionCard(data, horizon);
    }
}

function createPredictionCard(pred, horizon) {
    const category = getPSICategory(pred.prediction);
    
    let featuresHtml = '';
    if (pred.features) {
        featuresHtml = Object.entries(pred.features).map(([key, value]) => `
            <div class="prediction-feature">
                <div class="prediction-feature-label">${formatFeatureName(key)}</div>
                <div class="prediction-feature-value">${typeof value === 'number' ? value.toFixed(2) : value}</div>
            </div>
        `).join('');
    }

    let shapHtml = '';
    if (pred.shap_explanation) {
        shapHtml = `
            <div style="margin-top: 24px;">
                <h3>SHAP Explanation</h3>
                <div style="margin-top: 12px;">
                    <div><strong>Base Value:</strong> ${pred.shap_explanation.base_value?.toFixed(2)}</div>
                    <div style="margin-top: 12px;">
                        <strong>Top Contributing Factors:</strong>
                        <ul style="margin-top: 8px; padding-left: 20px;">
                            ${pred.shap_explanation.top_factors?.slice(0, 5).map(factor => `
                                <li>${factor.feature}: ${factor.contribution?.toFixed(2)} (${factor.impact})</li>
                            `).join('') || ''}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    return `
        <div class="prediction-info">
            <div>
                <div class="prediction-feature">
                    <div class="prediction-feature-label">Prediction</div>
                    <div class="prediction-feature-value ${category.class}">${pred.prediction?.toFixed(1)}</div>
                </div>
                <div class="prediction-feature">
                    <div class="prediction-feature-label">Confidence Interval</div>
                    <div class="prediction-feature-value">[${pred.confidence_interval?.[0]?.toFixed(1)}, ${pred.confidence_interval?.[1]?.toFixed(1)}]</div>
                </div>
                <div class="prediction-feature">
                    <div class="prediction-feature-label">Model Version</div>
                    <div class="prediction-feature-value">${pred.model_version || '-'}</div>
                </div>
                <div class="prediction-feature">
                    <div class="prediction-feature-label">Target Time</div>
                    <div class="prediction-feature-value">${formatDate(pred.target_timestamp)}</div>
                </div>
            </div>
        </div>
        ${featuresHtml ? `<div class="prediction-info">${featuresHtml}</div>` : ''}
        ${pred.health_advisory ? `<div class="health-advisory" style="margin-top: 16px; padding: 12px; background: #f0f0f0; border-radius: 6px;">${pred.health_advisory}</div>` : ''}
        ${shapHtml}
    `;
}

// Current Data Tab
async function loadCurrentData() {
    showLoading('Loading current data...');
    try {
        const [psi, fires, weather] = await Promise.all([
            api.getCurrentPSI().catch(() => null),
            api.getCurrentFires().catch(() => null),
            api.getCurrentWeather().catch(() => null)
        ]);

        if (psi) displayCurrentPSIDetails(psi);
        if (fires) displayFiresList(fires);
        if (weather) displayWeatherDetails(weather);
    } catch (error) {
        showToast('Failed to load current data', 'error');
    } finally {
        hideLoading();
    }
}

function displayCurrentPSIDetails(data) {
    const div = document.getElementById('currentPsiDetails');
    const readings = data.readings || {};
    
    let html = `
        <div style="margin-bottom: 16px;">
            <strong>Last Updated:</strong> ${formatDate(data.update_timestamp || data.timestamp)}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Region</th>
                    <th>PSI 24h</th>
                    <th>PM2.5 24h</th>
                    <th>PM10 24h</th>
                </tr>
            </thead>
            <tbody>
    `;

    const regions = ['national', 'north', 'south', 'east', 'west', 'central'];
    regions.forEach(region => {
        html += `
            <tr>
                <td><strong>${region.toUpperCase()}</strong></td>
                <td>${readings.psi_24h?.[region] || '-'}</td>
                <td>${readings.pm25_24h?.[region] || '-'}</td>
                <td>${readings.pm10_24h?.[region] || '-'}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
        ${data.health_advisory ? `<div style="margin-top: 16px; padding: 12px; background: #f0f0f0; border-radius: 6px;">${data.health_advisory}</div>` : ''}
    `;

    div.innerHTML = html;
}

function displayFiresList(data) {
    const div = document.getElementById('firesList');
    
    if (!data.fires || data.fires.length === 0) {
        div.innerHTML = '<p>No fires detected in the last 24 hours.</p>';
        return;
    }

    let html = `
        <div style="margin-bottom: 12px;">
            <strong>Total:</strong> ${data.count} fires detected
        </div>
        <div class="fires-list">
    `;

    data.fires.slice(0, 50).forEach(fire => {
        html += `
            <div class="fire-item">
                <div>
                    <div class="fire-location">${fire.latitude?.toFixed(4)}, ${fire.longitude?.toFixed(4)}</div>
                    <div class="fire-details">
                        FRP: ${fire.frp?.toFixed(1)} MW | 
                        Confidence: ${fire.confidence?.toUpperCase()} | 
                        Distance: ${fire.distance_to_singapore_km?.toFixed(1)} km
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    div.innerHTML = html;
}

window.loadFires = async function() {
    const minConfidence = document.getElementById('minConfidenceFilter').value;
    const minFrp = document.getElementById('minFrpFilter').value || null;
    
    showLoading('Loading fires...');
    try {
        const fires = await api.getCurrentFires(minConfidence || null, minFrp);
        displayFiresList(fires);
    } catch (error) {
        showToast('Failed to load fires', 'error');
    } finally {
        hideLoading();
    }
};

function displayWeatherDetails(data) {
    const div = document.getElementById('weatherDetails');
    div.innerHTML = `
        <div class="weather-info">
            <div class="weather-item">
                <div class="weather-label">Temperature</div>
                <div class="weather-value">${data.temperature_2m?.toFixed(1) || '-'}°C</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Humidity</div>
                <div class="weather-value">${data.relative_humidity_2m?.toFixed(1) || '-'}%</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Wind Speed</div>
                <div class="weather-value">${data.wind_speed_10m?.toFixed(1) || '-'} km/h</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Wind Direction</div>
                <div class="weather-value">${data.wind_direction_10m?.toFixed(0) || '-'}°</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Wind Gusts</div>
                <div class="weather-value">${data.wind_gusts_10m?.toFixed(1) || '-'} km/h</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Pressure</div>
                <div class="weather-value">${data.pressure_msl?.toFixed(1) || '-'} hPa</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Cloud Cover</div>
                <div class="weather-value">${data.cloud_cover || '-'}%</div>
            </div>
            <div class="weather-item">
                <div class="weather-label">Precipitation</div>
                <div class="weather-value">${data.precipitation_1h?.toFixed(1) || '-'} mm</div>
            </div>
        </div>
        <div style="margin-top: 16px; color: #64748b; font-size: 14px;">
            <strong>Location:</strong> ${data.location || 'Singapore'}<br>
            <strong>Timestamp:</strong> ${formatDate(data.timestamp)}
        </div>
    `;
}

// Historical Tab
window.loadHistorical = async function() {
    const horizon = document.getElementById('historicalHorizon').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const limit = parseInt(document.getElementById('limit').value) || 100;

    showLoading('Loading historical data...');
    try {
        const data = await api.getHistoricalPredictions(horizon, startDate || null, endDate || null, limit);
        displayHistoricalData(data);
    } catch (error) {
        showToast('Failed to load historical data', 'error');
    } finally {
        hideLoading();
    }
};

function displayHistoricalData(data) {
    // Display chart
    const canvas = document.getElementById('historicalChartCanvas');
    const ctx = canvas.getContext('2d');

    if (currentCharts.historical) {
        currentCharts.historical.destroy();
    }

    if (data.predictions && data.predictions.length > 0) {
        const labels = data.predictions.map(p => formatDate(p.target_timestamp));
        const predicted = data.predictions.map(p => p.predicted_psi);
        const actual = data.predictions.map(p => p.actual_psi);

        currentCharts.historical = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Predicted PSI',
                        data: predicted,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Actual PSI',
                        data: actual,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Display table
    const tableDiv = document.getElementById('historicalTable');
    if (data.predictions && data.predictions.length > 0) {
        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Target Time</th>
                        <th>Predicted PSI</th>
                        <th>Actual PSI</th>
                        <th>Error</th>
                        <th>Within CI</th>
                        <th>Model</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.predictions.forEach(p => {
            html += `
                <tr>
                    <td>${formatDate(p.target_timestamp)}</td>
                    <td>${p.predicted_psi?.toFixed(1) || '-'}</td>
                    <td>${p.actual_psi?.toFixed(1) || '-'}</td>
                    <td>${p.absolute_error?.toFixed(1) || '-'}</td>
                    <td>${p.within_ci ? '✓' : '✗'}</td>
                    <td>${p.model_version || '-'}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        tableDiv.innerHTML = html;
    } else {
        tableDiv.innerHTML = '<p>No historical data available.</p>';
    }
}

// Metrics Tab
window.loadMetrics = async function() {
    const horizon = document.getElementById('metricsHorizon').value;
    const periodDays = parseInt(document.getElementById('periodDays').value) || 30;

    showLoading('Loading metrics...');
    try {
        const data = await api.getMetrics(horizon, periodDays);
        displayMetrics(data);
    } catch (error) {
        showToast('Failed to load metrics', 'error');
    } finally {
        hideLoading();
    }
};

function displayMetrics(data) {
    const div = document.getElementById('metricsDetails');
    
    let html = `
        <div style="margin-bottom: 16px;">
            <strong>Period:</strong> ${data.period_days} days | 
            <strong>Sample Size:</strong> ${data.sample_size} | 
            <strong>Last Validated:</strong> ${formatDate(data.last_validated)}
        </div>
        <div class="metrics-grid">
    `;

    if (data.regression_metrics) {
        html += `
            <div class="metric-card">
                <div class="metric-label">MAE</div>
                <div class="metric-value">${data.regression_metrics.mae?.toFixed(2) || '-'}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">RMSE</div>
                <div class="metric-value">${data.regression_metrics.rmse?.toFixed(2) || '-'}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">R²</div>
                <div class="metric-value">${data.regression_metrics.r2?.toFixed(3) || '-'}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">MAPE</div>
                <div class="metric-value">${data.regression_metrics.mape?.toFixed(2) || '-'}%</div>
            </div>
        `;
    }

    if (data.alert_metrics) {
        html += `
            <div class="metric-card">
                <div class="metric-label">Alert Precision</div>
                <div class="metric-value">${(data.alert_metrics.precision * 100).toFixed(1)}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Alert Recall</div>
                <div class="metric-value">${(data.alert_metrics.recall * 100).toFixed(1)}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">F1 Score</div>
                <div class="metric-value">${data.alert_metrics.f1_score?.toFixed(3) || '-'}</div>
            </div>
        `;
    }

    html += '</div>';

    div.innerHTML = html;
}

window.loadDrift = async function() {
    showLoading('Checking model drift...');
    try {
        const data = await api.getModelDrift();
        displayDrift(data);
    } catch (error) {
        showToast('Failed to check drift', 'error');
    } finally {
        hideLoading();
    }
};

function displayDrift(data) {
    const div = document.getElementById('driftDetails');
    
    let html = `
        <div style="margin-bottom: 16px;">
            <div><strong>Drift Detected:</strong> ${data.drift_detected ? 'Yes' : 'No'}</div>
            <div><strong>Baseline Period:</strong> ${data.baseline_period || '-'}</div>
            <div><strong>Current Period:</strong> ${data.current_period || '-'}</div>
        </div>
    `;

    if (data.metrics_change) {
        html += '<table><thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Change</th><th>Significant</th></tr></thead><tbody>';
        
        Object.entries(data.metrics_change).forEach(([metric, change]) => {
            html += `
                <tr>
                    <td>${metric}</td>
                    <td>${change.baseline?.toFixed(2) || '-'}</td>
                    <td>${change.current?.toFixed(2) || '-'}</td>
                    <td>${change.change_percent?.toFixed(2) || '-'}%</td>
                    <td>${change.significant ? 'Yes' : 'No'}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
    }

    if (data.recommendation) {
        html += `<div style="margin-top: 16px; padding: 12px; background: #f0f0f0; border-radius: 6px;">${data.recommendation}</div>`;
    }

    div.innerHTML = html;
}

window.compareMetrics = async function() {
    const periodDays = parseInt(document.getElementById('periodDays').value) || 30;
    
    showLoading('Comparing metrics...');
    try {
        const data = await api.compareMetrics(periodDays);
        displayCompareMetrics(data);
    } catch (error) {
        showToast('Failed to compare metrics', 'error');
    } finally {
        hideLoading();
    }
};

function displayCompareMetrics(data) {
    const div = document.getElementById('compareMetrics');
    // Implementation similar to displayMetrics but for all horizons
    div.innerHTML = '<p>Comparison data loaded. Display implementation needed.</p>';
}

// Benchmark Tab
window.startBenchmark = async function() {
    const testDataPath = document.getElementById('testDataPath').value;
    const modelsDir = document.getElementById('modelsDir').value;
    const modelVersion = document.getElementById('modelVersion').value || null;

    if (!testDataPath || !modelsDir) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    showLoading('Starting benchmark...');
    try {
        const result = await api.startBenchmark(testDataPath, modelsDir, modelVersion);
        showToast('Benchmark started successfully', 'success');
        addBenchmarkJob(result.job_id, result);
        pollBenchmarkStatus(result.job_id);
    } catch (error) {
        showToast('Failed to start benchmark', 'error');
    } finally {
        hideLoading();
    }
};

function addBenchmarkJob(jobId, initialData) {
    const jobsDiv = document.getElementById('benchmarkJobs');
    const jobDiv = document.createElement('div');
    jobDiv.className = 'benchmark-job';
    jobDiv.id = `job-${jobId}`;
    jobDiv.innerHTML = `
        <div class="job-status ${initialData.status}">${initialData.status.toUpperCase()}</div>
        <div><strong>Job ID:</strong> ${jobId}</div>
        <div id="job-progress-${jobId}"></div>
    `;
    jobsDiv.appendChild(jobDiv);
}

async function pollBenchmarkStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const status = await api.getBenchmarkStatus(jobId);
            updateBenchmarkJob(jobId, status);
            
            if (status.status === 'completed' || status.status === 'failed') {
                clearInterval(interval);
            }
        } catch (error) {
            clearInterval(interval);
            showToast(`Failed to poll benchmark status: ${error.message}`, 'error');
        }
    }, 5000); // Poll every 5 seconds
}

function updateBenchmarkJob(jobId, status) {
    const jobDiv = document.getElementById(`job-${jobId}`);
    if (!jobDiv) return;

    const statusDiv = jobDiv.querySelector('.job-status');
    statusDiv.className = `job-status ${status.status}`;
    statusDiv.textContent = status.status.toUpperCase();

    const progressDiv = document.getElementById(`job-progress-${jobId}`);
    
    if (status.status === 'running' && status.progress) {
        progressDiv.innerHTML = `
            <div class="job-progress">
                <div>${status.progress.current_test || 'Running...'}</div>
                <div>Progress: ${status.progress.tests_completed || 0}/${status.progress.tests_total || 0} tests</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${status.progress.percent_complete || 0}%"></div>
                </div>
            </div>
        `;
    } else if (status.status === 'completed' && status.results) {
        progressDiv.innerHTML = `
            <div>
                <div><strong>Duration:</strong> ${status.duration_seconds || 0} seconds</div>
                <div><strong>Tests Passed:</strong> ${status.results.summary?.tests_passed || 0}/${status.results.summary?.tests_total || 0}</div>
                <div><strong>Overall Pass:</strong> ${status.results.summary?.overall_pass ? 'Yes' : 'No'}</div>
                <pre style="margin-top: 12px; padding: 12px; background: #f0f0f0; border-radius: 6px; overflow-x: auto;">${JSON.stringify(status.results, null, 2)}</pre>
            </div>
        `;
    } else if (status.status === 'failed') {
        progressDiv.innerHTML = `
            <div style="color: #ef4444;">
                <div><strong>Error:</strong> ${status.error || 'Unknown error'}</div>
            </div>
        `;
    }
}

// Utility Functions
function getPSICategory(psi) {
    if (psi < 50) return { label: 'Good', class: 'psi-good' };
    if (psi < 100) return { label: 'Moderate', class: 'psi-moderate' };
    if (psi < 200) return { label: 'Unhealthy', class: 'psi-unhealthy' };
    if (psi < 300) return { label: 'Very Unhealthy', class: 'psi-very-unhealthy' };
    return { label: 'Hazardous', class: 'psi-hazardous' };
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatFeatureName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function showLoading(text = 'Loading...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('errorToast');
    toast.textContent = message;
    toast.className = `toast ${type} active`;
    
    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

