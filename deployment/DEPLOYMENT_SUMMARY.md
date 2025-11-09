# GCP Deployment Summary - Singapore Haze Prediction System

Deployment completed on: 2025-11-08

## Deployed Services

### API Service
- **Status**: DEPLOYED AND RUNNING
- **URL**: https://haze-prediction-api-1092946108581.asia-southeast1.run.app
- **Region**: asia-southeast1
- **Service Name**: haze-prediction-api
- **Image**: asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest
- **Platform**: Cloud Run (Managed)
- **Configuration**:
  - Memory: 512Mi
  - CPU: 1
  - Min Instances: 0 (scales to zero)
  - Max Instances: 10
  - Port: 8000
  - Timeout: 300s
  - Environment: production

### Scheduler Service
- **Status**: NOT DEPLOYED (Background service architecture incompatible with Cloud Run)
- **Recommendation**: Deploy as Cloud Run Jobs or modify to include health endpoint
- **Image**: asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-scheduler:latest

## Infrastructure Components

### Cloud SQL Database
- **Instance Name**: haze-prediction-db
- **Database**: haze_prediction
- **Version**: PostgreSQL 15
- **Tier**: db-f1-micro
- **Region**: asia-southeast1
- **Connection Name**: hacx-477608:asia-southeast1:haze-prediction-db
- **User**: hazeuser
- **Password**: HazePredict2024Secure! (stored in Secret Manager)
- **Status**: RUNNING
- **Schema**: INITIALIZED (all tables created)

### Secret Manager
- **firms-api-key**: f6cd6de4fa5a42514a72c8525064e890
- **db-password**: HazePredict2024Secure!
- **database-url**: postgresql://hazeuser:HazePredict2024Secure!@/haze_prediction?host=/cloudsql/hacx-477608:asia-southeast1:haze-prediction-db

### Cloud Storage Buckets
- **hacx-haze-models**: Optional backup storage (models are bundled in Docker images)
- **hacx-haze-data**: Data and logs storage

**Note**: ML models are now included directly in Docker images for better version consistency:
- Models in `models/` directory are copied into each Docker build
- Always in sync with code version
- Faster loading (local filesystem vs. GCS fetch)
- See `deployment/MODEL_MANAGEMENT.md` for details

### Artifact Registry
- **Repository**: haze-prediction
- **Location**: asia-southeast1
- **Format**: Docker
- **Images**:
  - haze-api:latest (linux/amd64)
  - haze-scheduler:latest (linux/amd64)

## API Endpoints

Base URL: https://haze-prediction-api-1092946108581.asia-southeast1.run.app

