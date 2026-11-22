import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(
    page_title="Methodology | Clarity SG",
    page_icon="🌫️",
    layout="wide",
)
require_password()

st.title("Methodology")
st.markdown(
    "This page describes how Clarity SG retrieves, validates, and presents "
    "1-hour PM2.5 and 24-hour PSI data, and how its activity-guidance bands "
    "are selected."
)

st.header("Data flow")
st.markdown(
    """
1. **Request:** The dashboard sends HTTPS GET requests to the
   [data.gov.sg real-time PM2.5 API](https://api-open.data.gov.sg/v2/real-time/api/pm25)
   and [real-time PSI API](https://api-open.data.gov.sg/v2/real-time/api/psi).
   Each request has a 10-second timeout and identifies the app with a
   `User-Agent` header.
2. **Cache:** Successful results from each feed are cached for five minutes to
   limit repeated requests while keeping the dashboard periodically refreshed.
3. **Validate and select:** For each feed, the app checks for timestamped
   readings, selects the latest item, and reads `pm25_one_hourly` for PM2.5
   and `psi_twenty_four_hourly` for PSI. Invalid or missing data is reported
   rather than treated as a valid reading.
4. **Present:** The selected region's 1-hour PM2.5 value and activity-guidance
   band drive the event-planning check. The 24-hour PSI value and band remain
   available as a separate overview.
"""
)

st.header("How the PM2.5 activity guidance works")
st.markdown(
    """
- The user selects an event region and setting. The selected region's
  1-hour PM2.5 reading is assigned to one of four activity-guidance bands:
  Normal (0-55 µg/m³), Elevated (56-150 µg/m³), High (151-250 µg/m³), or
  Very High (above 250 µg/m³).
- Normal: all persons can continue with their activities.
- Elevated: healthy persons should reduce strenuous outdoor activities;
  vulnerable persons should avoid strenuous outdoor activities.
- High: healthy persons should avoid strenuous outdoor activities; vulnerable
  persons should avoid all outdoor activities.
- Very High: healthy persons should minimise all outdoor activities;
  vulnerable persons should continue to avoid all outdoor activities.
- These bands provide activity guidance, not an automatic event-cancellation
  decision. The dashboard also displays the 24-hour PSI snapshot separately.
- PSI bands are assigned by the dashboard: 0-50 Good, 51-100 Moderate,
  101-200 Unhealthy, 201-300 Very unhealthy, and above 300 Hazardous.
- If a feed or selected regional reading is unavailable, the dashboard reports
  the problem and does not show guidance for that unavailable reading.
"""
)

st.header("Implementation and limitations")
st.markdown(
    """
- The interface is built with Streamlit. PSI data is fetched with Python's
  standard-library HTTP and JSON tools; both feeds are fetched independently.
- The **Ask Clarity** page uses OpenAI embeddings to retrieve excerpts from a
  small, curated knowledge base and an OpenAI model to draft source-cited
  explanations. It does not use the assistant to fetch live readings or
  calculate PM2.5/PSI bands. Questions are sent to OpenAI; do not enter
  personal or sensitive information.
- The app uses one shared password stored as `app_password` in Streamlit
  secrets. Password comparison uses a constant-time comparison.
- Event inputs are handled by Streamlit widgets; this app code does not store
  event details in a database.
- The dashboard is a live snapshot, not a forecast. API readings can change,
  and upstream service availability can affect refreshes. Follow official NEA
  advisories and organizational policy; the activity bands are not universal
  event-cancellation rules.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
