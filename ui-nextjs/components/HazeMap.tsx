'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { FireDetection } from '@/types/api';

// Import maplibre-gl dynamically (client-side only)
let maplibregl: any = null;

interface HazeMapProps {
  showFires?: boolean;
  showWind?: boolean;
}

export default function HazeMap({ showFires = true, showWind = true }: HazeMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const [mounted, setMounted] = useState(false);
  const [showFiresState, setShowFiresState] = useState<boolean>(showFires);
  const [showWindState, setShowWindState] = useState<boolean>(showWind);
  const [fires, setFires] = useState<FireDetection[]>([]);
  const [hazeLevel, setHazeLevel] = useState(0);

  // Initialize map (client-side only)
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    setMounted(true);

    // Load maplibre-gl client-side
    if (!maplibregl) {
      maplibregl = require('maplibre-gl');
    }

    // Create map
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'carto-light': {
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
              'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
              'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
              'https://d.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          }
        },
        layers: [
          {
            id: 'carto-light-layer',
            type: 'raster',
            source: 'carto-light',
            minzoom: 0,
            maxzoom: 22
          }
        ]
      },
      center: [103.8198, 1.3521], // Singapore
      zoom: 6,
      maxBounds: [
        [90, -15], // Southwest coordinates
        [145, 10]  // Northeast coordinates
      ]
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(new maplibregl.ScaleControl(), 'bottom-left');

    // Load wind arrow icon when map loads
    map.current.on('load', () => {
      if (!map.current) return;

      // Create wind arrow SVG
      const svg = `
        <svg width="40" height="40" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
              <polygon points="0 0, 8 4, 0 8" fill="#3b82f6" />
            </marker>
          </defs>
          <line x1="20" y1="35" x2="20" y2="10" stroke="#3b82f6" stroke-width="3" marker-end="url(#arrowhead)" />
          <circle cx="20" cy="35" r="3" fill="#3b82f6" />
        </svg>
      `;

      const img = new Image(40, 40);
      img.onload = () => {
        if (map.current && !map.current.hasImage('wind-arrow')) {
          map.current.addImage('wind-arrow', img);
          console.log('Wind arrow icon loaded');
        }
      };
      img.src = 'data:image/svg+xml;base64,' + btoa(svg);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Fetch fires data
  useEffect(() => {
    const fetchFires = async () => {
      try {
        const firesData = await api.getCurrentFires();
        console.log('Fires data received:', firesData);
        setFires(firesData.fires || []);
      } catch (error) {
        console.error('Failed to fetch fires data:', error);
      }
    };

    fetchFires();
    const interval = setInterval(fetchFires, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch PSI data
  useEffect(() => {
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

    fetchPSI();
    const interval = setInterval(fetchPSI, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Add fire markers to map
  useEffect(() => {
    if (!map.current || fires.length === 0) {
      console.log('Not adding fires - map:', !!map.current, 'fires:', fires.length);
      return;
    }

    const mapInstance = map.current;

    console.log('Adding fires to map:', fires.length);

    // Wait for map to load
    if (!mapInstance.isStyleLoaded()) {
      console.log('Map style not loaded, waiting...');
      mapInstance.once('load', () => addFireMarkers());
    } else {
      addFireMarkers();
    }

    function addFireMarkers() {
      if (!mapInstance) return;

      console.log('Adding fire markers to map');

      // Remove existing fire layers
      if (mapInstance.getLayer('fires-layer')) {
        mapInstance.removeLayer('fires-layer');
      }
      if (mapInstance.getSource('fires')) {
        mapInstance.removeSource('fires');
      }

      // Convert fires to GeoJSON
      const geojson: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: fires.map((fire) => ({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [fire.longitude, fire.latitude]
          },
          properties: {
            confidence: fire.confidence,
            brightness: fire.brightness,
            frp: fire.frp,
            distance: fire.distance_to_singapore_km,
            satellite: fire.satellite,
            acq_date: fire.acq_date,
            acq_time: fire.acq_time
          }
        }))
      };

      // Add source
      mapInstance.addSource('fires', {
        type: 'geojson',
        data: geojson
      });

      // Add layer
      mapInstance.addLayer({
        id: 'fires-layer',
        type: 'circle',
        source: 'fires',
        paint: {
          'circle-radius': 8,
          'circle-color': '#ef4444',
          'circle-opacity': 0.8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#dc2626'
        }
      });

      console.log('Fire layer added successfully');

      // Add click handler for popups
      mapInstance.on('click', 'fires-layer', (e: any) => {
        if (!e.features || e.features.length === 0) return;

        const feature = e.features[0];
        const props = feature.properties;

        new (maplibregl as any).Popup()
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="text-sm">
              <p class="font-semibold text-red-600 mb-2">🔥 Fire Detected</p>
              <div class="space-y-1">
                <p>Confidence: <span class="font-medium">${props?.confidence?.toUpperCase()}</span></p>
                <p>Brightness: <span class="font-medium">${props?.brightness?.toFixed(1)}K</span></p>
                <p>FRP: <span class="font-medium">${props?.frp?.toFixed(1)} MW</span></p>
                <p>Distance: <span class="font-medium">${props?.distance?.toFixed(1)} km</span></p>
                <p>Satellite: <span class="font-medium">${props?.satellite}</span></p>
                <p class="text-xs text-gray-500 mt-2">${props?.acq_date} ${props?.acq_time}</p>
              </div>
            </div>
          `)
          .addTo(mapInstance);
      });

      // Change cursor on hover
      mapInstance.on('mouseenter', 'fires-layer', () => {
        mapInstance.getCanvas().style.cursor = 'pointer';
      });
      mapInstance.on('mouseleave', 'fires-layer', () => {
        mapInstance.getCanvas().style.cursor = '';
      });
    }
  }, [fires]);

  // Add/remove wind layer
  useEffect(() => {
    if (!map.current) return;

    const mapInstance = map.current;

    async function toggleWindLayer() {
      if (!mapInstance) return;

      const windLayerId = 'wind-layer';

      console.log('Toggle wind layer:', showWindState);

      if (showWindState) {
        // Fetch wind data and create a canvas layer
        try {
          // Fetch wind data for grid
          const windData = [];
          const latStart = -10;
          const latEnd = 5;
          const lngStart = 95;
          const lngEnd = 140;
          const latStep = 2.5;
          const lngStep = 4;

          console.log('Fetching wind data for canvas layer...');

          for (let lat = latStart; lat <= latEnd; lat += latStep) {
            for (let lng = lngStart; lng <= lngEnd; lng += lngStep) {
              try {
                const response = await fetch(
                  `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=wind_speed_10m,wind_direction_10m&timezone=auto`
                );
                const data = await response.json();
                if (data.current) {
                  windData.push({
                    lat,
                    lng,
                    speed: data.current.wind_speed_10m || 0,
                    direction: data.current.wind_direction_10m || 0,
                  });
                }
              } catch (err) {
                console.error('Error fetching wind for', lat, lng, err);
              }
            }
          }

          console.log('Wind data fetched:', windData.length, 'points');

          // Remove existing wind layer if it exists
          if (mapInstance.getLayer(windLayerId)) {
            mapInstance.removeLayer(windLayerId);
          }
          if (mapInstance.getSource('wind-source')) {
            mapInstance.removeSource('wind-source');
          }

          // Create GeoJSON features for wind arrows
          const windFeatures = windData.map((wind) => ({
            type: 'Feature' as const,
            geometry: {
              type: 'Point' as const,
              coordinates: [wind.lng, wind.lat],
            },
            properties: {
              speed: wind.speed,
              direction: wind.direction,
              // Create arrow SVG for symbol layer
              icon: 'wind-arrow'
            },
          }));

          const geojson = {
            type: 'FeatureCollection' as const,
            features: windFeatures,
          };

          // Add wind source
          mapInstance.addSource('wind-source', {
            type: 'geojson',
            data: geojson,
          });

          // Add wind arrows as symbols
          mapInstance.addLayer({
            id: windLayerId,
            type: 'symbol',
            source: 'wind-source',
            layout: {
              'icon-image': 'wind-arrow',
              'icon-size': 0.5,
              'icon-rotate': ['get', 'direction'],
              'icon-rotation-alignment': 'map',
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
            },
            paint: {
              'icon-opacity': 0.7,
            },
          });

          console.log('Wind layer added with', windFeatures.length, 'arrows');
        } catch (error) {
          console.error('Error adding wind layer:', error);
        }
      } else {
        // Remove wind layer
        if (mapInstance.getLayer(windLayerId)) {
          console.log('Removing wind layer');
          mapInstance.removeLayer(windLayerId);
        }
        if (mapInstance.getSource('wind-source')) {
          mapInstance.removeSource('wind-source');
        }
      }
    }

    // Wait for map to be fully loaded before adding wind layer
    let timeoutId: NodeJS.Timeout | null = null;

    const addWindLayer = () => {
      if (mapInstance.isStyleLoaded() && mapInstance.hasImage('wind-arrow')) {
        toggleWindLayer();
      } else {
        // Wait a bit and try again
        timeoutId = setTimeout(addWindLayer, 100);
      }
    };

    addWindLayer();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [showWindState]);

  // Toggle fire visibility
  useEffect(() => {
    if (!map.current) return;

    const mapInstance = map.current;

    if (mapInstance.getLayer('fires-layer')) {
      mapInstance.setLayoutProperty(
        'fires-layer',
        'visibility',
        showFiresState ? 'visible' : 'none'
      );
    }
  }, [showFiresState]);

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
        <div ref={mapContainer} className="w-full h-full" />
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
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-blue-500 rounded-full"></div>
            <span>Wind Vectors (Open-Meteo)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
