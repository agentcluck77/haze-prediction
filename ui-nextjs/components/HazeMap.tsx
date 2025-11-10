'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Popup, Circle, useMap, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '@/lib/api';
import type { FireDetection } from '@/types/api';

interface WindData {
  lat: number;
  lng: number;
  speed: number; // m/s
  direction: number; // degrees
}

interface HazeMapProps {
  showFires?: boolean;
  showWind?: boolean;
}

// Wind arrows component - renders multiple wind vectors with variable length
function WindArrows({ windData }: { windData: WindData[] }) {
  const map = useMap();

  useEffect(() => {
    const markers: L.Marker[] = [];

    windData.forEach(({ lat, lng, speed, direction }) => {
      // Skip if no wind data
      if (!speed && !direction) return;

      // Calculate arrow length based on wind speed
      // Base length: 10px, scale factor: 3px per m/s, max length: 50px
      const baseLength = 15;
      const scaleFactor = 1.5;
      // const maxLength = 50;
      const arrowLength = baseLength + speed * scaleFactor;

      // Calculate color based on speed (cyan-blue-purple scheme to avoid clash with red fires)
      const getWindColor = (speed: number) => {
        if (speed < 2) return '#06b6d4'; // Cyan - calm
        if (speed < 5) return '#3b82f6'; // Blue - light breeze
        if (speed < 8) return '#6366f1'; // Indigo - moderate
        return '#8b5cf6'; // Purple - strong wind
      };

      const windColor = getWindColor(speed);

      // SVG size - make it large enough to accommodate any arrow length plus padding
      const padding = 10;
      const svgSize = Math.max(80, (arrowLength + padding) * 2);
      const center = svgSize / 2;

      const svg = `
        <svg width="${svgSize}" height="${svgSize}" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="arrowhead-${lat}-${lng}" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
              <polygon points="0 0, 5 2.5, 0 5" fill="${windColor}" fill-opacity="0.5" />
            </marker>
          </defs>
          <line
            x1="${center}"
            y1="${center}"
            x2="${center}"
            y2="${center - arrowLength}"
            stroke="${windColor}"
            stroke-width="2"
            stroke-opacity="0.5"
            marker-end="url(#arrowhead-${lat}-${lng})"
            transform="rotate(${direction} ${center} ${center})"
          />
          <circle cx="${center}" cy="${center}" r="2.5" fill="${windColor}" opacity="0.4" />
        </svg>
      `;

      const windIcon = L.divIcon({
        html: svg,
        className: 'wind-arrow',
        iconSize: [svgSize, svgSize],
        iconAnchor: [center, center],
      });

      const marker = L.marker([lat, lng], { icon: windIcon }).addTo(map);
      marker.bindPopup(`
        <div class="text-sm">
          <div class="font-semibold mb-1">Wind Data</div>
          <div>Speed: <span class="font-medium">${speed.toFixed(1)} m/s</span> (${(speed * 3.6).toFixed(1)} km/h)</div>
          <div>Direction: <span class="font-medium">${direction.toFixed(0)}°</span></div>
          <div class="text-xs text-gray-500 mt-1">Location: ${lat.toFixed(2)}, ${lng.toFixed(2)}</div>
        </div>
      `);

      markers.push(marker);
    });

    return () => {
      markers.forEach(marker => map.removeLayer(marker));
    };
  }, [map, windData]);

  return null;
}

