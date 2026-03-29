import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy API route: forwards requests to the Python datastream.py backend.
 *
 * BACKEND_URL must point to the Fly.io backend (or localhost for dev).
 * Uses a 25s timeout to handle slow first-load (Overpass + MFG solve).
 */

const BACKEND = process.env.BACKEND_URL || "";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = "/" + path.join("/");
  const search = request.nextUrl.searchParams.toString();
  const url = `${BACKEND}${apiPath}${search ? `?${search}` : ""}`;

  if (!BACKEND) {
    return NextResponse.json(
      emptyResponse(apiPath),
      { headers: cors() }
    );
  }

  // Try with 25s timeout, retry once on failure
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(25000),
        cache: "no-store",
      });
      if (!res.ok && attempt === 0) continue;
      const data = await res.json();
      return NextResponse.json(data, { headers: cors() });
    } catch {
      if (attempt === 0) continue;
    }
  }

  return NextResponse.json(
    { error: "Backend unavailable", path: apiPath, backend: BACKEND ? "configured" : "not_set" },
    { status: 502, headers: cors() }
  );
}

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-cache, no-store, must-revalidate",
  };
}

function emptyResponse(path: string): Record<string, unknown> {
  switch (path) {
    case "/status":
      return {
        status: "no_backend",
        version: "4.0.0",
        data_feeds: {},
        surveillance_area: {
          center: [35.9132, -79.0555],
          radius_meters: 500,
          venue_source: "not_connected",
        },
      };
    case "/venues":
    case "/spots":
      return { spots: [], venues: [] };
    case "/heatmap":
      return { heatmap: [] };
    case "/convergence":
      return { venue_scores: {}, heatmap: [], top_searches: [] };
    case "/livefeed":
      return {
        reddit: null, dth: null, trends: null, unc_events: null,
        extracted_keywords: [], trivia_suggestions: [],
      };
    case "/trends":
      return { suggestions: [], trending_now: [] };
    case "/forecast":
      return { live_forecast: { signals: {}, signal_count: 0, recommendation: [] } };
    default:
      return { error: "Set BACKEND_URL to connect to Python backend" };
  }
}
