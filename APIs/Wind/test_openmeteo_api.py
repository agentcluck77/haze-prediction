import requests
import pandas as pd
from datetime import datetime, timedelta

print("=" * 70)
print("TESTING OPEN-METEO WIND API")
print("=" * 70)

# Test locations in Indonesia
locations = [
    {"name": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    {"name": "Surabaya", "lat": -7.2575, "lon": 112.7521},
    {"name": "Medan (Sumatra)", "lat": 3.5952, "lon": 98.6722},
    {"name": "Palembang (Sumatra)", "lat": -2.9761, "lon": 104.7754},
    {"name": "Pontianak (Kalimantan)", "lat": -0.0263, "lon": 109.3425},
    {"name": "Makassar (Sulawesi)", "lat": -5.1477, "lon": 119.4327},
]

# Weather parameters to fetch
params = [
    'temperature_2m',
    'relative_humidity_2m',
    'wind_speed_10m',
    'wind_direction_10m',
    'wind_gusts_10m'
]

print("\n" + "=" * 70)
print("TEST 1: CURRENT WEATHER CONDITIONS")
print("=" * 70)

for loc in locations:
    url = f"https://api.open-meteo.com/v1/forecast"
    params_dict = {
        'latitude': loc['lat'],
        'longitude': loc['lon'],
        'current': ','.join(params),
        'timezone': 'Asia/Jakarta'
    }

    try:
        response = requests.get(url, params=params_dict)
        data = response.json()

        if 'current' in data:
            current = data['current']
            print(f"\n📍 {loc['name']}")
            print(f"   Time: {current['time']}")
            print(f"   Temperature: {current.get('temperature_2m', 'N/A')}°C")
            print(f"   Humidity: {current.get('relative_humidity_2m', 'N/A')}%")
            print(f"   Wind Speed: {current.get('wind_speed_10m', 'N/A')} km/h")
            print(f"   Wind Direction: {current.get('wind_direction_10m', 'N/A')}°")
            print(f"   Wind Gusts: {current.get('wind_gusts_10m', 'N/A')} km/h")
        else:
            print(f"\n❌ {loc['name']}: Error - {data}")
    except Exception as e:
        print(f"\n❌ {loc['name']}: Error - {e}")

print("\n\n" + "=" * 70)
print("TEST 2: 7-DAY HOURLY FORECAST (Jakarta)")
print("=" * 70)

jakarta = locations[0]
url = "https://api.open-meteo.com/v1/forecast"
params_dict = {
    'latitude': jakarta['lat'],
    'longitude': jakarta['lon'],
    'hourly': 'temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m',
    'timezone': 'Asia/Jakarta',
    'forecast_days': 7
}

try:
    response = requests.get(url, params=params_dict)
    data = response.json()

    if 'hourly' in data:
        hourly = data['hourly']
        df = pd.DataFrame({
            'time': pd.to_datetime(hourly['time']),
            'temp_c': hourly['temperature_2m'],
            'wind_speed_kmh': hourly['wind_speed_10m'],
            'wind_dir_deg': hourly['wind_direction_10m'],
            'wind_gusts_kmh': hourly['wind_gusts_10m']
        })

        print(f"\n✓ Retrieved {len(df)} hourly forecasts")
        print(f"\nFirst 24 hours:")
        print(df.head(24).to_string(index=False))

        # Calculate daily statistics
        df['date'] = df['time'].dt.date
        daily_stats = df.groupby('date').agg({
            'wind_speed_kmh': ['mean', 'max'],
            'wind_gusts_kmh': 'max',
            'temp_c': ['mean', 'min', 'max']
        }).round(2)

        print(f"\n\nDaily Wind Statistics:")
        print(daily_stats)

        # Find peak wind periods
        high_wind = df[df['wind_speed_10m'] > 20]
        if len(high_wind) > 0:
            print(f"\n⚠️  High wind periods (>20 km/h): {len(high_wind)} hours")
            print(high_wind[['time', 'wind_speed_kmh', 'wind_gusts_kmh']].head(10).to_string(index=False))
        else:
            print(f"\n✓ No high wind periods (>20 km/h) forecasted")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n\n" + "=" * 70)
print("TEST 3: HISTORICAL WIND DATA (Past 10 days - Jakarta)")
print("=" * 70)

url = "https://api.open-meteo.com/v1/forecast"
params_dict = {
    'latitude': jakarta['lat'],
    'longitude': jakarta['lon'],
    'hourly': 'temperature_2m,wind_speed_10m,wind_direction_10m',
    'past_days': 10,
    'timezone': 'Asia/Jakarta'
}

try:
    response = requests.get(url, params=params_dict)
    data = response.json()

    if 'hourly' in data:
        hourly = data['hourly']
        df_hist = pd.DataFrame({
            'time': pd.to_datetime(hourly['time']),
            'temp_c': hourly['temperature_2m'],
            'wind_speed_kmh': hourly['wind_speed_10m'],
            'wind_dir_deg': hourly['wind_direction_10m']
        })

        # Only keep past data (before now)
        now = datetime.now()
        df_hist = df_hist[df_hist['time'] < now]

        print(f"\n✓ Retrieved {len(df_hist)} hours of historical data")

        # Calculate statistics
        print(f"\nWind Statistics (Past 10 days):")
        print(f"  Average wind speed: {df_hist['wind_speed_kmh'].mean():.2f} km/h")
        print(f"  Maximum wind speed: {df_hist['wind_speed_kmh'].max():.2f} km/h")
        print(f"  Minimum wind speed: {df_hist['wind_speed_kmh'].min():.2f} km/h")

        # Show recent trend
        print(f"\nLast 24 hours:")
        print(df_hist.tail(24)[['time', 'temp_c', 'wind_speed_kmh', 'wind_dir_deg']].to_string(index=False))

except Exception as e:
    print(f"❌ Error: {e}")

print("\n\n" + "=" * 70)
print("TEST 4: ARCHIVE DATA (ERA5 - Historical)")
print("=" * 70)
print("Note: Checking if archive API is available...")

# ERA5 archive for specific date range
start_date = "2024-01-01"
end_date = "2024-01-07"

url = "https://archive-api.open-meteo.com/v1/era5"
params_dict = {
    'latitude': jakarta['lat'],
    'longitude': jakarta['lon'],
    'start_date': start_date,
    'end_date': end_date,
    'hourly': 'temperature_2m,wind_speed_10m',
    'timezone': 'Asia/Jakarta'
}

try:
    response = requests.get(url, params=params_dict)
    data = response.json()

    if 'hourly' in data:
        hourly = data['hourly']
        df_archive = pd.DataFrame({
            'time': pd.to_datetime(hourly['time']),
            'temp_c': hourly['temperature_2m'],
            'wind_speed_kmh': hourly['wind_speed_10m']
        })

        print(f"\n✓ Retrieved archive data from {start_date} to {end_date}")
        print(f"  Total records: {len(df_archive)}")
        print(f"\n  Average wind speed: {df_archive['wind_speed_kmh'].mean():.2f} km/h")
        print(f"  Maximum wind speed: {df_archive['wind_speed_kmh'].max():.2f} km/h")
        print(f"\nSample data:")
        print(df_archive.head(10).to_string(index=False))
    else:
        print(f"❌ Could not retrieve archive data")
        print(f"Response: {data}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("API FEATURES SUMMARY")
print("=" * 70)
print("""
✓ No API key required - completely free!
✓ Global coverage including all of Indonesia
✓ Current weather conditions
✓ 7-day hourly forecast
✓ Historical data (past 10 days via forecast API)
✓ Long-term archive (ERA5 reanalysis data)
✓ High temporal resolution (hourly data)
✓ Multiple weather parameters available

Available parameters:
- Wind: speed, direction, gusts at 10m, 80m, 120m, 180m
- Temperature: 2m, soil temperatures
- Precipitation, humidity, cloud cover
- Pressure, visibility
- And many more!

Documentation: https://open-meteo.com/en/docs
""")

print("=" * 70)
print("TESTING COMPLETE")
print("=" * 70)
