# Data Availability Status

Last Updated: 2025-11-08

## Summary

All required data sources are available and accessible for the Singapore Haze Prediction System. Training data spans from 2014 to present.

## Fire Detection Data (NASA FIRMS)

**Source:** NASA Fire Information for Resource Management System (FIRMS)
**API Key:** f6cd6de4fa5a42514a72c8525064e890
**Status:** Active and Verified

### Available Datasets

| Dataset | Satellite | Date Range | Coverage | Notes |
|---------|-----------|------------|----------|-------|
| MODIS_SP | Terra/Aqua | 2000-11-01 to 2025-07-31 | Historical | Standard Product, 6-month lag |
| MODIS_NRT | Terra/Aqua | 2025-08-01 to present | Real-time | Near Real-Time updates |
| VIIRS_SNPP_SP | Suomi NPP | 2012-01-20 to 2025-07-31 | Historical | Higher resolution than MODIS |
| VIIRS_SNPP_NRT | Suomi NPP | 2025-08-01 to present | Real-time | Near Real-Time updates |
| VIIRS_NOAA20_SP | NOAA-20 | 2018-04-01 to 2025-07-31 | Historical | Latest generation sensor |
| VIIRS_NOAA20_NRT | NOAA-20 | 2025-08-01 to present | Real-time | Primary data source |

### Data Fields
- Latitude, Longitude
- Fire Radiative Power (FRP) in MW
- Brightness temperature
- Confidence level (high/nominal/low)
- Acquisition date and time
- Satellite identifier

### Update Frequency
- NRT: Every 3 hours
- SP: Daily (historical archive)

### Spatial Coverage
- Indonesia bbox: (95, -11, 141, 6)
- Covers Sumatra, Kalimantan, Java, Sulawesi

**Recommendation:** Use VIIRS_NOAA20_NRT for real-time predictions, VIIRS_SNPP_SP for historical training (2012-2025).

---

## Weather Data (Open-Meteo)

**Source:** Open-Meteo API
**Authentication:** None required (free tier)
**Status:** Active and Verified

### Current & Forecast API
- **Endpoint:** https://api.open-meteo.com/v1/forecast
- **Coverage:** Global, including Singapore and Indonesia
- **Forecast Range:** Up to 16 days
- **Past Days:** Up to 92 days (via past_days parameter)
- **Update Frequency:** Hourly

### Historical Archive (ERA5)
- **Endpoint:** https://archive-api.open-meteo.com/v1/era5
- **Date Range:** 1940-01-01 to present (7-day lag)
- **Resolution:** Hourly
- **Coverage:** Global 0.25° grid (~25km)

### Available Parameters
- Wind: speed_10m, direction_10m, gusts_10m (km/h, degrees)
- Temperature: 2m (°C)
- Humidity: relative_humidity_2m (%)
- Pressure: pressure_msl (hPa)
- Precipitation: precipitation (mm)
- Cloud cover, visibility, etc.

### Recommended Locations for Grid Simulation
1. Singapore: (1.3521, 103.8198)
2. Riau, Sumatra: (0.5, 101.5)
3. Jambi, Sumatra: (-1.6, 103.6)
4. South Sumatra: (-3.0, 104.8)
5. Central Kalimantan: (-2.0, 113.5)

**Recommendation:** Use ERA5 archive for training data (2014-2025), forecast API for real-time predictions.

---

## Singapore PSI Data (NEA via data.gov.sg)

**Source:** National Environment Agency (NEA), Singapore
**Authentication:** Not required (until Dec 31, 2025)
**Status:** Active and Verified

### Current Real-Time API
- **Endpoint:** https://api.data.gov.sg/v1/environment/psi
- **Update Frequency:** Every 15 minutes
- **Regions:** National, North, South, East, West, Central

### Historical Dataset
- **Endpoint:** https://data.gov.sg/api/action/datastore_search
- **Resource ID:** d_b4cf557f8750260d229c49fd768e11ed
- **Total Records:** 94,272
- **Date Range:** 2014-01-04 to present
- **Update Frequency:** Continuous (hourly snapshots)

### Data Fields
- Timestamp
- PSI 24-hour readings (by region)
- PM2.5 24-hour (¼g/m³)
- PM10 24-hour (¼g/m³)
- O3 sub-index
- CO sub-index
- NO2 1-hour max
- SO2 24-hour

### PSI Bands
- 0-50: Good
- 51-100: Moderate
- 101-200: Unhealthy
- 201-300: Very Unhealthy
- 301+: Hazardous

**Recommendation:** Use historical dataset for training (2014-2025), real-time API for predictions.

---

## Training Data Timeline

### Phase 1: Linear Regression Model

**Target Date Range:** 2014-01-04 to 2025-11-08 (11 years, 10 months)

| Data Source | Start Date | End Date | Records (Est.) |
|-------------|------------|----------|----------------|
| PSI (Historical) | 2014-01-04 | 2025-11-08 | 94,272 |
| Fire (VIIRS_SNPP_SP) | 2014-01-04 | 2025-07-31 | ~4,200 days |
| Weather (ERA5) | 2014-01-04 | 2025-11-01 | ~103,000 hours |

### Data Alignment Strategy
1. PSI readings are hourly ’ Use as primary timestamp anchor
2. Fire data is 24-hour snapshots ’ Aggregate to daily, join to PSI
3. Weather data is hourly ’ Direct join to PSI by timestamp

### Expected Training Set Size
- Rows: ~94,000 (one per PSI reading)
- Features: 3 (Phase 1), 50+ (Phase 2)
- Target variables: 4 (PSI at 24h, 48h, 72h, 7d ahead)

---

## Data Quality Notes

### Known Limitations
1. **PSI Data Gap:** No data before 2014 (not 2010 as originally requested)
2. **Fire Data Transition:** MODIS and VIIRS use different sensors (calibration differences)
3. **Weather Reanalysis:** ERA5 is a reanalysis product (slight differences from actual observations)
4. **Missing Values:** Some PSI records may have null regional readings

### Validation Checks Required
1. Check for timestamp gaps in PSI data
2. Verify fire data coverage during haze seasons (Jun-Oct)
3. Handle missing weather data with forward-fill or interpolation
4. Filter out PSI records with invalid/null national readings

---

## API Rate Limits & Costs

| API | Rate Limit | Cost | Notes |
|-----|------------|------|-------|
| FIRMS | 10,000 requests/day | Free | Monitor transaction count |
| Open-Meteo | ~10,000 requests/day | Free | Fair use policy |
| PSI (Current) | Unlimited (for now) | Free | Rate limits after Dec 31, 2025 |
| PSI (Historical) | 100 records/request | Free | Paginate large queries |

---

## Next Steps

1. Download historical PSI dataset (94K records) ’ CSV cache
2. Fetch VIIRS fire data for 2014-2025 (via FIRMS archive download)
3. Fetch ERA5 weather data for 2014-2025 (via Open-Meteo archive API)
4. Align all three datasets on common timestamps
5. Engineer features (fire risk, wind transport, baseline)
6. Train linear regression models for 4 horizons

**Estimated Download Time:** 2-4 hours (depending on API response times)
**Estimated Storage:** ~500 MB (raw data), ~100 MB (processed features)

---

Status: Ready for Implementation
