"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Palantir-Grade Intelligence Dashboard
==============================================

Run with:  streamlit run app.py

Multi-layer geospatial intelligence platform:
  - Satellite / aerial imagery with Esri World Imagery
  - Convergent foot traffic heat maps
  - 3D venue busyness columns (pydeck)
  - Street network overlay with centrality analysis
  - OSINT intelligence: demographics, weather, events, social
  - Click-to-inspect on everything
  - Full downloadable surveillance reports
"""

import copy
import json
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Franklin Street Panopticon v3",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS injection for Palantir aesthetic
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2e;
        border-radius: 4px 4px 0 0;
        padding: 8px 16px;
        color: #00ff88;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262d3d;
    }
    div[data-testid="stMetric"] {
        background-color: #1a1f2e;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #2a3040;
    }
    .stExpander {
        border: 1px solid #2a3040;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

from config import GOOGLE_PLACES_API_KEY, FRANKLIN_STREET_CENTER
from spots import get_enriched_spots, get_ranked_spots, FRANKLIN_STREET_SPOTS
from traffic import (
    build_heatmap_data,
    fetch_nearby_places,
    get_ncdot_traffic,
    aggregate_busyness,
)
from trends import build_trends_report, generate_trivia_suggestions
from satellite import TILE_SOURCES, PYDECK_VIEWS, get_folium_tile_layers
from intel import build_intel_report, get_demographics, fetch_weather, get_event_context
from network import (
    fetch_street_network,
    find_intersections,
    compute_walk_scores,
    get_network_lines,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div style='text-align: center; padding: 10px 0;'>
    <h1 style='color: #00ff88; margin-bottom: 0;'>
        📡 FRANKLIN STREET PANOPTICON v3
    </h1>
    <p style='color: #4a9eff; font-size: 14px; letter-spacing: 3px;'>
        SURVEILLANCE-GRADE INTELLIGENCE PLATFORM
    </p>
    <p style='color: #666; font-size: 12px;'>
        Trivia Night Optimization · Bandidos · UNC Chapel Hill
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Sidebar - Command Center Controls
# ---------------------------------------------------------------------------

st.sidebar.markdown("## 🎛️ COMMAND CENTER")

time_of_day = st.sidebar.selectbox(
    "⏰ Time Optimization", ["evening", "daytime", "morning"], index=0,
)

num_spots = st.sidebar.slider("📍 Surveillance Points", 3, 10, 8)

day_names = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]
current_dow = datetime.now().weekday()
selected_day = st.sidebar.selectbox(
    "📅 Day of Week", day_names, index=current_dow,
)
selected_dow = day_names.index(selected_day)

current_hour = datetime.now().hour
selected_hour = st.sidebar.slider(
    "🕐 Analysis Hour", 0, 23, current_hour,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ DATA FEEDS")

use_live_trends = st.sidebar.checkbox("Google Trends (Live)", value=False)

map_style = st.sidebar.selectbox(
    "Map Layer",
    ["Esri Satellite", "CartoDB Dark", "OpenStreetMap",
     "Esri Topo", "CartoDB Light"],
    index=0,
)

show_network = st.sidebar.checkbox("Street Network Overlay", value=True)
show_intersections = st.sidebar.checkbox("Intersection Nodes", value=True)

# API Status Panel
with st.sidebar.expander("📊 SYSTEM STATUS"):
    st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
    if GOOGLE_PLACES_API_KEY:
        st.markdown("🟢 Google Places: ACTIVE")
    else:
        st.markdown("🟡 Google Places: FALLBACK")
    st.markdown("🟢 OpenStreetMap: ACTIVE")
    st.markdown("🟢 NCDOT AADT: ACTIVE")
    st.markdown("🟢 Census Data: ACTIVE")
    weather = fetch_weather()
    st.markdown(
        f"🌤️ Weather: {weather['temp_f']}°F, {weather['description']}"
    )
    event = get_event_context()
    st.markdown(f"📅 Event: {event['event_type'].replace('_', ' ').title()}")

# ---------------------------------------------------------------------------
# Data Loading (Cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_spots(tod, hr, n):
    return get_enriched_spots(time_of_day=tod, hour=hr, top_n=n)

@st.cache_data(ttl=3600)
def load_all_spots(hr):
    spots = copy.deepcopy(FRANKLIN_STREET_SPOTS)
    return aggregate_busyness(spots, hour=hr)

@st.cache_data(ttl=3600)
def load_heatmap(hr, dow):
    spots = get_enriched_spots(hour=hr, top_n=10)
    return build_heatmap_data(spots, hour=hr, day_of_week=dow)

@st.cache_data(ttl=3600)
def load_osm():
    return fetch_nearby_places()

@st.cache_data(ttl=1800)
def load_trends():
    return build_trends_report()

@st.cache_data(ttl=7200)
def load_network():
    return fetch_street_network()

@st.cache_data(ttl=7200)
def load_intersections():
    return find_intersections()

@st.cache_data(ttl=7200)
def load_network_lines():
    return get_network_lines()

spots = load_spots(time_of_day, selected_hour, num_spots)

# ---------------------------------------------------------------------------
# Tab Layout
# ---------------------------------------------------------------------------

tab_sat, tab_heat, tab_traffic, tab_network, tab_intel, tab_trends, tab_report = st.tabs([
    "🛰️ SATELLITE", "🔥 HEAT MAP", "📊 TRAFFIC",
    "🕸️ NETWORK", "🕵️ INTEL", "📈 TRENDS", "📄 REPORT",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: SATELLITE VIEW
# ═══════════════════════════════════════════════════════════════
with tab_sat:
    st.subheader("🛰️ Satellite Reconnaissance")
    st.caption(
        "Click any marker for full intelligence briefing. "
        "Toggle layers with the control in the top-right."
    )

    try:
        import folium
        from folium.plugins import (
            HeatMap, MeasureControl, MiniMap, Fullscreen, MarkerCluster,
        )
        from streamlit_folium import st_folium

        tile_info = TILE_SOURCES.get(map_style, TILE_SOURCES["Esri Satellite"])

        m = folium.Map(
            location=list(FRANKLIN_STREET_CENTER),
            zoom_start=17,
            tiles=tile_info["url"],
            attr=tile_info["attr"],
        )

        # Add alternative tile layers
        for name, url, attr in get_folium_tile_layers():
            if name != tile_info["name"]:
                folium.TileLayer(
                    tiles=url, attr=attr, name=name, overlay=False,
                ).add_to(m)

        # Add satellite labels overlay
        labels = TILE_SOURCES.get("Esri Satellite Labels")
        if labels and map_style == "Esri Satellite":
            folium.TileLayer(
                tiles=labels["url"],
                attr=labels["attr"],
                name="Labels",
                overlay=True,
            ).add_to(m)

        # Add venue markers with full intelligence popups
        for i, spot in enumerate(spots, 1):
            busyness = spot.get("live_busyness", 0)
            walk = spot.get("walk_score", "N/A")

            if busyness >= 70:
                color = "red"
                icon_color = "darkred"
            elif busyness >= 40:
                color = "orange"
                icon_color = "orange"
            else:
                color = "blue"
                icon_color = "darkblue"

            popup_html = f"""
            <div style='width:320px; font-family: monospace; font-size: 11px;'>
                <h3 style='color: #1a73e8; margin:0;'>#{i} {spot['name']}</h3>
                <hr style='margin:4px 0;'>
                <table style='width:100%;'>
                    <tr><td><b>Score</b></td><td>{spot['composite_score']}/10</td></tr>
                    <tr><td><b>Busyness</b></td><td>{busyness}%</td></tr>
                    <tr><td><b>Foot Traffic</b></td><td>{spot['foot_traffic']}/10</td></tr>
                    <tr><td><b>Dwell Time</b></td><td>{spot['dwell_time']}/10</td></tr>
                    <tr><td><b>Visibility</b></td><td>{spot['visibility']}/10</td></tr>
                    <tr><td><b>Student %</b></td><td>{spot['student_density']}/10</td></tr>
                    <tr><td><b>Type</b></td><td>{spot.get('place_type', 'N/A')}</td></tr>
                    <tr><td><b>Best Times</b></td>
                        <td>{', '.join(spot['best_times'])}</td></tr>
                    <tr><td><b>Coords</b></td>
                        <td>{spot['lat']:.4f}, {spot['lon']:.4f}</td></tr>
                </table>
                <hr style='margin:4px 0;'>
                <b>INTEL:</b> {spot['rationale'][:200]}
                <hr style='margin:4px 0;'>
                <b>ACTION:</b> {spot['placement_tip'][:200]}
            </div>
            """

            folium.Marker(
                location=[spot["lat"], spot["lon"]],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"#{i} {spot['name']} | {busyness}% busy | Score {spot['composite_score']}",
                icon=folium.Icon(
                    color=color, icon_color="white",
                    icon="crosshairs", prefix="fa",
                ),
            ).add_to(m)

        # Add OSM discovered venues as cluster
        try:
            osm_places = load_osm()
            if osm_places:
                cluster = MarkerCluster(name="Discovered Venues").add_to(m)
                for place in osm_places:
                    folium.CircleMarker(
                        location=[place["lat"], place["lon"]],
                        radius=4,
                        popup=(
                            f"<b>{place['name']}</b><br>"
                            f"Type: {place['amenity_type']}<br>"
                            f"Coords: {place['lat']:.5f}, {place['lon']:.5f}"
                        ),
                        tooltip=f"{place['name']} ({place['amenity_type']})",
                        color="#00ff88",
                        fill=True,
                        fill_opacity=0.6,
                    ).add_to(cluster)
        except Exception:
            pass

        # Add intersection markers
        if show_intersections:
            try:
                intersections = load_intersections()
                ix_group = folium.FeatureGroup(name="Intersections")
                for ix in intersections[:15]:
                    folium.CircleMarker(
                        location=[ix["lat"], ix["lon"]],
                        radius=6,
                        popup=(
                            f"<b>Intersection</b><br>"
                            f"Degree: {ix['degree']}<br>"
                            f"Connectivity: {ix.get('connectivity_score', 'N/A')}/10<br>"
                            f"Name: {ix.get('name', 'unnamed')}"
                        ),
                        tooltip=f"Intersection (degree {ix['degree']})",
                        color="#ffff00",
                        fill=True,
                        fill_color="#ffff00",
                        fill_opacity=0.5,
                    ).add_to(ix_group)
                ix_group.add_to(m)
            except Exception:
                pass

        # Controls
        Fullscreen().add_to(m)
        MeasureControl(primary_length_unit="meters").add_to(m)
        MiniMap(toggle_display=True).add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)

        st_folium(m, width=1000, height=600, key="satellite_map")

        # Legend
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown("🔴 High busyness (70%+)")
        c2.markdown("🟠 Medium (40-70%)")
        c3.markdown("🔵 Low (<40%)")
        c4.markdown("🟡 Intersections")

    except ImportError as e:
        st.error(f"Map libraries not available: {e}")
        st.info("Install: `pip install folium streamlit-folium`")
        for i, spot in enumerate(spots, 1):
            st.markdown(
                f"**#{i} {spot['name']}** — Score: {spot['composite_score']}/10 "
                f"— ({spot['lat']}, {spot['lon']})"
            )

# ═══════════════════════════════════════════════════════════════
# TAB 2: HEAT MAP
# ═══════════════════════════════════════════════════════════════
with tab_heat:
    st.subheader(f"🔥 Convergent Heat Map — {selected_day} {selected_hour}:00")

    try:
        import folium
        from folium.plugins import HeatMap
        from streamlit_folium import st_folium

        m2 = folium.Map(
            location=list(FRANKLIN_STREET_CENTER),
            zoom_start=16,
            tiles="CartoDB dark_matter",
        )

        heatmap_data = load_heatmap(selected_hour, selected_dow)
        if heatmap_data:
            HeatMap(
                heatmap_data,
                min_opacity=0.4,
                max_val=1.0,
                radius=28,
                blur=22,
                gradient={
                    "0.1": "#000066",
                    "0.3": "#0066ff",
                    "0.5": "#00ff88",
                    "0.7": "#ffcc00",
                    "0.85": "#ff6600",
                    "1.0": "#ff0000",
                },
            ).add_to(m2)

        # Venue dots on top of heat
        for i, spot in enumerate(spots, 1):
            busyness = spot.get("live_busyness", 0)
            folium.CircleMarker(
                location=[spot["lat"], spot["lon"]],
                radius=10,
                popup=f"#{i} {spot['name']} — {busyness}%",
                tooltip=f"#{i} {spot['name']} ({busyness}%)",
                color="white",
                weight=2,
                fill=True,
                fill_color="white" if busyness >= 50 else "gray",
                fill_opacity=0.8,
            ).add_to(m2)

        st_folium(m2, width=1000, height=550, key="heatmap")

        # Time comparison
        st.markdown("### Busyness Over Time")
        hours_to_show = list(range(0, 24))
        all_s = load_all_spots(selected_hour)

        # Build comparison chart
        chart_rows = []
        for spot in all_s:
            hourly = spot.get("hourly_profile", [0]*24)
            for h in hours_to_show:
                chart_rows.append({
                    "Hour": h,
                    "Venue": spot["name"][:25],
                    "Busyness": hourly[h] if h < len(hourly) else 0,
                })

        import pandas as pd
        df = pd.DataFrame(chart_rows)
        # Pivot for multi-line chart
        pivot = df.pivot(index="Hour", columns="Venue", values="Busyness")
        st.line_chart(pivot, height=300)

    except ImportError:
        st.warning("Install `folium` and `streamlit-folium` for heat map.")


# ═══════════════════════════════════════════════════════════════
# TAB 3: LIVE TRAFFIC
# ═══════════════════════════════════════════════════════════════
with tab_traffic:
    st.subheader(f"📊 Traffic Intelligence — {selected_day} {selected_hour}:00")

    all_spots = load_all_spots(selected_hour)

    # Current busyness dashboard
    st.markdown("### Real-Time Busyness")
    cols = st.columns(5)
    for i, spot in enumerate(all_spots):
        col = cols[i % 5]
        busyness = spot.get("live_busyness", 0)
        delta = None
        hourly = spot.get("hourly_profile", [])
        if hourly and selected_hour > 0:
            prev = hourly[selected_hour - 1]
            delta = busyness - prev
        col.metric(
            spot["name"][:18],
            f"{busyness}%",
            delta=f"{delta:+d}%" if delta is not None else None,
        )

    # 24-hour timeline
    st.markdown("### 24-Hour Traffic Profile")
    spot_names = [s["name"] for s in all_spots]
    selected_spot_name = st.selectbox("Select venue for deep dive", spot_names)

    selected_spot = next(
        (s for s in all_spots if s["name"] == selected_spot_name), None
    )
    if selected_spot and "hourly_profile" in selected_spot:
        hourly = selected_spot["hourly_profile"]

        import pandas as pd
        timeline_df = pd.DataFrame({
            "Hour": list(range(24)),
            "Busyness (%)": hourly,
        })
        st.area_chart(timeline_df, x="Hour", y="Busyness (%)", height=250)

        peak_hour = hourly.index(max(hourly))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peak Hour", f"{peak_hour}:00")
        c2.metric("Peak Busyness", f"{max(hourly)}%")
        c3.metric("Current", f"{hourly[selected_hour]}%")
        c4.metric("Daily Average", f"{sum(hourly)//24}%")

    # OSM venue discovery
    st.markdown("### Venue Discovery (OpenStreetMap)")
    try:
        osm_places = load_osm()
        if osm_places:
            st.success(f"Scanned **{len(osm_places)} venues** within 400m radius")

            import pandas as pd
            by_type = {}
            for p in osm_places:
                t = p.get("amenity_type", "other")
                by_type[t] = by_type.get(t, 0) + 1
            type_df = pd.DataFrame(
                {"Type": list(by_type.keys()), "Count": list(by_type.values())}
            )
            st.bar_chart(type_df, x="Type", y="Count")

            with st.expander(f"📋 Full Venue List ({len(osm_places)} venues)"):
                for p in osm_places:
                    st.markdown(
                        f"• **{p['name']}** ({p['amenity_type']}) — "
                        f"`{p['lat']:.5f}, {p['lon']:.5f}`"
                    )
        else:
            st.info("OSM data unavailable (network access required)")
    except Exception:
        st.info("OSM scan unavailable")

    # NCDOT
    st.markdown("### NCDOT Vehicle Volume (AADT)")
    ncdot = get_ncdot_traffic()
    for road, data in ncdot.items():
        st.markdown(f"• **{road}**: `{data['aadt']:,}` vehicles/day ({data['year']})")


# ═══════════════════════════════════════════════════════════════
# TAB 4: NETWORK ANALYSIS
# ═══════════════════════════════════════════════════════════════
with tab_network:
    st.subheader("🕸️ Street Network Analysis")
    st.caption(
        "Pedestrian network topology from OpenStreetMap. "
        "Intersection nodes and connectivity scoring."
    )

    try:
        import folium
        from streamlit_folium import st_folium

        network = load_network()

        m3 = folium.Map(
            location=list(FRANKLIN_STREET_CENTER),
            zoom_start=16,
            tiles="CartoDB dark_matter",
        )

        # Draw street network edges
        if not network.get("fallback"):
            net_lines = load_network_lines()
            for line in net_lines:
                folium.PolyLine(
                    locations=[
                        [line["from"][1], line["from"][0]],
                        [line["to"][1], line["to"][0]],
                    ],
                    color=f"rgba({line['color'][0]},{line['color'][1]},{line['color'][2]},{line['color'][3]/255})",
                    weight=2,
                    opacity=0.7,
                    tooltip=f"{line['highway']}: {line['name']}" if line['name'] else line['highway'],
                ).add_to(m3)

        # Draw intersections
        intersections = load_intersections()
        for ix in intersections:
            size = min(12, ix["degree"] * 2)
            folium.CircleMarker(
                location=[ix["lat"], ix["lon"]],
                radius=size,
                popup=(
                    f"<b>Intersection Node</b><br>"
                    f"Degree: {ix['degree']}<br>"
                    f"Connectivity: {ix.get('connectivity_score', 'N/A')}/10<br>"
                    f"Name: {ix.get('name', 'N/A')}"
                ),
                tooltip=f"Degree-{ix['degree']} intersection",
                color="#00ff88",
                fill=True,
                fill_color="#00ff88",
                fill_opacity=0.7,
            ).add_to(m3)

        st_folium(m3, width=1000, height=500, key="network_map")

        # Network stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Network Nodes", f"{network.get('node_count', 0):,}")
        c2.metric("Network Edges", f"{network.get('edge_count', 0):,}")
        c3.metric("Intersections", f"{len(intersections)}")

        # Walk scores for spots
        st.markdown("### Walk Scores by Venue")
        walk_spots = copy.deepcopy(spots)
        walk_spots = compute_walk_scores(walk_spots, network)

        for spot in sorted(walk_spots, key=lambda s: s.get("walk_score", 0), reverse=True):
            ws = spot.get("walk_score", 0)
            ix_count = spot.get("nearby_intersections", 0)
            bar = "█" * (ws // 5) + "░" * (20 - ws // 5)
            st.markdown(
                f"**{spot['name'][:35]}** — Walk Score: **{ws}** "
                f"({ix_count} nearby intersections) `{bar}`"
            )

    except ImportError:
        st.warning("Install `folium` for network visualization.")
    except Exception as e:
        st.error(f"Network analysis error: {e}")


# ═══════════════════════════════════════════════════════════════
# TAB 5: OSINT INTELLIGENCE
# ═══════════════════════════════════════════════════════════════
with tab_intel:
    st.subheader("🕵️ OSINT Intelligence Briefing")

    # Demographics
    st.markdown("### 📊 Population Demographics")
    demo = get_demographics()

    c1, c2, c3, c4 = st.columns(4)
    d = demo["data"]
    c1.metric("Total Population", f"{d['total_population']:,}")
    c2.metric("Median Age", f"{d['median_age']}")
    c3.metric("College Enrollment", f"{d['college_enrollment']:,}")
    c4.metric("Pop. Density", f"{d['population_density_per_sq_mi']:,}/mi²")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Age 18-24", f"{d['pct_18_24']}%")
    c6.metric("Bachelor's+", f"{d['pct_bachelors_or_higher']}%")
    c7.metric("Renter-Occupied", f"{d['pct_renter_occupied']}%")
    c8.metric("Median Income", f"${d['median_household_income']:,}")

    with st.expander("📋 Demographic Insights for Trivia Marketing"):
        for insight in demo["insights"]:
            st.markdown(
                f"**{insight['metric']}:** {insight['value']}\n\n"
                f"→ {insight['insight']}"
            )
            st.markdown("---")

    # Weather
    st.markdown("### 🌤️ Weather Conditions")
    weather = fetch_weather()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temperature", f"{weather['temp_f']}°F")
    c2.metric("Feels Like", f"{weather['feels_like_f']}°F")
    c3.metric("Humidity", f"{weather['humidity']}%")
    c4.metric("Wind", f"{weather['wind_mph']} mph")

    if weather["is_good_flyering_weather"]:
        st.success(f"✅ {weather['weather_impact']}")
    else:
        st.warning(f"⚠️ {weather['weather_impact']}")

    # Event Context
    st.markdown("### 📅 Event Intelligence")
    event = get_event_context()
    c1, c2 = st.columns(2)
    c1.metric("Event Type", event["event_type"].replace("_", " ").title())
    c2.metric("Traffic Multiplier", f"{event['traffic_multiplier']}x")
    st.info(
        f"**Best flyering window:** {event['best_flyering_window']}\n\n"
        f"**Notes:** {event['notes']}"
    )

    with st.expander("📋 All Event Types & Impact"):
        for etype, edata in event["all_event_types"].items():
            st.markdown(
                f"**{etype.replace('_', ' ').title()}** — "
                f"Traffic: {edata['traffic_multiplier']}x | "
                f"Best window: {edata['best_flyering_window']}"
            )
            st.caption(edata["notes"])

    # Social Signals
    st.markdown("### 📱 Social Media Intelligence")
    from intel import get_social_signals
    social = get_social_signals()
    fs = social["franklin_street"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Instagram Posts/Day", f"~{fs['avg_instagram_posts_per_day']}")
    c2.metric("TikTok Mentions/Week", f"~{fs['avg_tiktok_mentions_per_week']}")
    c3.metric("Est. Monthly Reach", f"{fs['estimated_monthly_reach']:,}")

    st.markdown(
        "**Top Hashtags:** " +
        " ".join(f"`{tag}`" for tag in fs["top_hashtags"])
    )
    peak_hours = ", ".join(f"{h}:00" for h in fs["peak_posting_hours"])
    st.caption(f"Peak posting hours: {peak_hours}")


# ═══════════════════════════════════════════════════════════════
# TAB 6: TRIVIA TRENDS
# ═══════════════════════════════════════════════════════════════
with tab_trends:
    st.subheader("📈 Search Intelligence — Trivia Topic Engine")

    trends_report = None
    if use_live_trends:
        with st.spinner("Pulling live trends from Google..."):
            trends_report = load_trends()

    suggestions, using_fallback = generate_trivia_suggestions(trends_report)

    if using_fallback:
        st.caption(
            "Using curated intelligence. Enable 'Google Trends (Live)' "
            "in sidebar for real-time data."
        )

    # Two-column layout
    col1, col2 = st.columns(2)

    for idx, s in enumerate(suggestions):
        icon = "🔥" if s["strength"] == "HOT" else "📈" if s["strength"] == "Warm" else "📊"
        target_col = col1 if idx % 2 == 0 else col2

        with target_col:
            st.markdown(
                f"### {icon} {s['category']}\n"
                f"**{s['strength']}** — Score: {s['score']}"
            )
            st.markdown(s["suggestion"])

            if s.get("related_rising"):
                rising = s["related_rising"][:5]
                st.markdown(
                    "**↗ Rising:** " + " · ".join(f"`{q}`" for q in rising)
                )
            st.markdown("---")

    if trends_report and trends_report.get("trending_now"):
        st.markdown("### 🔍 Nationally Trending Now")
        trending = trends_report["trending_now"][:15]
        cols = st.columns(3)
        for i, query in enumerate(trending):
            cols[i % 3].markdown(f"• {query}")

        local = trends_report.get("locally_relevant", [])
        if local:
            st.markdown("### 🏠 Locally Relevant (NC/UNC)")
            for q in local:
                st.success(f"**{q}**")


# ═══════════════════════════════════════════════════════════════
# TAB 7: FULL REPORT
# ═══════════════════════════════════════════════════════════════
with tab_report:
    st.subheader("📄 Full Surveillance Report")

    from panopticon import generate_report

    report = generate_report(
        time_of_day=time_of_day,
        num_spots=num_spots,
        fetch_live_trends=False,
        fetch_live_traffic=True,
        hour=selected_hour,
    )
    st.code(report, language=None)

    st.download_button(
        label="📥 Download Report",
        data=report,
        file_name=f"panopticon_v3_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )
