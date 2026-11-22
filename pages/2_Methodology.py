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
    "PSI data, and how its event-threshold messages are selected."
)

st.header("Data flow")
st.markdown(
    """
1. **Request:** The dashboard sends an HTTPS GET request to the
   [data.gov.sg real-time PSI API](https://api-open.data.gov.sg/v2/real-time/api/psi).
   The request has a 10-second timeout and identifies the app with a
   `User-Agent` header.
2. **Cache:** Successful results are cached for five minutes to limit
   repeated requests while keeping the dashboard periodically refreshed.
3. **Validate:** The app checks that the response is a JSON object containing
   timestamped items and 24-hour PSI readings. Invalid or missing data is
   reported instead of being treated as a valid reading.
4. **Select the snapshot:** The app parses the timestamps and selects the
   latest item, then reads its `psi_twenty_four_hourly` values.
5. **Present:** The selected region's value, update time, PSI band, and the
   available values for all five regions are displayed.
"""
)

st.header("How the event check works")
st.markdown(
    """
- The user selects an event region and setting, then chooses a threshold
  between 51 and 300 PSI. The default is 101.
- The selected regional reading is compared with that threshold. At or above
  it, the dashboard asks the user to review the event plan. Below the
  configured threshold but at or above 101, it displays a caution message.
  Below 101, it says the reading is below the configured threshold.
- PSI bands are assigned by the dashboard: 0-50 Good, 51-100 Moderate,
  101-200 Unhealthy, 201-300 Very unhealthy, and above 300 Hazardous.
- If the feed or selected regional reading is unavailable, the dashboard
  reports the problem and makes no recommendation.
"""
)

st.header("Implementation and limitations")
st.markdown(
    """
- The interface is built with Streamlit. PSI data is fetched with Python's
  standard-library HTTP and JSON tools.
- The app uses one shared password stored as `app_password` in Streamlit
  secrets. Password comparison uses a constant-time comparison.
- Event inputs are handled by Streamlit widgets; this app code does not store
  event details in a database.
- The dashboard is a live snapshot, not a forecast. API readings can change,
  and upstream service availability can affect refreshes. Follow official NEA
  advisories and organizational policy; the displayed threshold is not a
  universal cancellation rule.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
