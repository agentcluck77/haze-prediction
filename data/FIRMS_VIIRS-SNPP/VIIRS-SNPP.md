Layer Information: VIIRS (Suomi NPP, NOAA-20 and NOAA-21) Fires and Thermal Anomalies (Day | Night, 375m)
VIIRS S-NPP TEMPORAL COVERAGE: 20 JANUARY 2012 - PRESENT
VIIRS NOAA-20 TEMPORAL COVERAGE: 1 JANUARY 2020 - PRESENT
VIIRS NOAA-21 TEMPORAL COVERAGE: 17 JANUARY 2024 - PRESENT
Latency - defined as time since satellite observation and the data being available in FIRMS:
within 3 hours for global data and
within 1-30 minutes for ultra and real-time in the US and Canada (see 'version' in attribute table below).

The VIIRS (Visible Infrared Imaging Radiometer Suite) Fire layer shows active fire detections and thermal anomalies, such as volcanoes, and gas flares. The fire layer is useful for studying the spatial and temporal distribution of fire, to locate persistent hot spots such as volcanoes and gas flares, to locate the source of air pollution from smoke that may have adverse human health impacts.

VIIRS is the successor to MODIS for Earth science data product generation. The 375m I-band data complements the MODIS fire detections; they both show good agreement in hotspot detection but the improved spatial resolution of the 375m data provides a greater response over fires of relatively small areas and provides improved mapping of large fire perimeters. The 375m data also has improved nighttime performance. Consequently, these data are well suited for use in support of fire management (e.g., near real-time alert systems), as well as other science applications requiring improved fire mapping fidelity.

The VIIRS Fire and Thermal Anomalies product is available from the joint NASA/NOAA Suomi-National Polar orbiting Partnership (S-NPP), NOAA-20 (JPSS-1) and NOAA-21 (JPSS-2) satellites. The sensor resolution is 375 m, imagery resolution is 250 m, and the temporal resolution is twice daily. The thermal anomalies are represented as red points (approximate center of a 375m pixel). The nominal (equator-crossing) observation times for VIIRS S-NPP are 1:30pm and 1:30am. The orbit of NOAA-21 is about 50 minutes ahead of NOAA-20 with S-NPP orbiting between them. Consequently, all three sensors conduct observations within approximately 1 hour of one another. Thanks to its polar orbit, mid-latitudes will experience 3-4 looks a day.


Attributes:

Attribute
Short Description
Long Description
Latitude	Latitude	Center of nominal 375 m fire pixel.
Longitude	Longitude	Center of nominal 375 m fire pixel.
Bright_ti4 / Brightness (in web services)	Brightness temperature I-4	VIIRS I-4 channel brightness temperature of the fire pixel measured in Kelvin.
Scan	Along Scan pixel size	The algorithm produces approximately 375 m pixels at nadir. Scan and track reflect actual pixel size.
Track	Along Track pixel size	The algorithm produces approximately 375 m pixels at nadir. Scan and track reflect actual pixel size.
Acq_Date	Acquisition Date	Date of VIIRS acquisition.
Acq_Time	Acquisition Time	Time of acquisition/overpass of the satellite (in UTC).
Satellite	Satellite	N = Suomi National Polar-orbiting Partnership (Suomi NPP).
N20 = NOAA-20 (JPSS1).
N21 = NOAA-21 (JPSS2).
Confidence	Confidence	
This value is based on a collection of intermediate algorithm quantities used in the detection process. It is intended to help users gauge the quality of individual hotspot/fire pixels. Confidence values are set to low (l), nominal (n), and high (h). Low (l) confidence daytime fire pixels are typically associated with areas of Sun glint and lower relative temperature anomaly (<15 K) in the mid-infrared channel I4. Nominal (n) confidence pixels are those free of potential Sun glint contamination during the day and marked by strong (>15 K) temperature anomaly in either day or nighttime data. High (h) confidence fire pixels are associated with day or nighttime saturated pixels.

Please note: Low confidence nighttime pixels occur only over the geographic area extending from 11° E to 110° W and 7° N to 55° S. This area describes the region of influence of the South Atlantic Magnetic Anomaly which can cause spurious brightness temperatures in the mid-infrared channel I4 leading to potential false positive alarms. These have been removed from the NRT data distributed by FIRMS.

Version	Version (collection and source)	
Version identifies the collection (e.g., VIIRS Collection 1 or VIIRS Collection 2), and source of data processing (Ultra Real-Time (URT suffix added to collection), Real-Time (RT suffix), Near Real-Time (NRT suffix) or Standard Processing (collection only). For example:

"2.0URT" - Collection 2 Ultra Real-Time processing.
"2.0RT" - Collection 2 Real-Time processing.
"1.0NRT" - Collection 1 Near Real-Time processing.
"1.0" - Collection 1 Standard processing.

Bright_ti5 / Brightness_2 (in web services)	Brightness temperature I-5	I-5 Channel brightness temperature of the fire pixel measured in Kelvin.
FRP	Fire Radiative Power	
FRP depicts the pixel-integrated fire radiative power in megawatts (MW). Given the unique spatial and spectral resolution of the data, the VIIRS 375 m fire detection algorithm was customized and tuned to optimize its response over small fires while balancing the occurrence of false alarms. Frequent saturation of the mid-infrared I4 channel (3.55-3.93 µm) driving the detection of active fires requires additional tests and procedures to avoid pixel classification errors. As a result, sub-pixel fire characterization (e.g., fire radiative power [FRP] retrieval) is only viable across small and/or low-intensity fires. Systematic FRP retrievals are based on a hybrid approach combining 375 and 750 m data. In fact, starting in 2015 the algorithm incorporated additional VIIRS channel M13 (3.973-4.128 µm) 750 m data in both aggregated and unaggregated format.

Type*	Inferred hot spot type	0 = presumed vegetation fire
1 = active volcano
2 = other static land source
3 = offshore detection (includes all detections over water)
DayNight	Day or Night	
D= Daytime fire, N= Nighttime fire

Type* = This attribute is only available for VNP14IMGT (standard quality) data

more details:
VIIRS S-NPP NRT fire 
VIIRS NOAA-20 NRT fire 
VIIRS NOAA-21 NRT fire 