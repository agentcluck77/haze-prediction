import xarray as xr

# Load the data
ds = xr.open_dataset('wind_data.nc')

# Inspect what you got
print(ds)
print(f"\nShape: {ds['u10'].shape}")
print(f"Time range: {ds.valid_time.values[0]} to {ds.valid_time.values[-1]}")
print(f"Lat range: {ds.latitude.values.min()} to {ds.latitude.values.max()}")
print(f"Lon range: {ds.longitude.values.min()} to {ds.longitude.values.max()}")

# Quick plot to verify
import matplotlib.pyplot as plt

# Pick first timestep
u = ds['u10'].isel(valid_time=0)
v = ds['v10'].isel(valid_time=0)

plt.figure(figsize=(10, 6))
plt.quiver(ds.longitude[::5], ds.latitude[::5], 
           u[::5, ::5], v[::5, ::5])
plt.title('Wind vectors - first timestep')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.savefig('wind_check.png')
print("\nSaved wind_check.png to verify data looks correct")