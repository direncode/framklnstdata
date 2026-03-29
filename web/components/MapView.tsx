"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface Venue {
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
  cuisine?: string;
  address?: string;
  category?: string;
  phone?: string;
  website?: string;
  opening_hours?: string;
  outdoor_seating?: string;
}

interface HeatmapPoint {
  lat: number;
  lon: number;
  weight: number;
}

function busynessColor(b: number | null): string {
  if (b == null || b <= 0) return "#4a9eff";
  if (b >= 80) return "#ff2244";
  if (b >= 60) return "#ff6600";
  if (b >= 40) return "#ffaa00";
  if (b >= 20) return "#00d4aa";
  return "#4a9eff";
}

function toGeoJSON(points: HeatmapPoint[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: points.map((p) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] },
      properties: { weight: p.weight },
    })),
  };
}

export default function MapView({
  venues,
  hour,
  onVenueClick,
  trafficHeatmap,
  searchHeatmap,
  showTraffic,
  showSearch,
}: {
  venues: Venue[];
  hour: number;
  onVenueClick?: (v: Venue) => void;
  trafficHeatmap?: HeatmapPoint[];
  searchHeatmap?: HeatmapPoint[];
  showTraffic: boolean;
  showSearch: boolean;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map once
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          "esri-satellite": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution:
              "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
          },
          "esri-labels": {
            type: "raster",
            tiles: [
              "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
          },
        },
        layers: [
          {
            id: "satellite",
            type: "raster",
            source: "esri-satellite",
            minzoom: 0,
            maxzoom: 19,
          },
          {
            id: "labels",
            type: "raster",
            source: "esri-labels",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [-79.055, 35.92],
      zoom: 14.5,
      pitch: 0,
      bearing: 0,
      maxZoom: 19,
      minZoom: 12,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 200, unit: "imperial" }),
      "bottom-left"
    );

    map.on("load", () => {
      // Traffic density heatmap source + layer (red-orange)
      map.addSource("traffic-heat", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "traffic-heatmap",
        type: "heatmap",
        source: "traffic-heat",
        paint: {
          "heatmap-weight": ["get", "weight"],
          "heatmap-intensity": 1.5,
          "heatmap-radius": 30,
          "heatmap-opacity": 0.6,
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(0,0,0,0)",
            0.2, "rgba(0,212,170,0.3)",
            0.4, "rgba(255,170,0,0.5)",
            0.6, "rgba(255,102,0,0.7)",
            0.8, "rgba(255,34,68,0.8)",
            1, "rgba(255,34,68,1)",
          ],
        },
        layout: { visibility: "none" },
      });

      // Search convergence heatmap source + layer (blue-purple)
      map.addSource("search-heat", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "search-heatmap",
        type: "heatmap",
        source: "search-heat",
        paint: {
          "heatmap-weight": ["get", "weight"],
          "heatmap-intensity": 1.5,
          "heatmap-radius": 35,
          "heatmap-opacity": 0.5,
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(0,0,0,0)",
            0.2, "rgba(74,158,255,0.2)",
            0.4, "rgba(100,80,255,0.4)",
            0.6, "rgba(150,50,255,0.6)",
            0.8, "rgba(200,50,255,0.8)",
            1, "rgba(255,50,255,1)",
          ],
        },
        layout: { visibility: "none" },
      });

      setMapReady(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update heatmap data
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const trafficSrc = map.getSource("traffic-heat") as maplibregl.GeoJSONSource | undefined;
    if (trafficSrc && trafficHeatmap) {
      trafficSrc.setData(toGeoJSON(trafficHeatmap));
    }

    const searchSrc = map.getSource("search-heat") as maplibregl.GeoJSONSource | undefined;
    if (searchSrc && searchHeatmap) {
      searchSrc.setData(toGeoJSON(searchHeatmap));
    }
  }, [trafficHeatmap, searchHeatmap, mapReady]);

  // Toggle heatmap visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    if (map.getLayer("traffic-heatmap")) {
      map.setLayoutProperty("traffic-heatmap", "visibility", showTraffic ? "visible" : "none");
    }
    if (map.getLayer("search-heatmap")) {
      map.setLayoutProperty("search-heatmap", "visibility", showSearch ? "visible" : "none");
    }
  }, [showTraffic, showSearch, mapReady]);

  // Update markers when venues or hour change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Add venue markers
    venues.forEach((v) => {
      const isClosed = (v as any).closed === true;
      const color = isClosed ? "#333840" : busynessColor(v.busyness);
      const size = isClosed ? 6 : (v.busyness != null && v.busyness > 0 ? 14 + (v.busyness / 100) * 16 : 10);

      // Create marker element — anchor wrapper ensures scale from center
      const wrapper = document.createElement("div");
      wrapper.style.width = `${size}px`;
      wrapper.style.height = `${size}px`;
      wrapper.style.position = "relative";

      const el = document.createElement("div");
      el.style.width = "100%";
      el.style.height = "100%";
      el.style.borderRadius = "50%";
      el.style.border = `2px solid ${color}`;
      el.style.backgroundColor = color + "44";
      el.style.cursor = "pointer";
      el.style.transition = "transform 0.2s ease, box-shadow 0.2s ease";
      el.style.transformOrigin = "center center";
      wrapper.appendChild(el);

      // Glow effect for busy venues
      if (v.busyness != null && v.busyness > 40) {
        el.style.boxShadow = `0 0 ${v.busyness / 4}px ${color}88, 0 0 ${v.busyness / 2}px ${color}33`;
      }

      wrapper.addEventListener("mouseenter", () => {
        el.style.transform = "scale(1.3)";
        wrapper.style.zIndex = "10";

        const busynessText =
          isClosed ? "CLOSED" :
          v.busyness != null && v.busyness > 0 ? `${v.busyness}% busy` : "no traffic data";
        const cuisine = v.cuisine ? `<div style="color: #6b7080;">${v.cuisine}</div>` : "";
        const address = v.address ? `<div style="color: #454a58; margin-top: 2px;">${v.address}</div>` : "";
        const category = v.category ? `<div style="color: #454a58; text-transform: uppercase; font-size: 9px; letter-spacing: 0.5px; margin-top: 3px;">${v.category}</div>` : "";

        popupRef.current = new maplibregl.Popup({
          offset: size / 2 + 6,
          closeButton: false,
          className: "venue-popup",
        })
          .setLngLat([v.lon, v.lat])
          .setHTML(
            `<div style="font-family: monospace; font-size: 11px; padding: 4px; max-width: 220px;">
              <div style="color: ${color}; font-weight: bold;">${v.name}</div>
              <div style="color: ${isClosed ? '#ff4d6a' : '#6b7080'}; margin-top: 2px;">${busynessText}</div>
              <div style="color: #6b7080;">${v.amenity_type}</div>
              ${cuisine}${address}${category}
            </div>`
          )
          .addTo(map);
      });

      wrapper.addEventListener("mouseleave", () => {
        el.style.transform = "scale(1)";
        wrapper.style.zIndex = "";
        popupRef.current?.remove();
      });

      wrapper.addEventListener("click", () => {
        onVenueClick?.(v);
      });

      const marker = new maplibregl.Marker({ element: wrapper, anchor: "center" })
        .setLngLat([v.lon, v.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [venues, hour, onVenueClick]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Overlay label */}
      <div className="absolute top-3 left-3 bg-[#0a0b0fcc] px-3 py-1.5 rounded text-[10px] font-mono text-[#00d4aa] tracking-wider uppercase pointer-events-none">
        Live Foot Traffic — {hour}:00
        {showTraffic && <span className="ml-2 text-[#ff6600]">HEAT</span>}
        {showSearch && <span className="ml-2 text-[#a050ff]">SEARCH</span>}
      </div>

      {/* Legend */}
      <div className="absolute bottom-8 right-3 bg-[#0a0b0fcc] px-3 py-2 rounded pointer-events-none">
        <div className="flex flex-col gap-1 text-[9px] font-mono text-[#6b7080]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#ff2244]" /> 80%+
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#ff6600]" /> 60%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#ffaa00]" /> 40%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00d4aa]" /> 20%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#4a9eff]" /> no data
          </span>
          {showTraffic && (
            <span className="flex items-center gap-1.5 mt-1 border-t border-[#1e2028] pt-1">
              <span className="w-2 h-2 rounded-full bg-[#ff6600]" /> traffic heat
            </span>
          )}
          {showSearch && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#a050ff]" /> search conv.
            </span>
          )}
        </div>
      </div>

      {/* Popup styles */}
      <style jsx global>{`
        .venue-popup .maplibregl-popup-content {
          background: #111318ee;
          border: 1px solid #2a2d38;
          border-radius: 8px;
          padding: 8px 12px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }
        .venue-popup .maplibregl-popup-tip {
          border-top-color: #111318ee;
        }
      `}</style>
    </div>
  );
}
