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
(PSI) readings into one event-planning view. You can compare readings across
Central, East, North, South, and West Singapore, choose an approximate venue
region, and prepare for outdoor or indoor activities.

The app can create an operational checklist based on the event date, duration,
setting, activity level, and attendee mix. It does not forecast future
conditions, provide personalised medical advice, or decide whether an event
should be cancelled.
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
- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) is used to
  find approximate Singapore addresses. It does not provide air-quality data.
"""
)

st.header("What is included")
st.markdown(
    """
- Live PM2.5 and PSI readings with update timestamps.
- Clear PM2.5 bands and regional comparison cards.
- A summary showing the selected region, current readings, freshness, and
  PM2.5 category.
- Singapore address lookup and a clickable region map.
- Event Planning Assessment based on date, duration, setting, activity
  intensity, and attendee mix.
- A checklist that can be marked complete and downloaded as Markdown.
- Locally saved event plans with a safety lead, next check, threshold,
  handover notes, and checklist progress.
- Dashboard alerts at Elevated, High, or Very High thresholds. Alerts
  recalculate when readings refresh or a plan is loaded; they do not send
  email or push notifications.
- Ask Clarity, which retrieves relevant app guidance and official NEA
  information and shows source references.
- Password-protected access for the shared app.
"""
)

st.header("Choosing a location")
st.markdown(
    """
You can select a region directly, click the map, or enter a Singapore address.
Address lookup is sent to OpenStreetMap's public Nominatim service. The app
then matches the location to the nearest regional reference point.

These are planning estimates, not official region boundaries. Please confirm
the selected region before using the reading. Do not enter sensitive addresses.
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

Saved event plans use local SQLite storage. Plans are available to users of the
same app deployment, so they should not contain sensitive personal information.
"""
)

st.caption(EDUCATIONAL_DISCLAIMER)