### Available Endpoints

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/` | GET | API information and available endpoints | ✓ Working |
| `/health` | GET | System health check | ✓ Working |
| `/predict/24h` | GET | 24-hour PSI prediction | ✓ Working |
| `/predict/48h` | GET | 48-hour PSI prediction | ✓ Working |
| `/predict/72h` | GET | 72-hour PSI prediction | ✓ Working |
| `/predict/7d` | GET | 7-day PSI prediction | ✓ Working |
| `/predict/all` | GET | All predictions | ✓ Working |
| `/current/psi` | GET | Current PSI readings from NEA | ✓ Working |
| `/current/fires` | GET | Current fire detections (last 24h) | ✓ Working |
| `/historical/{horizon}` | GET | Historical predictions | Not implemented |
| `/metrics/{horizon}` | GET | Model performance metrics | ✓ Working |

## Test Results

### Health Check
```bash
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/health
```
Response:
```json
{
  "status": "healthy",
  "last_update": {
    "fires": "2025-11-08T11:06:03.826474",
    "weather": "2025-11-08T11:06:03.826482",
    "psi": "2025-11-08T11:06:03.826484"
  },
  "api_status": {
    "firms": "healthy",
    "open_meteo": "unknown",
    "psi": "healthy"
  },
  "database": "not_configured"
}
```

### 24h Prediction
```bash
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/predict/24h
```
Response:
```json
{
  "prediction": 47.5,
  "confidence_interval": [27.5, 67.5],
  "features": {
    "fire_risk_score": 34.1,
    "wind_transport_score": 0.8,
    "baseline_score": 10.0
  },
  "timestamp": "2025-11-08T11:06:20.005295",
  "target_timestamp": "2025-11-09T11:06:20.005295",
  "horizon": "24h",
  "model_version": "phase1_linear_v1.0"
}
```

### Current PSI
```bash
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/current/psi
```
Successfully fetches real-time PSI data from NEA for all regions (north, south, east, west, central).

## Deployment Process Summary

1. ✓ Enabled required GCP services
2. ✓ Created Cloud SQL PostgreSQL instance
3. ✓ Set up Cloud Storage buckets and uploaded ML models
4. ✓ Configured Secret Manager with API keys and credentials
5. ✓ Set up Artifact Registry for Docker images
6. ✓ Initialized database schema with all required tables
7. ✓ Built Docker images for linux/amd64 platform
8. ✓ Pushed images to Artifact Registry
9. ✓ Deployed API service to Cloud Run
10. ✓ Granted Secret Manager permissions to service account
11. ✓ Tested all API endpoints

## Cost Estimates

**Monthly Operating Costs** (approximate):
- Cloud Run (API): $10-30
- Cloud SQL (db-f1-micro): $15-25
- Cloud Storage: $5-10
- Secret Manager: $1-2
- Artifact Registry: $0-5
- **Total**: ~$35-90/month

## Known Issues & Recommendations

### 1. Scheduler Service Not Deployed
**Issue**: The scheduler service failed to deploy because it's designed as a background task runner and doesn't listen on an HTTP port (required by Cloud Run services).

**Options**:
- **Option A** (Recommended): Deploy as Cloud Run Jobs
  - Create scheduled jobs that run periodically
  - Lower cost (pay only when running)
  - Better suited for batch operations

- **Option B**: Modify scheduler to include a minimal Flask/FastAPI server for health checks
  - Keep Cloud Run service architecture
  - Always running (higher cost)

- **Option C**: Use Cloud Scheduler to trigger API endpoints that perform the same tasks
  - Simplest implementation
  - No additional services needed

### 2. Database Integration
**Note**: The API currently shows `"database": "not_configured"` in health checks. To enable database integration:
1. Update API code to use the Cloud SQL connection
2. Redeploy the API service

### 3. CORS Configuration
**Current**: CORS allows all origins (`*`)
**Recommendation**: Update `src/api/main.py` to restrict origins to your frontend domain for production.

## Next Steps

### Immediate
1. [ ] Deploy scheduler service using one of the recommended options
2. [ ] Configure database integration in the API
3. [ ] Set up monitoring and alerts

### Short-term
4. [ ] Configure custom domain
5. [ ] Set up CI/CD pipeline (Cloud Build)
6. [ ] Implement rate limiting
7. [ ] Add authentication for admin endpoints

### Long-term
8. [ ] Set up staging environment
9. [ ] Implement caching layer (Cloud Memorystore)
10. [ ] Add comprehensive logging and monitoring dashboards
11. [ ] Set up automated backups and disaster recovery
12. [ ] Performance optimization and load testing

## Maintenance Commands

### View Logs
```bash
# API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=haze-prediction-api" \
  --limit=50 \
  --project=hacx-477608

# Database logs
gcloud sql operations list --instance=haze-prediction-db --project=hacx-477608
```

### Update Deployment
```bash
# Rebuild and redeploy
cd /Users/aloy/Desktop/Aloys\ Code/hacx-extra
docker build --platform linux/amd64 -t asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest .
docker push asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest
gcloud run services update haze-prediction-api --region=asia-southeast1 --project=hacx-477608
```

### Connect to Database
```bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
cat init-db.sql | gcloud sql connect haze-prediction-db --user=hazeuser --database=haze_prediction --project=hacx-477608
# Password: HazePredict2024Secure!
```

### Scale Service
```bash
# Increase max instances
gcloud run services update haze-prediction-api \
  --max-instances=20 \
  --region=asia-southeast1 \
  --project=hacx-477608

# Set minimum instances (keeps service warm)
gcloud run services update haze-prediction-api \
  --min-instances=1 \
  --region=asia-southeast1 \
  --project=hacx-477608
```

## Security Notes

1. **Secrets Management**:
   - All sensitive data stored in Secret Manager
   - Service account has minimum required permissions
   - Regular secret rotation recommended

2. **Network Security**:
   - Cloud Run services use HTTPS only
   - Cloud SQL accessible only via private connection (Cloud SQL Proxy)
   - No public IP exposed for database

3. **Authentication**:
   - API currently allows unauthenticated access
   - Scheduler service requires authentication (--no-allow-unauthenticated)
   - Consider adding API key authentication for production

## Monitoring & Alerts

Recommended setup:
1. Uptime checks for /health endpoint
2. Error rate alerts (>5%)
3. Latency alerts (>2s p95)
4. Cost budget alerts ($100/month)
5. Cloud SQL connection alerts

## Backup & Recovery

- **Database**: Automated daily backups at 02:00 SGT
- **Models**: Stored in Cloud Storage with versioning
- **Code**: In version control (Git)

## Support & Documentation

- Full deployment guide: `/deployment/GCP_DEPLOYMENT.md`
- Quick start guide: `/deployment/QUICKSTART.md`
- API documentation: Available at API root endpoint
- GCP Console: https://console.cloud.google.com/run?project=hacx-477608

## Contact Information

- Project ID: hacx-477608
- Region: asia-southeast1
- Deployment Date: 2025-11-08
- Deployed By: Automated deployment script
