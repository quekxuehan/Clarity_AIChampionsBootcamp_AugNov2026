import hmac
import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


PSI_API_URL = "https://api-open.data.gov.sg/v2/real-time/api/psi"
REGIONS = {
    "Central": "central",
    "East": "east",
    "North": "north",
    "South": "south",
    "West": "west",
}


def psi_category(value: int) -> str:
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very unhealthy"
    return "Hazardous"


@st.cache_data(ttl=300)
def fetch_psi() -> dict:
    request = Request(
        PSI_API_URL,
        headers={"User-Agent": "ClaritySG/1.0"},
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read())

    if not isinstance(payload, dict):
        raise ValueError("The live PSI feed returned an unexpected response.")
    data = payload.get("data")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("The live PSI feed did not contain any readings.")
    if any(
        not isinstance(item, dict) or not isinstance(item.get("timestamp"), str)
        for item in items
    ):
        raise ValueError("The live PSI feed returned an invalid reading.")

    latest = max(
        items,
        key=lambda item: datetime.fromisoformat(item["timestamp"]),
    )
    item_readings = latest.get("readings")
    readings = (
        item_readings.get("psi_twenty_four_hourly")
        if isinstance(item_readings, dict)
        else None
    )
    if not isinstance(readings, dict):
        raise ValueError("The live PSI feed is missing 24-hour PSI readings.")

    timestamp = datetime.fromisoformat(latest["timestamp"])
    return {"readings": readings, "timestamp": timestamp}


def require_password() -> None:
    try:
        app_password = st.secrets["app_password"]
    except (KeyError, StreamlitSecretNotFoundError):
        st.error(
            "The app password is not configured. Add `app_password` to "
            "`.streamlit/secrets.toml` or your hosting provider's secrets."
        )
        st.stop()

    if not isinstance(app_password, str) or not app_password:
        st.error("The configured app password must be a non-empty string.")
        st.stop()

    if st.session_state.get("authenticated") is True:
        return

    st.title("🌫️ Clarity SG")
    st.subheader("Password required")
    with st.form("password_login"):
        entered_password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock app")

    if submitted:
        if hmac.compare_digest(entered_password, app_password):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Incorrect password. Try again.")

    st.stop()


st.set_page_config(page_title="Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("🌫️ Clarity SG")
st.markdown(
    "Check Singapore's live air quality by region and compare it with "
    "your event's own PSI action threshold."
)

with st.sidebar:
    st.header("Event settings")
    if st.button("Log out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

    event_name = st.text_input("Event name", value="My event")
    activity_type = st.selectbox(
        "Event setting",
        ["Outdoor", "Mixed indoor and outdoor", "Indoor"],
    )
    selected_region = st.selectbox("Event region", list(REGIONS))
    action_threshold = st.slider(
        "Consider cancelling at PSI",
        min_value=51,
        max_value=300,
        value=101,
        help=(
            "Set this to your organisation's action threshold. The default "
            "starts at the NEA 'Unhealthy' band; it is not a universal "
            "cancellation rule."
        ),
    )
    if st.button("Refresh live readings", use_container_width=True):
        fetch_psi.clear()
        st.rerun()

try:
    with st.spinner("Loading Singapore's latest PSI readings…"):
        snapshot = fetch_psi()
except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as error:
    st.error(f"Could not load live PSI data: {error}")
    st.caption("Check your connection and try refreshing. No recommendation was made.")
    st.stop()

readings = snapshot["readings"]
region_key = REGIONS[selected_region]
selected_psi = readings.get(region_key)
if not isinstance(selected_psi, (int, float)):
    st.error(f"No current PSI reading is available for the {selected_region} region.")
    st.caption("No recommendation was made because the selected reading is unavailable.")
    st.stop()

selected_psi = int(selected_psi)
category = psi_category(selected_psi)
updated_at = snapshot["timestamp"].strftime("%d %b %Y, %I:%M %p %Z")
st.caption(f"Latest 24-hour PSI reading: {updated_at} · Singapore time")

metric_column, category_column, action_column = st.columns(3)
metric_column.metric(f"{selected_region} region · 24-hour PSI", selected_psi)
category_column.metric("NEA PSI band", category)

event_label = event_name.strip() or "Your event"
if selected_psi >= action_threshold:
    action_column.metric("Event action check", "Threshold reached")
    st.error(
        f"**Review {event_label}'s outdoor plans.** The {selected_region} "
        f"region's 24-hour PSI is {selected_psi}, at or above your action "
        f"threshold of {action_threshold}. Consider your event plan, "
        "attendee needs, and official health advisories before deciding."
    )
elif selected_psi >= 101:
    action_column.metric("Event action check", "Use caution")
    if activity_type == "Indoor":
        st.warning(
            f"The PSI is {selected_psi} ({category}), below your configured "
            f"threshold of {action_threshold}. For an indoor event, check "
            "indoor air quality and official advisories."
        )
    else:
        st.warning(
            f"The PSI is {selected_psi} ({category}), below your configured "
            f"threshold of {action_threshold}. For an {activity_type.lower()} "
            "event, consider reducing strenuous outdoor activity and check "
            "official advisories."
        )
else:
    action_column.metric("Event action check", "Below your threshold")
    st.success(
        f"The selected region's PSI is below your configured threshold of "
        f"{action_threshold}. This is not a guarantee of safe conditions."
    )

st.subheader("Cross-reference all regions")
region_rows = []
for region, key in REGIONS.items():
    value = readings.get(key)
    if isinstance(value, (int, float)):
        value = int(value)
        region_rows.append(
            {"Region": region, "24-hour PSI": value, "PSI band": psi_category(value)}
        )

if region_rows:
    st.dataframe(
        sorted(region_rows, key=lambda row: row["24-hour PSI"], reverse=True),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("The live feed did not include regional readings.")

st.info(
    "This app reports the latest 24-hour PSI snapshot; it does not forecast "
    "conditions at a future event time. PSI bands and current air-quality "
    "readings can change. Recheck close to your event, consult Singapore's "
    "NEA advisories, and follow your organisation's safety policy. This tool "
    "does not automatically cancel events or provide medical advice."
)
st.markdown(
    "Source: [Singapore data.gov.sg live PSI API]"
    "(https://api-open.data.gov.sg/v2/real-time/api/psi) · "
    "[NEA air pollution information]"
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/psi)"
)
