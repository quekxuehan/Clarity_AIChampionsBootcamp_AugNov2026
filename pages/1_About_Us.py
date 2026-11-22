import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(page_title="About Us | Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("About Us")
st.markdown(
    "Clarity SG is an educational prototype created for the AI Champions "
    "Bootcamp (Aug-Nov 2026). It helps event planners view Singapore's "
    "latest 24-hour Pollutant Standards Index (PSI) readings by region."
)

st.header("Project scope and objectives")
st.markdown(
    """
The project demonstrates how a public environmental data feed can be turned
into a simple, region-based event-planning reference. It aims to:

- make the latest 24-hour PSI snapshot easy to compare across Singapore's
  Central, East, North, South, and West regions;
- let a planner compare a selected region's reading with an organization-defined
  action threshold; and
- provide context for reviewing plans without making an automatic decision.

The app does not forecast conditions for a future event, issue official health
advice, or automatically cancel or change an event.
"""
)

st.header("Data sources")
st.markdown(
    """
- [data.gov.sg real-time PSI API](https://api-open.data.gov.sg/v2/real-time/api/psi)
  supplies the live readings and their timestamps.
- [NEA air pollution information](https://www.nea.gov.sg/our-services/pollution-control/air-pollution/psi)
  provides official PSI context.
"""
)

st.header("Features")
st.markdown(
    """
- Regional 24-hour PSI reading and timestamp.
- PSI band labels: Good, Moderate, Unhealthy, Very unhealthy, and Hazardous.
- Configurable event action threshold and event setting.
- Comparison table for available regional readings.
- Password-protected access.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
