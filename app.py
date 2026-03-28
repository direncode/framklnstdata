"""
==============================================
  FRANKLIN STREET PANOPTICON v1
  Streamlit Web App
==============================================

Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Franklin Street Panopticon",
    page_icon="📍",
    layout="wide",
)

from spots import get_ranked_spots, FRANKLIN_STREET_SPOTS
from panopticon import generate_trivia_suggestions, fetch_trends, TRIVIA_CATEGORIES

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Franklin Street Panopticon v1")
st.markdown(
    "*Trivia night optimization for Bandidos on Franklin Street, UNC Chapel Hill*"
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------------------------

st.sidebar.header("Settings")

time_of_day = st.sidebar.selectbox(
    "Optimize for time of day",
    ["evening", "daytime", "morning"],
    index=0,
)

num_spots = st.sidebar.slider("Number of spots to show", 3, 10, 8)

use_live_trends = st.sidebar.checkbox("Fetch live Google Trends", value=False)

# ---------------------------------------------------------------------------
# Tab Layout
# ---------------------------------------------------------------------------

tab_map, tab_spots, tab_trends, tab_report = st.tabs(
    ["Map", "Spot Rankings", "Trivia Trends", "Full Report"]
)

# --- Map Tab ---
with tab_map:
    st.subheader("QR Code & Flyer Placement Map")

    spots = get_ranked_spots(time_of_day=time_of_day, top_n=num_spots)

    try:
        import folium
        from streamlit_folium import st_folium

        # Center on Franklin Street
        m = folium.Map(
            location=[35.9132, -79.0555],
            zoom_start=16,
            tiles="CartoDB positron",
        )

        for i, spot in enumerate(spots, 1):
            color = "red" if i <= 3 else "orange" if i <= 5 else "blue"
            folium.Marker(
                location=[spot["lat"], spot["lon"]],
                popup=folium.Popup(
                    f"<b>#{i} {spot['name']}</b><br>"
                    f"Score: {spot['composite_score']}/10<br>"
                    f"<br>{spot['rationale']}<br>"
                    f"<br><i>Tip: {spot['placement_tip']}</i>",
                    max_width=300,
                ),
                tooltip=f"#{i} {spot['name']} ({spot['composite_score']}/10)",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(m)

        st_folium(m, width=800, height=500)
        st.caption(
            "Red = top 3 spots | Orange = spots 4-5 | Blue = remaining. "
            "Click markers for details."
        )

    except ImportError:
        st.warning(
            "Install `folium` and `streamlit-folium` for the interactive map: "
            "`pip install folium streamlit-folium`"
        )
        st.markdown("**Top spots (text fallback):**")
        for i, spot in enumerate(spots, 1):
            st.markdown(
                f"**#{i} {spot['name']}** — Score: {spot['composite_score']}/10 "
                f"— ({spot['lat']}, {spot['lon']})"
            )

# --- Spot Rankings Tab ---
with tab_spots:
    st.subheader(f"Top {num_spots} Spots ({time_of_day.title()} Optimization)")

    spots = get_ranked_spots(time_of_day=time_of_day, top_n=num_spots)

    for i, spot in enumerate(spots, 1):
        with st.expander(
            f"#{i} — {spot['name']} (Score: {spot['composite_score']}/10)",
            expanded=(i <= 3),
        ):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Foot Traffic", f"{spot['foot_traffic']}/10")
                st.metric("Dwell Time", f"{spot['dwell_time']}/10")
                st.metric("Visibility", f"{spot['visibility']}/10")
                st.metric("Student Density", f"{spot['student_density']}/10")
            with col2:
                st.markdown(f"**Address:** {spot['address']}")
                st.markdown(f"**Best times:** {', '.join(spot['best_times'])}")
                st.markdown(f"**Why here:** {spot['rationale']}")
                st.info(f"**Placement tip:** {spot['placement_tip']}")

# --- Trivia Trends Tab ---
with tab_trends:
    st.subheader("Trending Trivia Topics")

    trends_data = None
    if use_live_trends:
        with st.spinner("Fetching live trends from Google (this may take 30-60s)..."):
            all_keywords = []
            for kws in TRIVIA_CATEGORIES.values():
                all_keywords.extend(kws)
            all_keywords = list(dict.fromkeys(all_keywords))
            trends_data = fetch_trends(all_keywords)

    suggestions, using_fallback = generate_trivia_suggestions(trends_data)

    if using_fallback:
        st.caption(
            "Using curated fallback data. Enable 'Fetch live Google Trends' "
            "in the sidebar for real-time data."
        )

    for s in suggestions:
        if s["strength"] == "HOT":
            icon = "🔥"
        elif s["strength"] == "Warm":
            icon = "📈"
        else:
            icon = "📊"

        st.markdown(
            f"### {icon} {s['category']} — *{s['strength']}* (score: {s['score']})"
        )
        st.markdown(s["suggestion"])
        st.markdown("---")

# --- Full Report Tab ---
with tab_report:
    st.subheader("Full Text Report")
    st.caption("Copy-paste this or save it for reference.")

    from panopticon import generate_report

    report = generate_report(
        time_of_day=time_of_day,
        num_spots=num_spots,
        fetch_live_trends=False,  # Don't double-fetch in report tab
    )
    st.code(report, language=None)

    st.download_button(
        label="Download Report (.txt)",
        data=report,
        file_name="panopticon_report.txt",
        mime="text/plain",
    )
