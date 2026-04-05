"use client";

import { useEffect, useRef, useState } from "react";

/**
 * CesiumJS 3D Globe View
 *
 * Full 3D globe with satellite imagery, terrain, real satellite orbits,
 * aircraft tracking, camera networks, and GIBS overlays.
 * Uses CesiumJS loaded dynamically (client-side only).
 */

// Cesium type stubs for dynamic import
type CesiumViewer = any;
type CesiumModule = any;

interface GlobeViewProps {
  cameras?: Array<{ id: string | number; lat: number; lon: number; type: string; operator: string }>;
  aircraft?: Array<{
    icao24: string; callsign: string; lat: number; lon: number;
    altitude_m: number; heading: number; origin_country: string;
  }>;
  satellites?: Array<{
    name: string; norad_id: number; lat: number; lon: number; alt_km: number;
  }>;
  satelliteTracks?: Array<{ lat: number; lon: number; alt_km: number }>;
  displayMode?: "normal" | "night_vision" | "flir" | "crt";
  gibsLayer?: string | null;
  onLocationSelect?: (lat: number, lon: number) => void;
}

export default function GlobeView({
  cameras = [],
  aircraft = [],
  satellites = [],
  satelliteTracks = [],
  displayMode = "normal",
  gibsLayer = null,
  onLocationSelect,
}: GlobeViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<CesiumViewer>(null);
  const cesiumRef = useRef<CesiumModule>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dynamic import and initialization of CesiumJS
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    let cancelled = false;

    async function initCesium() {
      try {
        // Dynamic import to avoid SSR issues
        const Cesium = await import("cesium");
        if (cancelled) return;

        cesiumRef.current = Cesium;

        // Configure Cesium
        (window as any).CESIUM_BASE_URL = "/cesium";

        // Use Ion default access token (free tier) or none for basic imagery
        Cesium.Ion.defaultAccessToken = "";

        const viewer = new Cesium.Viewer(containerRef.current!, {
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: true,
          navigationHelpButton: false,
          animation: false,
          timeline: false,
          fullscreenButton: false,
          vrButton: false,
          infoBox: false,
          selectionIndicator: false,
          baseLayer: false,
          terrain: undefined,
          requestRenderMode: true,
          maximumRenderTimeChange: Infinity,
        });

        // Add ESRI satellite imagery as base layer (same as MapView)
        viewer.imageryLayers.addImageryProvider(
          new Cesium.UrlTemplateImageryProvider({
            url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            maximumLevel: 19,
            credit: "Esri World Imagery",
          })
        );

        // Add ESRI labels overlay
        viewer.imageryLayers.addImageryProvider(
          new Cesium.UrlTemplateImageryProvider({
            url: "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            maximumLevel: 19,
          })
        );

        // Style the globe
        viewer.scene.globe.enableLighting = true;
        viewer.scene.fog.enabled = true;
        viewer.scene.globe.showGroundAtmosphere = true;
        if (viewer.scene.skyAtmosphere) viewer.scene.skyAtmosphere.show = true;

        // Dark space background
        viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#0a0b0f");

        // Set initial view to Franklin Street area
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(-79.0555, 35.9132, 50000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0,
          },
          duration: 0,
        });

        // Click handler for location selection
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((movement: any) => {
          const cartesian = viewer.camera.pickEllipsoid(
            movement.position,
            viewer.scene.globe.ellipsoid
          );
          if (cartesian) {
            const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
            const lat = Cesium.Math.toDegrees(cartographic.latitude);
            const lon = Cesium.Math.toDegrees(cartographic.longitude);
            onLocationSelect?.(lat, lon);
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

        viewerRef.current = viewer;
        setLoading(false);
      } catch (err: any) {
        console.error("CesiumJS init error:", err);
        setError(err.message || "Failed to load 3D globe");
        setLoading(false);
      }
    }

    initCesium();

    return () => {
      cancelled = true;
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, [onLocationSelect]);

  // Update camera entities
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium || cameras.length === 0) return;

    // Remove old camera entities
    const existing = viewer.entities.values.filter((e: any) => e.id?.startsWith("cam-"));
    existing.forEach((e: any) => viewer.entities.remove(e));

    cameras.forEach((cam) => {
      if (!cam.lat || !cam.lon) return;
      viewer.entities.add({
        id: `cam-${cam.id}`,
        position: Cesium.Cartesian3.fromDegrees(cam.lon, cam.lat, 5),
        point: {
          pixelSize: 6,
          color: cam.type === "ALPR"
            ? Cesium.Color.fromCssColorString("#ff4d6a")
            : cam.type === "traffic"
            ? Cesium.Color.fromCssColorString("#ffaa00")
            : Cesium.Color.fromCssColorString("#00d4aa"),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 1,
        },
        label: {
          text: cam.operator || cam.type,
          font: "10px monospace",
          fillColor: Cesium.Color.fromCssColorString("#6b7080"),
          style: Cesium.LabelStyle.FILL,
          pixelOffset: new Cesium.Cartesian2(0, -12),
          scaleByDistance: new Cesium.NearFarScalar(500, 1, 50000, 0),
        },
      });
    });

    viewer.scene.requestRender();
  }, [cameras]);

  // Update aircraft entities
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium) return;

    // Remove old aircraft entities
    const existing = viewer.entities.values.filter((e: any) => e.id?.startsWith("ac-"));
    existing.forEach((e: any) => viewer.entities.remove(e));

    aircraft.forEach((ac) => {
      if (!ac.lat || !ac.lon) return;
      const alt = ac.altitude_m || 10000;
      viewer.entities.add({
        id: `ac-${ac.icao24}`,
        position: Cesium.Cartesian3.fromDegrees(ac.lon, ac.lat, alt),
        point: {
          pixelSize: 8,
          color: Cesium.Color.fromCssColorString("#4a9eff"),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 1,
        },
        label: {
          text: ac.callsign || ac.icao24,
          font: "10px monospace",
          fillColor: Cesium.Color.fromCssColorString("#4a9eff"),
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          outlineColor: Cesium.Color.BLACK,
          pixelOffset: new Cesium.Cartesian2(12, 0),
          scaleByDistance: new Cesium.NearFarScalar(1000, 1, 500000, 0.3),
        },
      });
    });

    viewer.scene.requestRender();
  }, [aircraft]);

  // Update satellite entities + ground tracks
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium) return;

    // Remove old satellite entities
    const existing = viewer.entities.values.filter((e: any) => e.id?.startsWith("sat-"));
    existing.forEach((e: any) => viewer.entities.remove(e));

    satellites.forEach((sat) => {
      if (!sat.lat || !sat.lon) return;
      const altMeters = (sat.alt_km || 400) * 1000;
      viewer.entities.add({
        id: `sat-${sat.norad_id}`,
        position: Cesium.Cartesian3.fromDegrees(sat.lon, sat.lat, altMeters),
        point: {
          pixelSize: 5,
          color: Cesium.Color.fromCssColorString("#ff6600"),
          outlineColor: Cesium.Color.fromCssColorString("#ff660088"),
          outlineWidth: 3,
        },
        label: {
          text: sat.name,
          font: "9px monospace",
          fillColor: Cesium.Color.fromCssColorString("#ff6600"),
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          outlineColor: Cesium.Color.BLACK,
          pixelOffset: new Cesium.Cartesian2(10, -5),
          scaleByDistance: new Cesium.NearFarScalar(100000, 1, 5000000, 0.2),
        },
      });
    });

    // Ground track polyline
    if (satelliteTracks.length > 1) {
      const existing_track = viewer.entities.values.filter((e: any) => e.id === "sat-track");
      existing_track.forEach((e: any) => viewer.entities.remove(e));

      const positions = satelliteTracks.map((p) =>
        Cesium.Cartesian3.fromDegrees(p.lon, p.lat, (p.alt_km || 400) * 1000)
      );

      viewer.entities.add({
        id: "sat-track",
        polyline: {
          positions,
          width: 2,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.3,
            color: Cesium.Color.fromCssColorString("#ff660088"),
          }),
        },
      });
    }

    viewer.scene.requestRender();
  }, [satellites, satelliteTracks]);

  // GIBS overlay layer
  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium) return;

    // Remove previous GIBS layer (index > 1 means after base + labels)
    while (viewer.imageryLayers.length > 2) {
      viewer.imageryLayers.remove(viewer.imageryLayers.get(2));
    }

    if (gibsLayer) {
      const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];
      viewer.imageryLayers.addImageryProvider(
        new Cesium.UrlTemplateImageryProvider({
          url: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${gibsLayer}/default/${yesterday}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`,
          maximumLevel: 9,
          credit: "NASA GIBS",
        })
      );
    }

    viewer.scene.requestRender();
  }, [gibsLayer]);

  // Display mode CSS filter
  const filterStyle = (() => {
    switch (displayMode) {
      case "night_vision":
        return "hue-rotate(90deg) saturate(3) brightness(1.5) contrast(1.2)";
      case "flir":
        return "hue-rotate(180deg) saturate(0.3) brightness(1.2) contrast(2)";
      case "crt":
        return "sepia(0.3) contrast(1.4) brightness(0.9)";
      default:
        return "none";
    }
  })();

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full"
        style={{ filter: filterStyle }}
      />

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-[#0a0b0f] flex items-center justify-center z-10">
          <div className="text-center">
            <div className="text-lg font-mono text-[#00d4aa] animate-pulse mb-2">
              INITIALIZING 3D GLOBE
            </div>
            <div className="text-xs font-mono text-[#454a58]">
              Loading CesiumJS + Satellite Imagery...
            </div>
          </div>
        </div>
      )}

      {/* Error fallback */}
      {error && (
        <div className="absolute inset-0 bg-[#0a0b0f] flex items-center justify-center z-10">
          <div className="text-center max-w-md">
            <div className="text-sm font-mono text-[#ff4d6a] mb-2">
              3D GLOBE UNAVAILABLE
            </div>
            <div className="text-xs font-mono text-[#454a58]">{error}</div>
            <div className="text-xs font-mono text-[#6b7080] mt-2">
              Falling back to 2D map view
            </div>
          </div>
        </div>
      )}

      {/* Globe HUD overlay */}
      <div className="absolute top-3 left-3 bg-[#0a0b0fcc] px-3 py-1.5 rounded text-[10px] font-mono text-[#00d4aa] tracking-wider uppercase pointer-events-none z-20">
        3D Globe — CesiumJS
        {cameras.length > 0 && <span className="ml-2 text-[#ff4d6a]">{cameras.length} CAM</span>}
        {aircraft.length > 0 && <span className="ml-2 text-[#4a9eff]">{aircraft.length} AC</span>}
        {satellites.length > 0 && <span className="ml-2 text-[#ff6600]">{satellites.length} SAT</span>}
      </div>

      {/* Display mode indicator */}
      {displayMode !== "normal" && (
        <div className="absolute top-3 right-3 bg-[#0a0b0fcc] px-3 py-1.5 rounded text-[10px] font-mono tracking-wider uppercase pointer-events-none z-20"
          style={{
            color: displayMode === "night_vision" ? "#00ff41" :
                   displayMode === "flir" ? "#ff6600" : "#00d4aa",
            textShadow: displayMode === "night_vision" ? "0 0 8px #00ff41" :
                        displayMode === "flir" ? "0 0 8px #ff6600" : "none",
          }}
        >
          {displayMode.replace("_", " ")} MODE
        </div>
      )}

      {/* CRT scanline overlay */}
      {displayMode === "crt" && (
        <div
          className="absolute inset-0 pointer-events-none z-30"
          style={{
            background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.15) 0px, rgba(0,0,0,0.15) 1px, transparent 1px, transparent 3px)",
            mixBlendMode: "multiply",
          }}
        />
      )}

      {/* Cesium widget styles override */}
      <style jsx global>{`
        .cesium-viewer .cesium-widget-credits { display: none !important; }
        .cesium-viewer .cesium-viewer-toolbar { top: auto !important; bottom: 40px !important; right: 8px !important; }
        .cesium-viewer .cesium-sceneModePicker-wrapper {
          background: #111318 !important;
          border: 1px solid #1e2028 !important;
          border-radius: 6px !important;
        }
        .cesium-viewer .cesium-sceneModePicker-wrapper button {
          background: transparent !important;
        }
        .cesium-viewer .cesium-sceneModePicker-wrapper .cesium-sceneModePicker-dropDown-icon {
          filter: brightness(0.6) !important;
        }
      `}</style>
    </div>
  );
}