export default function HazeMap({ showFires = true, showWind = true}: HazeMapProps) {
  const [mounted, setMounted] = useState(false);
  // Local toggle state so checkboxes can control visibility
  const [showFiresState, setShowFiresState] = useState<boolean>(showFires);
  const [showWindState, setShowWindState] = useState<boolean>(showWind);

  // Fetch fire data from API
  const [fires, setFires] = useState<FireDetection[]>([]);

  // Fetch wind data from API - now an array of wind vectors across the region
  const [windData, setWindData] = useState<WindData[]>([]);
  
  const [hazeLevel, setHazeLevel] = useState(0); // PSI value from API
  
  // Singapore center coordinates
  const center: [number, number] = [1.3521, 103.8198];
  
  useEffect(() => {
    setMounted(true);

    // Fetch fires data
    const fetchFires = async () => {
      try {
        const firesData = await api.getCurrentFires();
        setFires(firesData.fires || []);
      } catch (error) {
        console.error('Failed to fetch fires data:', error);
      }
    };

    // Fetch weather/wind data for a grid of locations across the region
    const fetchWeather = async () => {
      try {
        // Create a grid of locations across Indonesia-Singapore-Malaysia region
        // Bounding box: 95,-11,141,6 (west, south, east, north)
        const windVectors: WindData[] = [];

        // Grid spacing: increased density with smaller steps
        const latStart = -10;
        const latEnd = 5;
        const lngStart = 95;
        const lngEnd = 140;
        const latStep = 2.5; // Reduced from 5 to 2.5 degrees
        const lngStep = 4;   // Reduced from 8 to 4 degrees

        // Fetch wind data for grid points from Open-Meteo API
        const promises = [];
        for (let lat = latStart; lat <= latEnd; lat += latStep) {
          for (let lng = lngStart; lng <= lngEnd; lng += lngStep) {
            promises.push(
              fetch(
                `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=wind_speed_10m,wind_direction_10m&timezone=auto`
              )
                .then(res => res.json())
                .then(data => ({
                  lat,
                  lng,
                  speed: data.current?.wind_speed_10m || 0,
                  direction: data.current?.wind_direction_10m || 0,
                }))
                .catch(() => null)
            );
          }
        }

        // Wait for all requests
        const results = await Promise.all(promises);
        const validResults = results.filter(r => r !== null) as WindData[];
        setWindData(validResults);

      } catch (error) {
        console.error('Failed to fetch weather data:', error);
      }
    };

    // Fetch PSI data for haze level
    const fetchPSI = async () => {
      try {
        const psiData = await api.getCurrentPSI();
        if (psiData?.readings?.psi_24h?.national) {
          setHazeLevel(psiData.readings.psi_24h.national);
        }
      } catch (error) {
        console.error('Failed to fetch PSI data:', error);
      }
    };

    fetchFires();
    fetchWeather();
    fetchPSI();

    // Refresh data periodically
    const firesInterval = setInterval(fetchFires, 15 * 60 * 1000); // 15 minutes
    const weatherInterval = setInterval(fetchWeather, 30 * 60 * 1000); // 30 minutes (multiple API calls)
    const psiInterval = setInterval(fetchPSI, 15 * 60 * 1000); // 15 minutes

    return () => {
      clearInterval(firesInterval);
      clearInterval(weatherInterval);
      clearInterval(psiInterval);
    };
  }, []);
  
  if (!mounted) {
    return (
      <div className="w-full h-[600px] bg-gray-200 dark:bg-gray-700 animate-pulse rounded-lg flex items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Loading map...</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700">
        <div className="flex flex-wrap gap-4 items-center">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showFiresState}
              onChange={(e) => setShowFiresState(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-gray-900 dark:text-gray-100 font-medium">Show Fires</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showWindState}
              onChange={(e) => setShowWindState(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-gray-900 dark:text-gray-100 font-medium">Show Wind</span>
          </label>


          <div className="ml-auto flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Haze Level:</span>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              hazeLevel < 50 ? 'bg-green-100 text-green-800' :
              hazeLevel < 100 ? 'bg-yellow-100 text-yellow-800' :
              hazeLevel < 200 ? 'bg-orange-100 text-orange-800' :
              'bg-red-100 text-red-800'
            }`}>
              {hazeLevel} PSI
            </span>
          </div>
        </div>
      </div>
      
      {/* Map */}
      <div className="w-full h-[600px] rounded-lg overflow-hidden shadow-lg border dark:border-gray-700">
        <MapContainer
          center={center}
          zoom={11}
          style={{ height: '100%', width: '100%' }}
          className="z-0"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png"
          />
          
          {/* Fire markers */}
          {showFiresState && fires.map((fire, index) => (
            <CircleMarker
              key={`${fire.latitude}-${fire.longitude}-${index}`}
              center={[fire.latitude, fire.longitude]}
              radius={8}
              pathOptions={{
                fillColor: '#ef4444',
                fillOpacity: 0.8,
                color: '#dc2626',
                weight: 2,
              }}
            >
              <Popup>
                <div className="min-w-[200px]">
                  <p className="font-semibold text-red-600 mb-2">🔥 Fire Detected</p>
                  <div className="space-y-1 text-sm">
                    <p>Confidence: <span className="font-medium">{fire.confidence.toUpperCase()}</span></p>
                    <p>Brightness: <span className="font-medium">{fire.brightness.toFixed(1)}K</span></p>
                    <p>FRP: <span className="font-medium">{fire.frp.toFixed(1)} MW</span></p>
                    <p>Distance: <span className="font-medium">{fire.distance_to_singapore_km.toFixed(1)} km</span></p>
                    <p>Satellite: <span className="font-medium">{fire.satellite}</span></p>
                    <p className="text-xs text-gray-500 mt-2">
                      {fire.acq_date} {fire.acq_time}
                    </p>
                    <p className="text-xs text-gray-500">
                      Lat: {fire.latitude.toFixed(4)}, Lng: {fire.longitude.toFixed(4)}
                    </p>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
          
          {/* Wind arrows */}
          {showWindState && windData.length > 0 && <WindArrows windData={windData} />}
        </MapContainer>
      </div>
      
      {/* Legend */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Legend</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700 dark:text-gray-300">
          {/* Fire Legend */}
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-red-500 rounded-full"></div>
            <span>Fire Detection (VIIRS)</span>
          </div>

          {/* Wind Legend */}
          <div>
            <div className="font-medium mb-2">Wind Vectors (length = speed)</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-[#06b6d4] rounded-full"></div>
                <span>&lt; 2 m/s (Calm)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-[#3b82f6] rounded-full"></div>
                <span>2-5 m/s (Light)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-[#6366f1] rounded-full"></div>
                <span>5-8 m/s (Moderate)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-[#8b5cf6] rounded-full"></div>
                <span>&gt; 8 m/s (Strong)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}