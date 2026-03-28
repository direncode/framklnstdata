import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy API route: forwards requests to the Python datastream.py backend.
 *
 * In production, set PANOPTICON_BACKEND_URL to point to the Python server.
 * For Vercel deployment, the Python backend runs separately (e.g., Railway, Render).
 *
 * If no backend is configured, returns empty/null responses so the
 * frontend renders gracefully with "no data" states.
 */

const BACKEND = process.env.PANOPTICON_BACKEND_URL || "";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = "/" + path.join("/");
  const search = request.nextUrl.searchParams.toString();
  const url = `${BACKEND}${apiPath}${search ? `?${search}` : ""}`;

  // If no backend configured, return structured empty responses
  if (!BACKEND) {
    return NextResponse.json(
      emptyResponse(apiPath),
      { headers: { "Access-Control-Allow-Origin": "*" } }
    );
  }

  try {
    const res = await fetch(url, {
      headers: { "Accept": "application/json" },
      next: { revalidate: 30 },
    });
    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Access-Control-Allow-Origin": "*" },
    });
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable", path: apiPath },
      { status: 502, headers: { "Access-Control-Allow-Origin": "*" } }
    );
  }
}

function emptyResponse(path: string): Record<string, unknown> {
  switch (path) {
    case "/status":
      return {
        status: "no_backend",
        version: "3.0.0",
        data_feeds: {},
        surveillance_area: {
          center: [35.9132, -79.0555],
          radius_meters: 500,
          venue_source: "not_connected",
        },
      };
    case "/venues":
      return { data: [] };
    case "/heatmap":
      return { data: [] };
    case "/livefeed":
      return {
        reddit: null,
        dth: null,
        trends: null,
        unc_events: null,
        extracted_keywords: [],
        trivia_suggestions: [],
      };
    case "/trends":
      return { suggestions: [], trending_now: [] };
    case "/forecast":
      return { live_forecast: { signals: {}, signal_count: 0, recommendation: [] } };
    case "/weather":
      return { unavailable: true };
    default:
      return { error: "Set PANOPTICON_BACKEND_URL to connect to Python backend" };
  }
}
