import pandas as pd
import requests
from datetime import datetime

# Your FIRMS MAP_KEY
MAP_KEY = 'f6cd6de4fa5a42514a72c8525064e890'

print("=" * 70)
print("TESTING FIRE DETECTION FOR INDONESIA")
print("=" * 70)

# Indonesia bounding box (approximate)
# West: 95°E, South: -11°S, East: 141°E, North: 6°N
west, south, east, north = 95, -11, 141, 6

print(f"\nSearching area: {west}°E to {east}°E, {south}°S to {north}°N")
print("This covers: Sumatra, Java, Kalimantan, Sulawesi, Papua, etc.")

# Test multiple datasets and time periods
datasets = [
    ('VIIRS_NOAA20_NRT', 'VIIRS NOAA-20 (375m resolution)'),
    ('VIIRS_SNPP_NRT', 'VIIRS Suomi-NPP (375m resolution)'),
    ('MODIS_NRT', 'MODIS Terra/Aqua (1km resolution)'),
]

day_ranges = [1, 3, 7]

for dataset_id, dataset_name in datasets:
    print("\n" + "=" * 70)
    print(f"Dataset: {dataset_name}")
    print("=" * 70)

    for days in day_ranges:
        area_url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{dataset_id}/{west},{south},{east},{north}/{days}'

        try:
            df = pd.read_csv(area_url)
            num_fires = len(df)

            print(f"\n  Last {days} day(s): {num_fires} fire detections")

            if num_fires > 0:
                # Calculate statistics
                total_frp = df['frp'].sum()
                avg_frp = df['frp'].mean()
                max_brightness = df['bright_ti4'].max() if 'bright_ti4' in df.columns else df['brightness'].max()

                # Count by confidence
                if 'confidence' in df.columns:
                    confidence_counts = df['confidence'].value_counts()
                    print(f"    - High confidence: {confidence_counts.get('h', 0)}")
                    print(f"    - Normal confidence: {confidence_counts.get('n', 0)}")
                    print(f"    - Low confidence: {confidence_counts.get('l', 0)}")

                print(f"    - Total Fire Radiative Power: {total_frp:.2f} MW")
                print(f"    - Average FRP per detection: {avg_frp:.2f} MW")
                print(f"    - Max brightness temperature: {max_brightness:.2f} K")

                # Show regional breakdown (by island approximation)
                print(f"\n    Regional breakdown:")

                # Sumatra: 95-106°E
                sumatra = df[(df['longitude'] >= 95) & (df['longitude'] < 106)]
                print(f"      Sumatra region: {len(sumatra)} fires")

                # Java: 106-115°E, south of 0°
                java = df[(df['longitude'] >= 106) & (df['longitude'] < 115) & (df['latitude'] < 0)]
                print(f"      Java region: {len(java)} fires")

                # Kalimantan (Borneo): 109-119°E
                kalimantan = df[(df['longitude'] >= 109) & (df['longitude'] < 119) &
                               (df['latitude'] >= -4) & (df['latitude'] < 7)]
                print(f"      Kalimantan region: {len(kalimantan)} fires")

                # Papua: >130°E
                papua = df[df['longitude'] >= 130]
                print(f"      Papua region: {len(papua)} fires")

                # Show sample of recent detections
                if days == 1:
                    print(f"\n    Most recent 5 detections:")
                    sample = df.nsmallest(5, 'acq_time')[['latitude', 'longitude', 'bright_ti4' if 'bright_ti4' in df.columns else 'brightness',
                                                            'frp', 'acq_date', 'acq_time', 'confidence']]
                    print(sample.to_string(index=False))

        except Exception as e:
            print(f"\n  Last {days} day(s): Error - {e}")

# Check transaction usage
print("\n" + "=" * 70)
print("API Usage Summary")
print("=" * 70)
status_url = f'https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={MAP_KEY}'
try:
    response = requests.get(status_url)
    data = response.json()
    print(f"Transactions used: {data['current_transactions']}/{data['transaction_limit']}")
    print(f"Resets every: {data['transaction_interval']}")
except Exception as e:
    print(f"Error checking usage: {e}")

print("\n" + "=" * 70)
print("TESTING COMPLETE")
print("=" * 70)
print("\nNote: Fire activity in Indonesia is typically highest during dry season")
print("(June-October) and can be related to agricultural burning, peatland fires,")
print("and deforestation.")
