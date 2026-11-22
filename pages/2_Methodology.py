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
    "1-hour PM2.5 and 24-hour PSI data, how its activity-guidance bands are "
    "selected, and how Ask Clarity answers questions using retrieval-augmented "
    "generation (RAG)."
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

st.header("Event location selection")
st.markdown(
    """
- The map displays one reference point for each data.gov.sg air-quality
  region. Clicking the map selects the nearest point using geographic
  distance.
- Address lookup sends the submitted Singapore address to
  [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/), limited to
  Singapore results. Requests are rate-limited to one per second.
- The interactive map loads OpenStreetMap tiles in the browser; map tiles and
  address geocoding are separate from the data.gov.sg air-quality feeds.
- The five reference points are not region-boundary polygons. Map and address
  matching are approximate; users can confirm or change the region with the
  selector. The selected region determines which live reading is displayed.
- Do not submit a sensitive address.
"""
)

st.header("How the PM2.5 activity guidance works")
st.markdown(
    """
- The user selects an event setting and can select a region manually, click
  the map, or submit a Singapore address for an approximate region suggestion.
  The selected region's 1-hour PM2.5 reading is assigned to one of four
  activity-guidance bands:
  Normal (0-55 µg/m³), Elevated (56-150 µg/m³), High (151-250 µg/m³), or
  Very High (above 250 µg/m³).
- Normal: all persons can continue with their activities.
- Elevated: healthy persons should reduce strenuous outdoor activities;
  vulnerable persons should avoid strenuous outdoor activities.
- High: healthy persons should avoid strenuous outdoor activities; vulnerable
  persons should avoid all outdoor activities.
- Very High: healthy persons should minimise all outdoor activities;
  vulnerable persons should avoid all outdoor activities.
- In this guidance, **reduce** means do less of the specified activity;
  **minimise** means do as little as possible; and **avoid** means do not do
  the specified activity.
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
- **Ask Clarity RAG flow:**
  1. The app creates embeddings for its small, curated set of guidance and
     source-summary excerpts with OpenAI's `text-embedding-3-small` model.
     The resulting vector index is cached in the Streamlit process; it is
     not a persistent vector database.
  2. When a question is submitted, the app embeds it, ranks the excerpts by
     cosine similarity, and supplies the three closest excerpts to
     `gpt-4o-mini`.
  3. The model is instructed to answer only from those excerpts, cite them
     with source IDs, and return `NOT_FOUND` when the excerpts do not answer
     the question. The app displays an answer only when it contains valid
     citations to retrieved excerpts, then lists the cited sources and links
     where available.
- The RAG knowledge base is curated in the app; it does not crawl or
  continuously refresh external documents. Ask Clarity does not fetch live
  readings or calculate PM2.5/PSI bands. Those remain the dashboard's
  deterministic data flow described above.
- Questions and retrieved excerpts are sent to OpenAI for embeddings and
  answer generation. The API key is stored in Streamlit secrets; do not enter
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
