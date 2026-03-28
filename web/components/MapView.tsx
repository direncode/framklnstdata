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
}

function busynessColor(b: number | null): string {
  if (b == null || b <= 0) return "#4a9eff";
  if (b >= 80) return "#ff2244";
  if (b >= 60) return "#ff6600";
  if (b >= 40) return "#ffaa00";
  if (b >= 20) return "#00d4aa";
  return "#4a9eff";
}

export default function MapView({
  venues,
  hour,
  onVenueClick,
}: {
  venues: Venue[];
  hour: number;
  onVenueClick?: (v: Venue) => void;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const popupRef = useRef<maplibregl.Popup | null>(null);

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
      center: [-79.0555, 35.9132],
      zoom: 16.5,
      pitch: 0,
      bearing: 0,
      maxZoom: 19,
      minZoom: 14,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 200, unit: "imperial" }),
      "bottom-left"
    );

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update markers when venues or hour change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Add venue markers
    venues.forEach((v) => {
      const color = busynessColor(v.busyness);
      const size = v.busyness != null && v.busyness > 0 ? 14 + (v.busyness / 100) * 16 : 10;

      // Create marker element
      const el = document.createElement("div");
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.style.borderRadius = "50%";
      el.style.border = `2px solid ${color}`;
      el.style.backgroundColor = color + "44";
      el.style.cursor = "pointer";
      el.style.transition = "all 0.3s";

      // Glow effect for busy venues
      if (v.busyness != null && v.busyness > 40) {
        el.style.boxShadow = `0 0 ${v.busyness / 4}px ${color}88, 0 0 ${v.busyness / 2}px ${color}33`;
      }

      el.addEventListener("mouseenter", () => {
        el.style.transform = "scale(1.3)";
        el.style.zIndex = "10";

        // Show popup
        const busynessText =
          v.busyness != null && v.busyness > 0 ? `${v.busyness}% busy` : "no traffic data";

        popupRef.current = new maplibregl.Popup({
          offset: size / 2 + 4,
          closeButton: false,
          className: "venue-popup",
        })
          .setLngLat([v.lon, v.lat])
          .setHTML(
            `<div style="font-family: monospace; font-size: 11px; padding: 4px;">
              <div style="color: ${color}; font-weight: bold;">${v.name}</div>
              <div style="color: #6b7080; margin-top: 2px;">${busynessText}</div>
              <div style="color: #454a58;">${v.amenity_type}</div>
            </div>`
          )
          .addTo(map);
      });

      el.addEventListener("mouseleave", () => {
        el.style.transform = "scale(1)";
        el.style.zIndex = "";
        popupRef.current?.remove();
      });

      el.addEventListener("click", () => {
        onVenueClick?.(v);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([v.lon, v.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [venues, hour, onVenueClick]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Overlay labels */}
      <div className="absolute top-3 left-3 bg-[#0a0b0fcc] px-3 py-1.5 rounded text-[10px] font-mono text-[#00d4aa] tracking-wider uppercase pointer-events-none">
        Live Foot Traffic — {hour}:00
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
