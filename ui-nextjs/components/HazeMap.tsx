'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom fire icon
const fireIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ff4444" width="32" height="32">
      <path d="M12 23c-2.2 0-4-1.8-4-4 0-1.5.8-2.8 2-3.5-.1-.3-.2-.7-.2-1 0-1.7 1.3-3 3-3 .5 0 1 .1 1.4.4.1-.5.3-.9.6-1.3-1.7-.7-3-2.4-3-4.4 0-2.6 2.1-4.7 4.7-4.7.8 0 1.5.2 2.2.5-.4.9-.7 1.9-.7 3 0 3.3 2.7 6 6 6v1c0 4.4-3.6 8-8 8z"/>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

interface FireData {
  id: string;
  lat: number;
  lng: number;
  confidence: string;
}

interface WindData {
  speed: number; // m/s
  direction: number; // degrees
}

interface HazeMapProps {
  showFires?: boolean;
  showWind?: boolean;
}

// Wind arrow component
function WindArrow({ speed, direction }: WindData) {
  const map = useMap();
  
  useEffect(() => {
    const center = map.getCenter();
    const svg = `
      <svg width="60" height="60" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="#3b82f6" />
          </marker>
        </defs>
        <line x1="30" y1="30" x2="30" y2="5" stroke="#3b82f6" stroke-width="3" marker-end="url(#arrowhead)" 
              transform="rotate(${direction} 30 30)" />
        <circle cx="30" cy="30" r="4" fill="#3b82f6" />
      </svg>
    `;
    
    const windIcon = L.divIcon({
      html: svg,
      className: 'wind-arrow',
      iconSize: [60, 60],
      iconAnchor: [30, 30],
    });
    
    const marker = L.marker(center, { icon: windIcon }).addTo(map);
    marker.bindPopup(`Wind Speed: ${speed} m/s<br>Direction: ${direction}°`);
    
    return () => {
      map.removeLayer(marker);
    };
  }, [map, speed, direction]);
  
  return null;
}

export default function HazeMap({ showFires = true, showWind = true}: HazeMapProps) {
  const [mounted, setMounted] = useState(false);
  // Local toggle state so checkboxes can control visibility
  const [showFiresState, setShowFiresState] = useState<boolean>(showFires);
  const [showWindState, setShowWindState] = useState<boolean>(showWind);
  
  // Sample data - replace with your API calls
  const [fires, setFires] = useState<FireData[]>([
    { id: '1', lat: 1.3521, lng: 103.8198, confidence: 'High' },
    { id: '2', lat: 1.2897, lng: 103.8501, confidence: 'High' },
    { id: '3', lat: 1.4382, lng: 103.7892, confidence: 'High' },
  ]);
  
  const [windData, setWindData] = useState<WindData>({
    speed: 5.2,
    direction: 135,
  });
  
  const [hazeLevel, setHazeLevel] = useState(78); // PSI or AQI value
  
  // Singapore center coordinates
  const center: [number, number] = [1.3521, 103.8198];
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!mounted) {
    return (
      <div className="w-full h-[600px] bg-gray-200 animate-pulse rounded-lg flex items-center justify-center">
        <p className="text-gray-500">Loading map...</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white p-4 rounded-lg shadow-sm border">
        <div className="flex flex-wrap gap-4 items-center">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showFiresState}
              onChange={(e) => setShowFiresState(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-black font-medium">Show Fires</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showWindState}
              onChange={(e) => setShowWindState(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-black font-medium">Show Wind</span>
          </label>


          <div className="ml-auto flex items-center gap-2">
            <span className="text-sm text-gray-600">Haze Level:</span>
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
      <div className="w-full h-[600px] rounded-lg overflow-hidden shadow-lg border">
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
          {showFiresState && fires.map((fire) => (
            <Marker
              key={fire.id}
              position={[fire.lat, fire.lng]}
              icon={fireIcon}
            >
              <Popup>
                <div className="min-w-[150px]">
                  <p className="font-semibold text-red-600 mb-2">🔥 Fire Detected</p>
                  <div className="space-y-1 text-sm">
                    <p>Confidence: <span className="font-medium">{fire.confidence}</span></p>
                    <p className="text-xs text-gray-500 mt-2">
                      Lat: {fire.lat.toFixed(4)}, Lng: {fire.lng.toFixed(4)}
                    </p>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
          
          {/* Wind arrow */}
          {showWindState && <WindArrow speed={windData.speed} direction={windData.direction} />}
        </MapContainer>
      </div>
      
      {/* Legend */}
      <div className="bg-white p-4 rounded-lg shadow-sm border">
        <h3 className="font-semibold mb-3">Legend</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-red-500 rounded-full"></div>
            <span>Fire Location</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-blue-500 rounded-full"></div>
            <span>Wind Direction</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-yellow-400 opacity-40 rounded-full"></div>
            <span>Haze Coverage</span>
          </div>
        </div>
      </div>
    </div>
  );
}