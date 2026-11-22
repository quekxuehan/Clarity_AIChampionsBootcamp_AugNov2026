import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(page_title="About Us | Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("About Us")
st.markdown(
    "Clarity SG is an educational prototype created by Quek Xue Han for the AI Champions "
    "Bootcamp (Aug-Nov 2026). It helps event planners review Singapore's "
    "latest 1-hour PM2.5 activity guidance by region, with a 24-hour "
    "Pollutant Standards Index (PSI) overview."
)

st.header("Project scope and objectives")
st.markdown(
    """
The project allows event planners to quickly and consistently decide whether their events will need to be cancelled in view of air quality. It aims to:

- make the latest 1-hour PM2.5 guidance and 24-hour PSI snapshot easy to
  compare across Singapore's Central, East, North, South, and West regions; and
- provide context for reviewing event plans.

The app does not forecast conditions for a future event, issue official health
advice, or automatically cancel or change an event.
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
- Password-protected access.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
