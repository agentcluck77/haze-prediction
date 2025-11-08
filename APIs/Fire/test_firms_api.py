import pandas as pd
import requests

# Your FIRMS MAP_KEY
MAP_KEY = 'f6cd6de4fa5a42514a72c8525064e890'

print("=" * 70)
print("TESTING NASA FIRMS API")
print("=" * 70)

# Test 1: Check MAP_KEY status
print("\n1. Testing MAP_KEY status...")
print("-" * 70)
status_url = 'https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=' + MAP_KEY
try:
    response = requests.get(status_url)
    data = response.json()
    df_status = pd.Series(data)
    print("✓ MAP_KEY is valid!")
    print(df_status)
except Exception as e:
    print(f"✗ Error checking MAP_KEY: {e}")
    exit()

# Test 2: Check data availability
print("\n\n2. Testing data availability...")
print("-" * 70)
da_url = f'https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{MAP_KEY}/all'
try:
    df_availability = pd.read_csv(da_url)
    print("✓ Data availability retrieved successfully!")
    print(df_availability)
except Exception as e:
    print(f"✗ Error getting data availability: {e}")

# Test 3: Get recent fire data for a specific region (e.g., California)
print("\n\n3. Testing area query (California fires, last 1 day)...")
print("-" * 70)
# California approximate bounds: west=-124.4, south=32.5, east=-114.1, north=42.0
area_url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/-124.4,32.5,-114.1,42.0/1'
try:
    df_california = pd.read_csv(area_url)
    print(f"✓ Found {len(df_california)} fire detections in California (last 24 hours)")
    if len(df_california) > 0:
        print("\nFirst 5 records:")
        print(df_california.head())
        print(f"\nTotal fire radiative power (FRP): {df_california['frp'].sum():.2f} MW")
except Exception as e:
    print(f"✗ Error getting area data: {e}")

# Test 4: Get global fire count
print("\n\n4. Testing global fire detection count (last 1 day)...")
print("-" * 70)
world_url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/world/1'
try:
    df_world = pd.read_csv(world_url)
    print(f"✓ Found {len(df_world)} fire detections globally (last 24 hours)")

    # Show breakdown by confidence level
    if len(df_world) > 0:
        confidence_counts = df_world['confidence'].value_counts()
        print("\nBreakdown by confidence level:")
        print(confidence_counts)
except Exception as e:
    print(f"✗ Error getting world data: {e}")

# Test 5: Check transaction usage
print("\n\n5. Final transaction count...")
print("-" * 70)
try:
    response = requests.get(status_url)
    data = response.json()
    df_status = pd.Series(data)
    print(f"✓ Transactions used: {df_status['current_transactions']}/{df_status['transaction_limit']}")
    print(f"  (Resets every {df_status['transaction_interval']})")
except Exception as e:
    print(f"✗ Error checking final status: {e}")

print("\n" + "=" * 70)
print("TESTING COMPLETE")
print("=" * 70)
