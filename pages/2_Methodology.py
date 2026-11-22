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
   band drive the event-planning check. A status strip presents the region,
   live PM2.5, PSI, band, and data freshness. Regional comparison cards and
   detailed tables provide a deeper view.
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
- The Event Planning Assessment uses the same PM2.5 bands and adds event date,
  duration, setting, activity intensity, and attendee mix. It generates a
  practical checklist, including monitoring and fallback options. The
  assessment is deterministic, does not use the reading as a future forecast,
  and does not make a cancellation decision. A Markdown checklist can be
  downloaded for event-planning records.
- The PM2.5 threshold alert compares the selected region's current 1-hour
  reading with a saved Elevated (56 µg/m³), High (151 µg/m³), or Very High
  (251 µg/m³) threshold. It recalculates when readings are refreshed or a plan
  is loaded; it does not send notifications or monitor continuously.
- Saved-plan controls are grouped in an expandable section. The page also
  includes a checklist progress indicator, expandable handover and threshold
  settings, explicit delete confirmation, and a Markdown checklist export.
- Saved-plan cards derive checklist progress and handover status from stored
  plan fields. Responsive CSS changes status and plan cards to fewer columns
  on tablets and one column on mobile screens.
"""
)

st.header("Implementation and limitations")
st.markdown(
    """
- The interface is built with Streamlit. PSI data is fetched with Python's
  standard-library HTTP and JSON tools; both feeds are fetched independently.
- **Ask Clarity RAG flow:**
  1. On a question, the app fetches the NEA air-pollution FAQs and managing
     haze pages over HTTPS. Successful page content is cached for up to one
     hour; users can also request an immediate refresh. The retrieval corpus
     combines those pages with the app's curated guidance excerpts.
  2. The app creates embeddings for the corpus and caches the in-memory vector
     index. When a question is submitted, it embeds the question, ranks
     excerpts by cosine similarity, and supplies the three closest excerpts
     to `gpt-4o-mini`.
  3. The model is instructed to answer only from those excerpts, cite them
     with source IDs, and return `NOT_FOUND` when the excerpts do not answer
     the question. The app displays an answer only when it contains valid
     citations, lists the cited sources, and shows when the NEA pages were
     last fetched.
- Ask Clarity retrieves only the listed NEA pages; it does not crawl the
  wider web, fetch live readings, or calculate PM2.5/PSI bands. Current
  readings and deterministic bands remain in the dashboard.
- Questions and retrieved excerpts are sent to OpenAI for embeddings and
  answer generation. The API key is stored in Streamlit secrets; do not enter
  personal or sensitive information.
- The app uses one shared password stored as `app_password` in Streamlit
  secrets. Password comparison uses a constant-time comparison.
- Event plans are stored locally in an SQLite database at
  `.data/event_plans.sqlite3`. Saved plans include event settings, safety lead,
  next-check details, threshold selection, handover notes, and checklist
  status. The database is excluded from Git and should not contain sensitive
  personal information. It is shared across users of the same app deployment,
  and data may be lost if the hosting environment replaces local storage.
- The dashboard is a live snapshot, not a forecast. API readings can change,
  and upstream service availability can affect refreshes. Follow official NEA
  advisories and organizational policy; the activity bands are not universal
  event-cancellation rules.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
