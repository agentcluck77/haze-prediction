# Singapore Haze Prediction Dashboard - Next.js

A modern, responsive web dashboard built with Next.js, React, and TypeScript for the Singapore Haze Prediction API.

## Features

- **Modern Stack**: Next.js 14, React 18, TypeScript
- **Responsive Design**: Tailwind CSS with mobile-first approach
- **Type Safety**: Full TypeScript types based on OpenAPI specification
- **Real-time Updates**: Auto-refresh and polling for live data
- **Interactive Charts**: Chart.js for data visualization
- **All API Endpoints**: Complete integration with all endpoints from OpenAPI spec

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- API server running (default: `http://localhost:8000`)

### Installation

1. Navigate to the project directory:
```bash
cd ui-nextjs
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Run the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
ui-nextjs/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main dashboard page
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── Header.tsx         # Dashboard header with server selection
│   ├── TabNavigation.tsx  # Tab navigation component
│   ├── Card.tsx           # Reusable card component
│   ├── LoadingOverlay.tsx # Loading overlay
│   ├── Toast.tsx          # Toast notifications
│   └── tabs/              # Tab components
│       ├── OverviewTab.tsx
│       ├── PredictionsTab.tsx
│       ├── CurrentDataTab.tsx
│       ├── HistoricalTab.tsx
│       ├── MetricsTab.tsx
│       └── BenchmarkTab.tsx
├── contexts/             # React contexts
│   └── ApiContext.tsx     # API base URL context
├── lib/                   # Utilities
│   └── api.ts            # API client
├── types/                 # TypeScript types
│   └── api.ts             # API types from OpenAPI spec
├── utils/                 # Utility functions
│   └── psi.ts             # PSI category utilities
└── package.json
```

## Configuration

### API Server

The dashboard supports multiple API servers:
- **Local Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.hazeprediction.sg/v1`
- **Production**: `https://api.hazeprediction.sg/v1`

Select your server from the dropdown in the header. The API client automatically uses the selected server.

### Environment Variables

Create a `.env.local` file to customize the default API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Features by Tab

### Overview Tab
- Current PSI readings with regional breakdown
- Predictions summary for all horizons
- Active fire detections summary
- Current weather conditions
- Auto-refreshes every 5 minutes

### Predictions Tab
- View PSI predictions for specific horizons (24h, 48h, 72h, 7d)
- Confidence intervals
- Input features used for prediction
- SHAP explanations (for Phase 2 XGBoost model)
- Health advisories

### Current Data Tab
- Detailed PSI readings by region
- Filterable fire detections
- Comprehensive weather data
- Real-time updates

### Historical Tab
- Historical predictions with validation
- Interactive charts comparing predicted vs actual PSI
- Filterable by date range and horizon
- Error analysis

### Metrics Tab
- Model performance metrics (MAE, RMSE, R², MAPE)
- Alert classification metrics
- Model drift detection
- Performance comparison across horizons

### Benchmark Tab
- Start comprehensive model benchmarks
- Track benchmark job progress in real-time
- View detailed benchmark results
- Multiple concurrent benchmark jobs

## API Integration

All endpoints from the OpenAPI specification are integrated:

- `GET /predict/{horizon}` - Get prediction for specific horizon
- `GET /predict/all` - Get all predictions
- `GET /current/psi` - Current PSI readings
- `GET /current/fires` - Active fire detections
- `GET /current/weather` - Current weather conditions
- `GET /historical/{horizon}` - Historical predictions
- `GET /metrics/{horizon}` - Model performance metrics
- `GET /metrics/compare` - Compare metrics across horizons
- `GET /metrics/drift` - Model drift analysis
- `POST /benchmark` - Start benchmark job
- `GET /benchmark/{job_id}` - Get benchmark status
- `GET /health` - System health check

## Technologies Used

- **Next.js 14**: React framework with App Router
- **React 18**: UI library
- **TypeScript**: Type safety
- **Tailwind CSS**: Utility-first CSS framework
- **Chart.js**: Data visualization
- **Axios**: HTTP client
- **date-fns**: Date formatting utilities

## Development

### Code Style

- TypeScript strict mode enabled
- ESLint with Next.js config
- Prettier recommended for formatting

### Adding New Features

1. Add types to `types/api.ts` if needed
2. Add API methods to `lib/api.ts`
3. Create components in `components/` or `components/tabs/`
4. Update the main page to include new tabs/features

## Troubleshooting

### CORS Issues

If you encounter CORS errors, ensure your API server has CORS enabled:

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

### API Connection Errors

1. Check that the API server is running
2. Verify the server URL in the dropdown
3. Check browser console for detailed error messages
4. Ensure the API endpoints match the OpenAPI specification

### Build Errors

1. Clear `.next` directory: `rm -rf .next`
2. Reinstall dependencies: `rm -rf node_modules && npm install`
3. Check TypeScript errors: `npm run lint`

## Docker Deployment

### Local Docker with Docker Compose

From the project root directory:

```bash
docker-compose up
```

This starts:
- API service on http://localhost:8000
- UI service on http://localhost:3000
- PostgreSQL database on port 5432
- Scheduler service (background tasks)

### Production Docker Build

```bash
cd ui-nextjs
docker build -t haze-ui .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=https://your-api-url.com haze-ui
```

## Google Cloud Run Deployment

The UI is automatically deployed to Cloud Run when you push to the main branch via Cloud Build.

### Architecture

```
┌─────────────────────────────────────────────────┐
│           Google Cloud Platform                  │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────┐         ┌──────────────┐      │
│  │  Cloud Run   │         │  Cloud Run   │      │
│  │  (UI)        │────────>│  (API)       │      │
│  │  Port: 3000  │         │  Port: 8000  │      │
│  └──────────────┘         └──────┬───────┘      │
│                                   │               │
│                                   ▼               │
│                          ┌─────────────────┐     │
│                          │  Cloud SQL      │     │
│                          │  (PostgreSQL)   │     │
│                          └─────────────────┘     │
│                                                   │
└─────────────────────────────────────────────────┘
```

### Deployment Process

Cloud Build automatically:
1. Builds the API Docker image
2. Builds the UI Docker image
3. Deploys API to Cloud Run
4. Gets the API URL from the deployed service
5. Deploys UI to Cloud Run with NEXT_PUBLIC_API_URL set to the API URL

### Manual Cloud Run Deployment

If you need to deploy manually:

```bash
# Set variables
export PROJECT_ID=hacx-477608
export REGION=asia-southeast1

# Build UI image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/haze-prediction/haze-ui:latest -f ui-nextjs/Dockerfile ./ui-nextjs

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/haze-prediction/haze-ui:latest

# Get API URL
API_URL=$(gcloud run services describe haze-prediction-api \
  --region=${REGION} \
  --format="value(status.url)")

# Deploy UI
gcloud run deploy haze-prediction-ui \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/haze-prediction/haze-ui:latest \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000 \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=60 \
  --set-env-vars="NEXT_PUBLIC_API_URL=${API_URL},NODE_ENV=production"

# Get UI URL
gcloud run services describe haze-prediction-ui \
  --region=${REGION} \
  --format="value(status.url)"
```

### CORS Configuration

The API must allow requests from the UI domain. For Cloud Run deployments, ensure the API has CORS configured to allow the UI URL.

For local development, ensure the API has CORS enabled for `http://localhost:3000`.

## License

MIT License - See main project license

