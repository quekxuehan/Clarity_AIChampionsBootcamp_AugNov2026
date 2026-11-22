import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(
    page_title="Methodology | ClaritySG",
    page_icon="🌫️",
    layout="wide",
)
require_password()

st.title("Methodology")
st.markdown(
    "This page describes how ClaritySG retrieves, validates, and presents "
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
   Only the feed relevant to the event date is requested. Each request has a
   10-second timeout and identifies the app with a `User-Agent` header.
2. **Cache:** Successful results from each feed are cached for five minutes to
   limit repeated requests while keeping the dashboard periodically refreshed.
3. **Validate and select:** For each feed, the app checks for timestamped
   readings, selects the latest item, and reads `pm25_one_hourly` for PM2.5
   and `psi_twenty_four_hourly` for PSI. Invalid or missing data is reported
   rather than treated as a valid reading.
4. **Select:** Today's events use the selected region's 1-hour PM2.5 value.
   Future events within 7 days use 24-hour PSI. Future events beyond 7 days
   use long-range planning guidance and no air-quality forecast.
5. **Present:** The event details appear in a numbered landing-page flow:
   event details, location, relevant reading, and assessment. The selected
   reading, category/band, region, freshness, and
   event-date context drive the assessment and recommended checklist.
"""
)

st.header("Event location selection")
st.markdown(
    """
- Users select one of five Singapore regions directly. This keeps the proof
  of concept simple and avoids collecting a venue address.
"""
)

st.header("How the PM2.5 activity guidance works")
st.markdown(
    """
The selected regional reading is mapped to a band, then combined with event
details:

| Reading | Bands used |
|---|---|
| 1-hour PM2.5 | Normal 0-55; Elevated 56-150; High 151-250; Very High above 250 µg/m³ |
| 24-hour PSI | Good 0-50; Moderate 51-100; Unhealthy 101-200; Very unhealthy 201-300; Hazardous above 300 |

**Assessment inputs:** event date, setting, duration, activity intensity,
attendee mix, and selected region.

**Assessment logic:** Today uses 1-hour PM2.5. Future events within 7 days
use 24-hour PSI. Beyond 7 days use long-range planning only and prompt an
event-day 1-hour PM2.5 recheck.

The app assigns Monitor/Prepare/Act/Urgent Review for PM2.5 or equivalent
PSI conditions, then generates up to five relevant actions. Missing readings
produce an unable-to-assess result rather than guidance.

**Meaning:** reduce = do less; minimise = do as little as possible;
avoid = do not perform the activity. Bands inform planning only and do not
automatically cancel an event or forecast future conditions.

**Saved plans:** Store the event details, personal notes, editable checklist,
and completion status. Plans can be loaded or deleted, and checklists can be
downloaded as Markdown.
"""
)

st.header("Implementation and limitations")
st.markdown(
    """
- The interface is built with Streamlit. The app fetches PSI or PM2.5 based on
  the event date, using Python's standard-library HTTP and JSON tools.
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
  `.data/event_plans.sqlite3`. Saved plans include event settings,
  personal follow-up notes, and checklist
  status. Plans are filtered by a browser cookie and can be administered with
  a separate `admin_password`. Browser identity is not a strong security boundary;
  the database is excluded from Git and should not contain sensitive personal
  information. Data may be lost if the hosting environment replaces local storage.
- The dashboard is a live snapshot, not a forecast. API readings can change,
  and upstream service availability can affect refreshes. Follow official NEA
  advisories and organizational policy; the activity bands are not universal
  event-cancellation rules.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
