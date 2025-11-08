#!/usr/bin/env python3
"""
Download ERA5 reanalysis data for Singapore region.
This script downloads wind, temperature, and precipitation data from 2016-2024.
"""

import cdsapi
import os

# Ensure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

dataset = "reanalysis-era5-single-levels"
request = {
    "product_type": ["reanalysis"],
    "variable": [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_dewpoint_temperature",
        "2m_temperature",
        "mean_wave_direction",
        "sea_surface_temperature",
        "total_precipitation"
    ],
    "year": [
        "2016", "2017", "2018",
        "2019", "2020", "2021",
        "2022", "2023", "2024"
    ],
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "06:00", "12:00",
        "18:00"
    ],
    "data_format": "grib",
    "download_format": "unarchived"
}

print("Initializing CDS API client...")
client = cdsapi.Client()

print("Submitting download request...")
print("Note: This may take a while as it's downloading ~9 years of data")
print(f"Output will be saved to: {os.getcwd()}")

client.retrieve(dataset, request).download("era5_data.grib")
print("Download complete!")
