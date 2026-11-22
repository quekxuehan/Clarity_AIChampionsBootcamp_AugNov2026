import streamlit as st

from app_common import EDUCATIONAL_DISCLAIMER, require_password


st.set_page_config(page_title="About Us | Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("About Us")
st.markdown(
    "Clarity SG is an educational air-quality planning prototype created by "
    "Quek Xue Han for the AI Champions Bootcamp (Aug-Nov 2026). It helps "
    "event planners understand live Singapore air-quality readings and turn "
    "them into practical planning checklists."
)

st.header("What Clarity SG helps you do")
st.markdown(
    """
Clarity SG brings live 1-hour PM2.5 and 24-hour Pollutant Standards Index
(PSI) readings into one event-planning view. You select a Central, East,
North, South, or West region and prepare for outdoor or indoor activities.

The app creates an operational checklist based on the event date, duration,
setting, activity level, and attendee mix. Events today use 1-hour PM2.5;
future events within 7 days use 24-hour PSI for near-term context. Events
beyond 7 days use long-range planning guidance and should be checked again
with 1-hour PM2.5 on the event day. The app does not forecast future conditions,
provide personalised medical advice, or decide whether an event should be
cancelled.
"""
)

st.header("Data sources")
st.markdown(
    """
- [data.gov.sg real-time PSI API](https://api-open.data.gov.sg/v2/real-time/api/psi)
  supplies 24-hour PSI readings and timestamps.
- [data.gov.sg real-time PM2.5 API](https://api-open.data.gov.sg/v2/real-time/api/pm25)
  supplies regional 1-hour PM2.5 readings and timestamps.
- [NEA haze management and air-pollution information](https://www.nea.gov.sg/our-services/pollution-control/air-pollution/managing-haze)
  provides official haze and air-pollution context.
"""
)

st.header("What is included")
st.markdown(
    """
- Only the reading relevant to the event date: 1-hour PM2.5 today or
  24-hour PSI for future events within 7 days.
- Clear PM2.5 and PSI bands.
- A dynamic assessment showing the relevant reading, freshness, region, and
  category for the selected event date.
- Event Planning Assessment based on date, duration, setting, activity
  intensity, and attendee mix.
- Up to five generated checklist actions that can be marked complete, edited, added to,
  deleted, and downloaded as Markdown.
- A recheck reminder for future and long-range events.
- Locally saved event plans with personal follow-up notes and checklist progress.
- Ask Clarity, which retrieves relevant app guidance and official NEA
  information and shows source references.
- Password-protected access for the shared app.
"""
)

st.header("Choosing a location")
st.markdown(
    """
Select the Central, East, North, South, or West region closest to the venue.
The region is a planning estimate, not an official boundary.
"""
)

st.header("Understanding PM2.5 guidance")
st.markdown(
    """
Clarity SG uses four PM2.5 bands:

- **Normal:** continue normal activities.
- **Elevated:** reduce strenuous outdoor activities.
- **High:** avoid strenuous outdoor activities.
- **Very High:** minimise outdoor activity and review whether outdoor components
  should proceed.

In the guidance:

- **Reduce** means do less.
- **Minimise** means do as little as possible.
- **Avoid** means do not do the activity.
"""
)

st.header("Ask Clarity and privacy")
st.markdown(
    """
Ask Clarity finds relevant excerpts in the app's guidance and NEA's
air-pollution FAQs and haze guidance pages. NEA pages are refreshed up to once
an hour or when you use the manual refresh button.

Ask Clarity uses OpenAI to prepare answers and sends questions and retrieved
excerpts to OpenAI for processing. It does not retrieve live readings or make
event decisions. Do not enter personal or sensitive information.

Saved event plans use local SQLite storage. Plans are separated by browser
identity, and this deployment also supports an admin password for authorised
administration. Browser identity and the shared app password are convenience
controls, not strong personal-security boundaries. Do not store sensitive
personal information.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
