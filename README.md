# Franklin Street Panopticon v1

A trivia night optimization tool for UNC Chapel Hill's Franklin Street.
Helps maximize visibility and engagement for trivia events at Bandidos.

## What It Does

1. **Foot Traffic Optimizer** - Ranks the best spots on Franklin Street to place QR codes and flyers based on foot traffic, dwell time, and visibility.
2. **Search Interpretation Engine** - Pulls Google Trends data for UNC/Chapel Hill keywords and suggests trending trivia categories.
3. **Combined Report** - Generates a single easy-to-read report with placement recommendations and trivia topic suggestions.

## Quick Start

```bash
pip install -r requirements.txt

# Run as CLI (generates a text report)
python panopticon.py

# Run as web app (interactive map + report)
streamlit run app.py
```

## Files

- `panopticon.py` - Core engine (foot traffic data, trends, report generation). Also works as a standalone CLI.
- `app.py` - Streamlit web interface with interactive map.
- `spots.py` - Franklin Street location database with traffic scores and metadata.
- `requirements.txt` - Python dependencies.
