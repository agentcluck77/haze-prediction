from dotenv import load_dotenv
import os
import cdsapi

load_dotenv()  # loads .env file

c = cdsapi.Client(
    url=os.environ.get('CDSAPI_URL'),
    key=os.environ.get('CDSAPI_KEY')
)

c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': ['10m_u_component_of_wind', '10m_v_component_of_wind'],
        'year': '2025',
        'month': '11',
        'day': ['02'],
        # 'day': ['0', '02', '03'],  # your dates
        'time': [
            "00:00", "01:00", "02:00",
            "03:00", "04:00", "05:00",
            "06:00", "07:00", "08:00",
            "09:00", "10:00", "11:00",
            "12:00", "13:00", "14:00",
            "15:00", "16:00", "17:00",
            "18:00", "19:00", "20:00",
            "21:00", "22:00", "23:00"
        ],
        'area': [7, 95, -5, 110],  # [N, W, S, E] for Singapore region
        'data_format': 'netcdf',
        'download_format': 'unarchived'
    },
    'wind_data.nc')