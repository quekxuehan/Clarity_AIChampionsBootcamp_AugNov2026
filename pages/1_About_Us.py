import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(page_title="About Us | Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("About Us")
st.markdown(
    "Clarity SG is an educational prototype created by Quek Xue Han for the AI Champions "
    "Bootcamp (Aug-Nov 2026). It helps event planners review Singapore's "
    "latest 1-hour PM2.5 activity guidance by region, alongside a 24-hour "
    "Pollutant Standards Index (PSI) overview and explanations of the app's "
    "guidance."
)

st.header("Project scope and objectives")
st.markdown(
    """
The project helps event planners review air-quality information as one input
to event planning. It aims to:

- make the latest 1-hour PM2.5 guidance and 24-hour PSI snapshot easy to
  compare across Singapore's Central, East, North, South, and West regions; and
- explain the app's guidance and data sources through the Ask Clarity
  question-and-answer feature.

The app does not forecast conditions for a future event, issue official health
advice, or decide whether an event should be cancelled or changed.
"""
)

st.header("Data sources")
st.markdown(
    """
- [data.gov.sg real-time PSI API](https://api-open.data.gov.sg/v2/real-time/api/psi)
  supplies the 24-hour PSI overview and its timestamp.
- [data.gov.sg real-time PM2.5 API](https://api-open.data.gov.sg/v2/real-time/api/pm25)
  supplies regional 1-hour PM2.5 readings and their timestamps.
- [NEA air pollution information](https://www.nea.gov.sg/our-services/pollution-control/air-pollution/psi)
  provides official PSI context.
- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) is used to
  look up submitted addresses; it does not provide the app's air-quality data.
"""
)

st.header("Features")
st.markdown(
    """
- Regional 24-hour PSI reading and timestamp.
- Regional 1-hour PM2.5 reading, activity-guidance band, and timestamp.
- PSI band labels: Good, Moderate, Unhealthy, Very unhealthy, and Hazardous.
- Event setting and guidance for healthy and vulnerable persons.
- Comparison table for available regional readings.
- Clickable region map and Singapore address lookup for choosing an
  approximate air-quality region.
- Ask Clarity: source-cited answers about the app's guidance, PSI bands, and
  data sources, based on a curated knowledge base.
- Password-protected access.
"""
)

st.header("Event location and privacy")
st.markdown(
    """
Choose a region by clicking the map or entering a Singapore address. Address
lookups are sent to OpenStreetMap's public Nominatim service. The app matches
the location to the nearest regional reference point, not an official region
boundary; review or change the suggested region before using the reading.
The map also loads OpenStreetMap tiles. Avoid entering sensitive addresses.
"""
)

st.header("Understanding the activity guidance")
st.markdown(
    """
The PM2.5 activity guidance uses these terms:

- **Reduce:** do less of the specified activity.
- **Minimise:** do as little as possible of the specified activity.
- **Avoid:** do not do the specified activity.
"""
)

st.header("Ask Clarity and privacy")
st.markdown(
    """
Ask Clarity uses OpenAI to find relevant excerpts from the curated knowledge
base and draft an answer with references. It does not retrieve live readings
or make event decisions. Questions and retrieved excerpts are sent to OpenAI
for processing; do not enter personal or sensitive information. For current
conditions and official advice, use the dashboard and linked data sources.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
