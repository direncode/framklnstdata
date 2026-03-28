"""
==============================================
  FRANKLIN STREET PANOPTICON v2
  Streamlit Web App
==============================================

Run with:  streamlit run app.py

Features:
  - Interactive heat map with hourly time slider
  - Live foot traffic bar charts and 24h timelines
  - Trending trivia topics with rising queries
  - Full downloadable report
"""

import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Franklin Street Panopticon v2",
    page_icon="📡",
    layout="wide",
)

from config import GOOGLE_PLACES_API_KEY, FRANKLIN_STREET_CENTER
from spots import get_enriched_spots, get_ranked_spots, FRANKLIN_STREET_SPOTS
from traffic import (
    build_heatmap_data,
    fetch_nearby_places,
    get_ncdot_traffic,
    aggregate_busyness,
)
from trends import (
    build_trends_report,
    generate_trivia_suggestions,
    TRIVIA_CATEGORIES,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📡 Franklin Street Panopticon v2")
st.markdown(
    "*Surveillance-grade trivia night optimization for Bandidos, "
    "UNC Chapel Hill*"
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------------------------

st.sidebar.header("⚙️ Controls")

time_of_day = st.sidebar.selectbox(
    "Optimize for time of day",
    ["evening", "daytime", "morning"],
    index=0,
)

num_spots = st.sidebar.slider("Number of spots to show", 3, 10, 8)

day_names = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]
current_dow = datetime.now().weekday()
selected_day = st.sidebar.selectbox(
    "Day of week", day_names, index=current_dow
)
selected_dow = day_names.index(selected_day)

current_hour = datetime.now().hour
selected_hour = st.sidebar.slider(
    "Hour of day (for heat map)", 0, 23, current_hour
)

use_live_trends = st.sidebar.checkbox("Fetch live Google Trends", value=False)

# API Status
with st.sidebar.expander("📊 Data Source Status"):
    if GOOGLE_PLACES_API_KEY:
        st.success("Google Places API: ✓ Key configured")
    else:
        st.info("Google Places API: Using fallback data")
    st.info("OpenStreetMap: ✓ Free (no key needed)")
    st.info("NCDOT Traffic: ✓ Static AADT data")
    if use_live_trends:
        st.info("Google Trends: Will fetch live")
    else:
        st.info("Google Trends: Using fallback data")

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_spots(tod, hr, n):
    return get_enriched_spots(time_of_day=tod, hour=hr, top_n=n)

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

spots = load_spots(time_of_day, selected_hour, num_spots)

# ---------------------------------------------------------------------------
# Tab Layout
# ---------------------------------------------------------------------------

tab_map, tab_traffic, tab_spots, tab_trends, tab_report = st.tabs(
    ["🗺️ Heat Map", "📊 Live Traffic", "📍 Spot Rankings",
     "📈 Trivia Trends", "📄 Full Report"]
)

# ─── Heat Map Tab ─────────────────────────────────────────────
with tab_map:
    st.subheader(f"Foot Traffic Heat Map — {selected_day} {selected_hour}:00")

    try:
        import folium
        from folium.plugins import HeatMap
        from streamlit_folium import st_folium

        m = folium.Map(
            location=list(FRANKLIN_STREET_CENTER),
            zoom_start=16,
            tiles="CartoDB dark_matter",
        )

        # Add heat map layer
        heatmap_data = load_heatmap(selected_hour, selected_dow)
        if heatmap_data:
            HeatMap(
                heatmap_data,
                min_opacity=0.3,
                max_val=1.0,
                radius=25,
                blur=20,
                gradient={
                    "0.2": "blue",
                    "0.4": "cyan",
                    "0.6": "lime",
                    "0.8": "orange",
                    "1.0": "red",
                },
            ).add_to(m)

        # Add venue markers on top
        for i, spot in enumerate(spots, 1):
            busyness = spot.get("live_busyness", 0)
            if busyness >= 70:
                color = "red"
            elif busyness >= 40:
                color = "orange"
            else:
                color = "blue"

            folium.CircleMarker(
                location=[spot["lat"], spot["lon"]],
                radius=8,
                popup=folium.Popup(
                    f"<b>#{i} {spot['name']}</b><br>"
                    f"Score: {spot['composite_score']}/10<br>"
                    f"Busyness: {busyness}%<br>"
                    f"<br>{spot['rationale']}<br>"
                    f"<br><i>Tip: {spot['placement_tip']}</i>",
                    max_width=300,
                ),
                tooltip=f"#{i} {spot['name']} ({busyness}% busy)",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
            ).add_to(m)

        # Add OSM discovered venues as small dots
        try:
            osm_places = load_osm()
            for place in osm_places:
                folium.CircleMarker(
                    location=[place["lat"], place["lon"]],
                    radius=3,
                    popup=f"{place['name']} ({place['amenity_type']})",
                    tooltip=place["name"],
                    color="gray",
                    fill=True,
                    fill_opacity=0.4,
                ).add_to(m)
        except Exception:
            pass

        # Add layer control
        folium.LayerControl().add_to(m)

        st_folium(m, width=900, height=550, key="heatmap")

        col1, col2, col3 = st.columns(3)
        col1.markdown("🔴 **Red** = High busyness (70%+)")
        col2.markdown("🟠 **Orange** = Medium (40-70%)")
        col3.markdown("🔵 **Blue** = Low (<40%)")

        st.caption(
            f"Heat map shows estimated foot traffic at {selected_hour}:00 on "
            f"{selected_day}. Small gray dots are OSM-discovered venues. "
            "Adjust the hour slider in the sidebar to see how traffic shifts."
        )

    except ImportError:
        st.warning(
            "Install `folium` and `streamlit-folium` for the interactive map: "
            "`pip install folium streamlit-folium`"
        )
        st.markdown("**Top spots (text fallback):**")
        for i, spot in enumerate(spots, 1):
            busyness = spot.get("live_busyness", "N/A")
            st.markdown(
                f"**#{i} {spot['name']}** — Score: {spot['composite_score']}/10 "
                f"— Busyness: {busyness}% — ({spot['lat']}, {spot['lon']})"
            )


# ─── Live Traffic Tab ─────────────────────────────────────────
with tab_traffic:
    st.subheader(f"Live Traffic Analysis — {selected_day} {selected_hour}:00")

    # Current busyness bar chart
    st.markdown("### Current Busyness by Venue")

    import copy
    all_spots = copy.deepcopy(FRANKLIN_STREET_SPOTS)
    all_spots = aggregate_busyness(all_spots, hour=selected_hour)

    chart_data = {
        "Venue": [s["name"][:30] for s in all_spots],
        "Busyness (%)": [s.get("live_busyness", 0) for s in all_spots],
    }
    st.bar_chart(chart_data, x="Venue", y="Busyness (%)", horizontal=True)

    # 24-hour timeline for selected spot
    st.markdown("### 24-Hour Traffic Profile")
    spot_names = [s["name"] for s in all_spots]
    selected_spot_name = st.selectbox("Select a venue", spot_names)

    selected_spot = next(
        (s for s in all_spots if s["name"] == selected_spot_name), None
    )
    if selected_spot and "hourly_profile" in selected_spot:
        hourly = selected_spot["hourly_profile"]
        timeline_data = {
            "Hour": list(range(24)),
            "Busyness (%)": hourly,
        }
        st.line_chart(timeline_data, x="Hour", y="Busyness (%)")

        peak_hour = hourly.index(max(hourly))
        st.info(
            f"**Peak hour:** {peak_hour}:00 ({max(hourly)}% busyness) — "
            f"**Current ({selected_hour}:00):** {hourly[selected_hour]}%"
        )

    # OSM venue discovery
    st.markdown("### Discovered Venues (OpenStreetMap)")
    try:
        osm_places = load_osm()
        if osm_places:
            st.success(
                f"Found **{len(osm_places)} venues** within 400m of "
                f"Franklin Street"
            )
            by_type = {}
            for p in osm_places:
                t = p.get("amenity_type", "other")
                by_type[t] = by_type.get(t, 0) + 1

            type_data = {
                "Type": list(by_type.keys()),
                "Count": list(by_type.values()),
            }
            st.bar_chart(type_data, x="Type", y="Count")

            with st.expander("Full venue list"):
                for p in osm_places:
                    st.markdown(
                        f"• **{p['name']}** ({p['amenity_type']}) — "
                        f"{p['lat']:.4f}, {p['lon']:.4f}"
                    )
        else:
            st.info("No OSM data available (may need network access)")
    except Exception as e:
        st.info(f"OSM data unavailable: {e}")

    # NCDOT context
    st.markdown("### NCDOT Vehicle Traffic (Annual Average)")
    ncdot = get_ncdot_traffic()
    for road, data in ncdot.items():
        st.markdown(f"• **{road}**: {data['aadt']:,} vehicles/day ({data['year']})")


# ─── Spot Rankings Tab ────────────────────────────────────────
with tab_spots:
    st.subheader(
        f"Top {num_spots} Spots ({time_of_day.title()} | {selected_day})"
    )

    for i, spot in enumerate(spots, 1):
        busyness = spot.get("live_busyness", None)
        label = f"#{i} — {spot['name']} (Score: {spot['composite_score']}/10)"
        if busyness is not None:
            label += f" | {busyness}% busy"

        with st.expander(label, expanded=(i <= 3)):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Foot Traffic", f"{spot['foot_traffic']}/10")
                st.metric("Dwell Time", f"{spot['dwell_time']}/10")
                st.metric("Visibility", f"{spot['visibility']}/10")
                st.metric("Student Density", f"{spot['student_density']}/10")
                if busyness is not None:
                    st.metric("Live Busyness", f"{busyness}%")
            with col2:
                st.markdown(f"**Address:** {spot['address']}")
                st.markdown(f"**Best times:** {', '.join(spot['best_times'])}")
                st.markdown(f"**Type:** {spot.get('place_type', 'N/A')}")
                st.markdown(f"**Why here:** {spot['rationale']}")
                st.info(f"**Placement tip:** {spot['placement_tip']}")

                # Show 24h sparkline if available
                if "hourly_profile" in spot:
                    hourly = spot["hourly_profile"]
                    mini_data = {
                        "Hour": list(range(24)),
                        "Busyness": hourly,
                    }
                    st.line_chart(mini_data, x="Hour", y="Busyness", height=120)


# ─── Trivia Trends Tab ───────────────────────────────────────
with tab_trends:
    st.subheader("Trending Trivia Topics")

    trends_report = None
    if use_live_trends:
        with st.spinner(
            "Fetching live trends from Google (this may take 30-60s)..."
        ):
            trends_report = load_trends()

    suggestions, using_fallback = generate_trivia_suggestions(trends_report)

    if using_fallback:
        st.caption(
            "Using curated fallback data. Enable 'Fetch live Google Trends' "
            "in the sidebar for real-time data."
        )

    # Two-column layout for suggestions
    col1, col2 = st.columns(2)

    for idx, s in enumerate(suggestions):
        if s["strength"] == "HOT":
            icon = "🔥"
        elif s["strength"] == "Warm":
            icon = "📈"
        else:
            icon = "📊"

        target_col = col1 if idx % 2 == 0 else col2

        with target_col:
            st.markdown(
                f"### {icon} {s['category']}\n"
                f"**{s['strength']}** (score: {s['score']})"
            )
            st.markdown(s["suggestion"])

            # Show rising queries
            if s.get("related_rising"):
                rising = s["related_rising"][:5]
                st.markdown(
                    "**↗ Rising searches:** " + " · ".join(
                        f"`{q}`" for q in rising
                    )
                )

            st.markdown("---")

    # Trending now section
    if trends_report and trends_report.get("trending_now"):
        st.markdown("### 🔍 Trending Nationally Right Now")
        trending = trends_report["trending_now"][:15]
        cols = st.columns(3)
        for i, query in enumerate(trending):
            cols[i % 3].markdown(f"• {query}")

        local = trends_report.get("locally_relevant", [])
        if local:
            st.markdown("### 🏠 Locally Relevant (NC/UNC)")
            for q in local:
                st.markdown(f"• **{q}**")


# ─── Full Report Tab ──────────────────────────────────────────
with tab_report:
    st.subheader("Full Text Report")
    st.caption("Copy-paste this or download for reference.")

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
        label="📥 Download Report (.txt)",
        data=report,
        file_name=f"panopticon_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )
