/**
 * Franklin Street Data API client.
 * Talks to the Python datastream.py backend or Next.js API routes.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/data";

export interface Venue {
  id: number;
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
  composite_score: number;
  hourly_profile: number[] | null;
  osm_id?: number;
  cuisine?: string;
  opening_hours?: string;
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  weight: number;
}

export interface TrendSuggestion {
  category: string;
  keyword: string;
  score: number;
  strength: string;
  marker: string;
  suggestion: string;
  related_rising: string[];
}

export interface FeedPost {
  source: string;
  title: string;
  score?: number;
  comments?: number;
  created?: string;
  url?: string;
  flair?: string;
  summary?: string;
  published?: string;
}

export interface LiveFeed {
  reddit: FeedPost[] | null;
  dth: FeedPost[] | null;
  trends: {
    nationally_trending: string[];
    locally_relevant: string[];
    core_keyword_interest: Record<string, number>;
  } | null;
  unc_events: Array<{
    source: string;
    title: string;
    location: string;
    date: string;
    url: string;
    type: string[];
  }> | null;
  extracted_keywords: Array<{ keyword: string; frequency: number }>;
  trivia_suggestions: Array<{
    source: string;
    topic: string;
    signal: string;
    suggestion: string;
  }>;
}

export interface SystemStatus {
  status: string;
  version: string;
  data_feeds: Record<string, string>;
  surveillance_area: {
    center: [number, number];
    radius_meters: number;
    venue_source: string;
  };
}

async function fetchJSON<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export const api = {
  status: () => fetchJSON<SystemStatus>("/status"),
  venues: (hour?: number) =>
    fetchJSON<Venue[]>(`/venues${hour !== undefined ? `?hour=${hour}` : ""}`),
  heatmap: (hour?: number) =>
    fetchJSON<HeatmapPoint[]>(`/heatmap${hour !== undefined ? `?hour=${hour}` : ""}`),
  livefeed: () => fetchJSON<LiveFeed>("/livefeed"),
  trends: () => fetchJSON<{ suggestions: TrendSuggestion[]; trending_now: string[] }>("/trends"),
  forecast: () => fetchJSON<{ live_forecast: { signals: Record<string, unknown>; signal_count: number; recommendation: string[] } }>("/forecast"),
  weather: () => fetchJSON<{ temp_f: number; description: string; is_good_flyering_weather: boolean } | null>("/weather"),
};
