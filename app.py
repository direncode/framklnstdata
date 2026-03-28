"""
==============================================
  FRANKLIN STREET DATA
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
    page_title="Franklin Street Data",
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
from spots import get_enriched_spots
from traffic import (
    build_heatmap_data,
    fetch_nearby_places,
    get_ncdot_traffic,
)
from trends import build_trends_report, generate_trivia_suggestions
from satellite import TILE_SOURCES, PYDECK_VIEWS, get_folium_tile_layers
from intel import build_intel_report, fetch_demographics, fetch_weather, fetch_unc_events
from network import (
    fetch_street_network,
    find_intersections,
    compute_walk_scores,
    get_network_lines,
)
from spatial import (
    build_spatial_analysis,
    compute_isochrones_for_spots,
    compute_kde,
    kde_to_heatmap_points,
    dbscan_cluster,
    compute_voronoi,
    compute_hexbins,
    gravity_model,
    pareto_frontier,
    optimize_placement,
)
from buildings import (
    fetch_building_footprints,
    compute_viewshed_for_spots,
)
from osint import (
    fetch_transit_stops,
    fetch_crime_data,
    fetch_abc_licenses,
    fetch_all_reddit,
    build_deep_osint_report,
)
from forecast import (
    forecast_from_live_data,
    build_forecast_report,
)
from livefeed import build_live_feed

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div style='text-align: center; padding: 10px 0;'>
    <h1 style='color: #00ff88; margin-bottom: 0;'>
        📡 FRANKLIN STREET DATA
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
    import os
    st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
    if GOOGLE_PLACES_API_KEY:
        st.markdown("🟢 Google Places: ACTIVE")
    else:
        st.markdown("⚫ Google Places: NO KEY")
    st.markdown("🟢 OpenStreetMap: ACTIVE")
    if os.environ.get("OPENWEATHER_API_KEY"):
        weather = fetch_weather()
        if weather:
            st.markdown(f"🟢 Weather: {weather['temp_f']}°F, {weather['description']}")
        else:
            st.markdown("🔴 Weather: API ERROR")
    else:
        st.markdown("⚫ Weather: NO KEY")
    if os.environ.get("CENSUS_API_KEY"):
        st.markdown("🟢 Census: ACTIVE")
    else:
        st.markdown("⚫ Census: NO KEY")
    st.markdown("🟢 Reddit: ACTIVE (no key)")
    st.markdown("🟢 UNC Calendar: ACTIVE (no key)")
    st.markdown("🟢 DTH RSS: ACTIVE (no key)")

# ---------------------------------------------------------------------------
# Data Loading (Cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_spots(tod, hr, n):
    return get_enriched_spots(time_of_day=tod, hour=hr, top_n=n)

@st.cache_data(ttl=3600)
def load_all_spots(hr):
    return get_enriched_spots(hour=hr, top_n=100)

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

tab_sat, tab_heat, tab_traffic, tab_network, tab_spatial, tab_intel, tab_osint, tab_forecast, tab_trends, tab_report = st.tabs([
    "🛰️ SATELLITE", "🔥 HEAT MAP", "📊 TRAFFIC", "🕸️ NETWORK",
    "🔬 SPATIAL", "🕵️ INTEL", "🔍 DEEP OSINT", "📉 FORECAST",
    "📈 TRENDS", "📄 REPORT",
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
            busyness = spot.get("busyness") or spot.get("live_busyness") or 0
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

            busyness_str = f"{busyness}%" if busyness else "no data"
            popup_html = f"""
            <div style='width:280px; font-family: monospace; font-size: 11px;'>
                <h3 style='color: #1a73e8; margin:0;'>{spot['name']}</h3>
                <hr style='margin:4px 0;'>
                <table style='width:100%;'>
                    <tr><td><b>Busyness</b></td><td>{busyness_str}</td></tr>
                    <tr><td><b>Type</b></td><td>{spot.get('amenity_type', 'N/A')}</td></tr>
                    <tr><td><b>Coords</b></td>
                        <td>{spot['lat']:.5f}, {spot['lon']:.5f}</td></tr>
                </table>
            </div>
            """

            folium.Marker(
                location=[spot["lat"], spot["lon"]],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{spot['name']} | {busyness or '?'}% busy",
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
            busyness = spot.get("busyness") or spot.get("live_busyness") or 0
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
        busyness = spot.get("busyness") or spot.get("live_busyness") or 0
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
# TAB 5: SPATIAL ANALYTICS
# ═══════════════════════════════════════════════════════════════
with tab_spatial:
    st.subheader("🔬 Advanced Spatial Analytics")

    import pandas as pd

    # Run spatial analysis
    spatial = build_spatial_analysis(spots, hour=selected_hour)

    # Pareto Frontier
    st.markdown("### Pareto-Optimal Spots")
    st.caption("Spots that can't be beaten on ALL metrics simultaneously")
    pareto = spatial["pareto_frontier"]
    for p in pareto:
        status = "⭐ PARETO OPTIMAL" if p["is_pareto"] else "  dominated"
        scores_str = " | ".join(f"{k}: {v}" for k, v in p["scores"].items())
        st.markdown(f"**{p['spot_name']}** — {status} — {scores_str}")

    st.markdown("---")

    # Optimal Placement
    st.markdown("### Optimal QR Code Placement (5 spots, max coverage)")
    optimal = spatial["optimal_placement"]
    for o in optimal:
        st.markdown(
            f"**#{o['rank']}** — {o['spot_name']} "
            f"(score: {o['composite_score']})"
        )

    st.markdown("---")

    # Clusters
    st.markdown("### DBSCAN Activity Clusters")
    clusters = spatial["clusters"]
    if clusters:
        for c in clusters:
            st.markdown(
                f"**Cluster {c['cluster_id']}** — "
                f"{c['member_count']} venues, "
                f"total weight: {c['total_weight']}, "
                f"center: ({c['center'][0]:.4f}, {c['center'][1]:.4f})"
            )
    else:
        st.info("No significant clusters detected at current parameters")

    # Voronoi
    st.markdown("### Voronoi Influence Zones")
    st.caption("Which venue 'owns' the most territory")
    voronoi = spatial["voronoi_cells"]
    voronoi_data = pd.DataFrame([
        {"Venue": v["spot_name"][:25], "Coverage %": v["coverage_area_pct"]}
        for v in voronoi
    ])
    st.bar_chart(voronoi_data, x="Venue", y="Coverage %")

    # Isochrones
    st.markdown("### Walk-Time Isochrones (Top 3 Spots)")
    try:
        import folium
        from streamlit_folium import st_folium

        m_iso = folium.Map(
            location=list(FRANKLIN_STREET_CENTER),
            zoom_start=16, tiles="CartoDB dark_matter",
        )
        iso_data = spatial["isochrones"]
        iso_colors = {"3": "#ff000066", "5": "#ff660066"}
        for spot_iso in iso_data:
            for ring in spot_iso["isochrones"]:
                folium.Polygon(
                    locations=ring["polygon"],
                    color=ring["color"],
                    fill=True,
                    fill_color=ring["color"],
                    fill_opacity=0.15,
                    tooltip=f"{spot_iso['spot_name']} — {ring['minutes']} min walk",
                ).add_to(m_iso)
            folium.Marker(
                location=[spot_iso["lat"], spot_iso["lon"]],
                tooltip=spot_iso["spot_name"],
                icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"),
            ).add_to(m_iso)
        st_folium(m_iso, width=900, height=400, key="isochrone_map")
    except ImportError:
        st.info("Install folium for isochrone visualization")

    # Viewshed
    st.markdown("### Viewshed Analysis (Line-of-Sight Visibility)")
    try:
        viewshed = compute_viewshed_for_spots(spots)
        for vs in viewshed:
            bar = "█" * (vs["visibility_pct"] // 5) + "░" * (20 - vs["visibility_pct"] // 5)
            st.markdown(
                f"**{vs['spot_name'][:30]}** — "
                f"{vs['visibility_pct']}% visible `{bar}`"
            )
    except Exception:
        st.info("Viewshed data unavailable")

    # Gravity Model
    st.markdown("### Gravity Model — Where Do People Go?")
    st.caption("Probability of visiting each venue from campus center")
    campus_lat, campus_lon = 35.9117, -79.0510
    gravity = gravity_model(spots, campus_lat, campus_lon)
    gravity_df = pd.DataFrame([
        {"Venue": g["spot_name"][:25], "Probability %": g["probability_pct"]}
        for g in gravity[:8]
    ])
    st.bar_chart(gravity_df, x="Venue", y="Probability %")


# ═══════════════════════════════════════════════════════════════
# TAB 6: INTEL (Live APIs Only)
# ═══════════════════════════════════════════════════════════════
with tab_intel:
    st.subheader("🕵️ Live Intelligence Briefing")

    # Demographics (requires CENSUS_API_KEY)
    st.markdown("### 📊 Population Demographics")
    demo = fetch_demographics()
    if demo:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Population", f"{demo['total_population']:,}")
        c2.metric("Median Age", f"{demo.get('median_age', 'N/A')}")
        c3.metric("School Enrollment", f"{demo.get('school_enrollment', 'N/A'):,}" if demo.get('school_enrollment') else "N/A")
        c4.metric("Age 18-24", f"{demo.get('pct_18_24', 'N/A')}%")
        st.caption(f"Source: {demo['source']}")
    else:
        st.info("Census data unavailable. Set `CENSUS_API_KEY` env var (free at api.census.gov)")

    st.markdown("---")

    # Weather (requires OPENWEATHER_API_KEY)
    st.markdown("### 🌤️ Weather Conditions")
    weather = fetch_weather()
    if weather:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temperature", f"{weather['temp_f']}°F")
        c2.metric("Feels Like", f"{weather['feels_like_f']}°F")
        c3.metric("Humidity", f"{weather['humidity']}%")
        c4.metric("Wind", f"{weather['wind_mph']} mph")
        if weather.get("is_good_flyering_weather"):
            st.success(f"✅ Good flyering weather: {weather['description']}")
        else:
            st.warning(f"⚠️ Challenging conditions: {weather['description']}")
        st.caption(f"Source: {weather['source']}")
    else:
        st.info("Weather data unavailable. Set `OPENWEATHER_API_KEY` env var (free at openweathermap.org)")

    st.markdown("---")

    # UNC Events (no key needed)
    st.markdown("### 📅 UNC Events (Next 7 Days)")
    events = fetch_unc_events()
    if events:
        st.success(f"Found **{len(events)} upcoming events**")
        for ev in events[:10]:
            tags_str = ", ".join(ev.get("tags", [])[:3])
            st.markdown(
                f"• **{ev['title']}** — {ev.get('location', 'TBD')} | "
                f"{ev.get('start', '')} {f'| Tags: {tags_str}' if tags_str else ''}"
            )
    else:
        st.info("Could not fetch UNC events calendar")

    st.markdown("---")

    # Live Feed
    st.markdown("### 📡 Live Keyword Feed")
    feed = build_live_feed()
    if feed.get("extracted_keywords"):
        top_kw = feed["extracted_keywords"][:15]
        st.markdown("**Top keywords across Reddit + DTH + Trends:**")
        kw_str = " · ".join(f"`{k['keyword']}` ({k['frequency']})" for k in top_kw)
        st.markdown(kw_str)

    if feed.get("trivia_suggestions"):
        st.markdown("### 💡 Live Trivia Suggestions")
        for s in feed["trivia_suggestions"][:8]:
            st.markdown(f"**[{s['source']}]** {s['suggestion']}")


# ═══════════════════════════════════════════════════════════════
# TAB 7: DEEP OSINT (All Live)
# ═══════════════════════════════════════════════════════════════
with tab_osint:
    st.subheader("🔍 Deep OSINT Intelligence (Live Feeds)")

    # Reddit Feed
    st.markdown("### 📱 Reddit — r/UNC, r/chapelhill, r/NorthCarolina")
    reddit = fetch_all_reddit()
    if reddit:
        for sub, posts in reddit.items():
            st.markdown(f"**r/{sub}** — {len(posts)} recent posts")
            for post in posts[:5]:
                st.markdown(
                    f"• [{post['score']}↑ {post['num_comments']}💬] "
                    f"**{post['title'][:80]}**"
                )
    else:
        st.info("Reddit data unavailable (network access required)")

    st.markdown("---")

    # Crime Intelligence (live from ArcGIS)
    st.markdown("### 🚨 Crime Intelligence (Chapel Hill Open Data)")
    crime = fetch_crime_data()
    if crime:
        st.success(f"**{len(crime)} incidents** from Chapel Hill ArcGIS")
        for incident in crime[:10]:
            st.markdown(
                f"• **{incident.get('type', 'Unknown')}** — "
                f"{incident.get('location', 'Unknown location')}"
            )
    else:
        st.info("Crime data unavailable from Chapel Hill ArcGIS")

    st.markdown("---")

    # Transit Stops (live GTFS)
    st.markdown("### 🚌 Transit Stops (Chapel Hill Transit GTFS)")
    stops = fetch_transit_stops()
    if stops:
        st.success(f"**{len(stops)} bus stops** near Franklin Street")
        for stop in stops[:10]:
            st.markdown(f"• **{stop['stop_name']}** — `{stop['lat']:.4f}, {stop['lon']:.4f}`")
    else:
        st.info("Transit GTFS data unavailable")

    st.markdown("---")

    # ABC Licenses (live from NC ABC)
    st.markdown("### 🍺 ABC License Intelligence (NC ABC Commission)")
    licenses = fetch_abc_licenses()
    if licenses:
        st.success(f"**{len(licenses)} active licenses** on Franklin Street")
        for lic in licenses:
            st.markdown(
                f"• **{lic['name']}** — {lic.get('permit_type', 'N/A')} | "
                f"{lic.get('address', '')}"
            )
    else:
        st.info("ABC license data unavailable")


# ═══════════════════════════════════════════════════════════════
# TAB 8: FORECAST (Live Signal-Based)
# ═══════════════════════════════════════════════════════════════
with tab_forecast:
    st.subheader("📉 Live Signal Forecast")
    st.caption("Predictions derived from live data feeds — not hardcoded baselines.")

    # Live signal forecast
    st.markdown("### 📡 Available Signals")
    forecast = forecast_from_live_data()

    signal_count = forecast.get("signal_count", 0)
    st.metric("Live Signals Available", f"{signal_count}/5")

    for name, signal in forecast.get("signals", {}).items():
        with st.expander(f"Signal: {name}", expanded=True):
            source = signal.get("source", "unknown")
            st.caption(f"Source: {source}")
            # Display signal-specific data
            if name == "weather" and signal.get("data"):
                w = signal["data"]
                st.markdown(f"**{w.get('temp_f', '?')}°F** — {w.get('description', '?')}")
            elif name == "trends" and signal.get("data"):
                for kw, score in signal["data"].items():
                    st.markdown(f"• `{kw}`: {score}")
            elif name == "unc_events":
                st.markdown(f"**{signal.get('count', 0)} events** this week")
                for ev in (signal.get("upcoming") or [])[:3]:
                    st.markdown(f"• {ev.get('title', '')}")
            elif name == "reddit":
                st.markdown(f"Avg post score: {signal.get('avg_post_score', 'N/A')}")
                for topic in (signal.get("recent_topics") or [])[:3]:
                    st.markdown(f"• {topic}")
            elif name == "transit":
                st.markdown(f"**{signal.get('stops_nearby', 0)} transit stops** nearby")

    st.markdown("---")

    # Recommendations
    st.markdown("### 🎯 Recommendations")
    for rec in forecast.get("recommendation", []):
        st.info(rec)



# ═══════════════════════════════════════════════════════════════
# TAB 9: TRIVIA TRENDS
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

    from main import generate_report

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
        file_name=f"franklinst_data_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )
