import requests
import pandas as pd
from datetime import datetime, timedelta

# Helper functions
def get_psi_status(psi_value):
    """Return PSI status based on value"""
    if psi_value <= 50:
        return "Good"
    elif psi_value <= 100:
        return "Moderate"
    elif psi_value <= 200:
        return "Unhealthy"
    elif psi_value <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"

def get_health_advisory(psi_value):
    """Return health advisory based on PSI"""
    if psi_value <= 50:
        return "Air quality is good. Normal activities can continue."
    elif psi_value <= 100:
        return "Air quality is moderate. Sensitive individuals should limit prolonged outdoor activities."
    elif psi_value <= 200:
        return "Air quality is unhealthy. Reduce prolonged or strenuous outdoor activities."
    elif psi_value <= 300:
        return "Air quality is very unhealthy. Minimize outdoor activities. Sensitive groups should avoid outdoor activities."
    else:
        return "Air quality is hazardous. Avoid outdoor activities. Everyone should remain indoors and keep activity levels low."

print("=" * 80)
print("TESTING SINGAPORE PSI (POLLUTANT STANDARDS INDEX) API")
print("=" * 80)
print("\nPSI measures air quality across 5 regions in Singapore:")
print("- North, South, East, West, Central")
print("- National reading = maximum of all regions")
print("\nUpdated every 15 minutes")
print("=" * 80)

# Test 1: Current Real-time PSI
print("\n" + "=" * 80)
print("TEST 1: CURRENT REAL-TIME PSI DATA")
print("=" * 80)

url = "https://api.data.gov.sg/v1/environment/psi"

try:
    response = requests.get(url)
    data = response.json()

    if 'items' in data and len(data['items']) > 0:
        latest = data['items'][0]
        timestamp = latest['timestamp']
        readings = latest['readings']

        print(f"\n✓ Successfully retrieved PSI data")
        print(f"📅 Timestamp: {timestamp}")
        print(f"🔄 Update time: {latest.get('update_timestamp', 'N/A')}")

        # Display PSI readings by region
        print("\n" + "-" * 80)
        print("PSI READINGS BY REGION")
        print("-" * 80)

        regions = ['west', 'national', 'east', 'central', 'south', 'north']

        if 'psi_twenty_four_hourly' in readings:
            psi_24h = readings['psi_twenty_four_hourly']
            print("\n24-Hour PSI:")
            for region in regions:
                if region in psi_24h:
                    value = psi_24h[region]
                    status = get_psi_status(value)
                    print(f"  {region.capitalize():10s}: {value:3d}  [{status}]")

        # Display pollutant sub-indices
        print("\n" + "-" * 80)
        print("POLLUTANT SUB-INDICES (24-Hour)")
        print("-" * 80)

        pollutants = {
            'o3_sub_index': 'Ozone (O3)',
            'pm10_twenty_four_hourly': 'PM10',
            'pm25_twenty_four_hourly': 'PM2.5',
            'co_sub_index': 'Carbon Monoxide (CO)',
            'no2_one_hour_max': 'Nitrogen Dioxide (NO2)',
            'so2_twenty_four_hourly': 'Sulfur Dioxide (SO2)'
        }

        for key, name in pollutants.items():
            if key in readings:
                print(f"\n{name}:")
                values = readings[key]
                for region in regions:
                    if region in values:
                        print(f"  {region.capitalize():10s}: {values[region]}")

        # Find highest pollutant
        print("\n" + "-" * 80)
        print("AIR QUALITY ANALYSIS")
        print("-" * 80)

        if 'psi_twenty_four_hourly' in readings:
            psi_24h = readings['psi_twenty_four_hourly']

            # Get national PSI or calculate it as max of regions
            if 'national' in psi_24h:
                national_psi = psi_24h['national']
            else:
                # Calculate national as max of all regions
                regional_values = {k: v for k, v in psi_24h.items()
                                  if k in ['north', 'south', 'east', 'west', 'central']}
                national_psi = max(regional_values.values()) if regional_values else None

            if national_psi is not None:
                status = get_psi_status(national_psi)
                print(f"\n🇸🇬 National PSI: {national_psi} [{status}]")

                # Find which region has the highest PSI
                psi_values = {k: v for k, v in psi_24h.items()
                             if k in ['north', 'south', 'east', 'west', 'central']}
                max_region = max(psi_values, key=psi_values.get)
                max_value = psi_values[max_region]

                print(f"🔴 Highest PSI Region: {max_region.capitalize()} ({max_value})")

                # Health recommendations
                print(f"\n💡 Health Advisory:")
                print(get_health_advisory(national_psi))
            else:
                print("\n⚠️  National PSI not available")

    else:
        print("❌ No data available in response")
        print(f"Response: {data}")

except Exception as e:
    print(f"❌ Error fetching current PSI: {e}")

# Test 2: Historical PSI data
print("\n\n" + "=" * 80)
print("TEST 2: HISTORICAL PSI DATA (Past 24 hours)")
print("=" * 80)

now = datetime.now()
yesterday = now - timedelta(days=1)

params = {
    'date_time': yesterday.strftime('%Y-%m-%dT%H:%M:%S'),
}

try:
    response = requests.get(url, params=params)
    data = response.json()

    if 'items' in data:
        print(f"\n✓ Retrieved {len(data['items'])} historical records")

        # Convert to DataFrame for analysis
        records = []
        for item in data['items']:
            timestamp = item['timestamp']
            if 'psi_twenty_four_hourly' in item['readings']:
                psi = item['readings']['psi_twenty_four_hourly']
                records.append({
                    'timestamp': timestamp,
                    'national': psi.get('national', None),
                    'north': psi.get('north', None),
                    'south': psi.get('south', None),
                    'east': psi.get('east', None),
                    'west': psi.get('west', None),
                    'central': psi.get('central', None)
                })

        if records:
            df = pd.DataFrame(records)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            print("\nRecent PSI Trends:")
            print(df.head(10).to_string(index=False))

            print("\n24-Hour Statistics:")
            print(df.describe().round(1))

            # Check for any alerts
            max_psi = df['national'].max()
            if max_psi > 100:
                print(f"\n⚠️  WARNING: PSI exceeded 100 in the past 24 hours!")
                print(f"   Maximum PSI: {max_psi}")
                alert_times = df[df['national'] > 100]['timestamp']
                print(f"   Alert periods: {len(alert_times)}")
        else:
            print("No PSI records found in historical data")

except Exception as e:
    print(f"❌ Error fetching historical PSI: {e}")

# Test 3: Historical dataset from datastore
print("\n\n" + "=" * 80)
print("TEST 3: HISTORICAL PSI DATASET (Archive)")
print("=" * 80)

dataset_id = "d_b4cf557f8750260d229c49fd768e11ed"
datastore_url = "https://data.gov.sg/api/action/datastore_search"
params = {
    'resource_id': dataset_id,
    'limit': 10
}

try:
    response = requests.get(datastore_url, params=params)
    data = response.json()

    if data.get('success') and 'result' in data:
        result = data['result']
        records = result.get('records', [])
        total = result.get('total', 0)

        print(f"\n✓ Historical dataset available")
        print(f"  Total records in dataset: {total}")
        print(f"  Showing latest {len(records)} records:")

        if records:
            df_hist = pd.DataFrame(records)
            print("\n" + df_hist.to_string(index=False))
    else:
        print("❌ Could not access historical dataset")
        print(f"Response: {data}")

except Exception as e:
    print(f"❌ Error fetching historical dataset: {e}")

print("\n" + "=" * 80)
print("API INFORMATION")
print("=" * 80)
print("""
✓ No authentication required (currently)
✓ Rate limits coming December 31, 2025
✓ Updates every 15 minutes
✓ Free for commercial and personal use
✓ Data from National Environment Agency (NEA)

PSI Measurement:
- PM2.5, PM10, O3, CO, NO2, SO2 sub-indices
- 24-hour and 1-hour readings
- 5 regions + national reading

Documentation: https://data.gov.sg/datasets/d_fe37906a0182569d891506e815e819b7/view
API Guide: https://guide.data.gov.sg/developer-guide/real-time-apis
""")

print("=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
