import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st
from app_common import EDUCATIONAL_DISCLAIMER, require_password


PSI_API_URL = "https://api-open.data.gov.sg/v2/real-time/api/psi"
PM25_API_URL = "https://api-open.data.gov.sg/v2/real-time/api/pm25"
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


def pm25_band(value: int) -> str:
    if value <= 55:
        return "Normal"
    if value <= 150:
        return "Elevated"
    if value <= 250:
        return "High"
    return "Very High"


def pm25_guidance(value: int) -> tuple[str, str | None]:
    if value <= 55:
        return "All persons can continue with their activities.", None
    if value <= 150:
        return (
            "Healthy persons should reduce strenuous outdoor activities.",
            "Vulnerable persons should avoid strenuous outdoor activities.",
        )
    if value <= 250:
        return (
            "Healthy persons should avoid strenuous outdoor activities.",
            "Vulnerable persons should avoid all outdoor activities.",
        )
    return (
        "Healthy persons should minimise all outdoor activities.",
        "Vulnerable persons should avoid all outdoor activities.",
    )


def fetch_readings(api_url: str, reading_key: str, pollutant: str) -> dict:
    request = Request(
        api_url,
        headers={"User-Agent": "ClaritySG/1.0"},
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read())

    if not isinstance(payload, dict):
        raise ValueError(f"The live {pollutant} feed returned an unexpected response.")
    data = payload.get("data")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError(f"The live {pollutant} feed did not contain any readings.")
    if any(
        not isinstance(item, dict) or not isinstance(item.get("timestamp"), str)
        for item in items
    ):
        raise ValueError(f"The live {pollutant} feed returned an invalid reading.")

    latest = max(
        items,
        key=lambda item: datetime.fromisoformat(item["timestamp"]),
    )
    item_readings = latest.get("readings")
    readings = (
        item_readings.get(reading_key)
        if isinstance(item_readings, dict)
        else None
    )
    if not isinstance(readings, dict):
        raise ValueError(f"The live {pollutant} feed is missing {reading_key} readings.")

    timestamp = datetime.fromisoformat(latest["timestamp"])
    return {"readings": readings, "timestamp": timestamp}


@st.cache_data(ttl=300)
def fetch_psi() -> dict:
    return fetch_readings(PSI_API_URL, "psi_twenty_four_hourly", "PSI")


@st.cache_data(ttl=300)
def fetch_pm25() -> dict:
    return fetch_readings(PM25_API_URL, "pm25_one_hourly", "PM2.5")


st.set_page_config(page_title="Clarity SG", page_icon="🌫️", layout="wide")
require_password()

st.title("🌫️ Clarity SG")
st.markdown(
    "Review Singapore's live 1-hour PM2.5 activity guidance for your event "
    "region, alongside the 24-hour PSI overview."
)

with st.sidebar:
    st.header("Event settings")
    activity_type = st.selectbox(
        "Event setting",
        ["Outdoor", "Mixed indoor and outdoor", "Indoor"],
    )
    selected_region = st.selectbox("Event region", list(REGIONS))
    if st.button("Refresh live readings", use_container_width=True):
        fetch_psi.clear()
        fetch_pm25.clear()
        st.rerun()

psi_snapshot = None
pm25_snapshot = None
with st.spinner("Loading Singapore's latest air-quality readings…"):
    try:
        snapshot = fetch_psi()
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as error:
        st.error(f"Could not load the 24-hour PSI overview: {error}")
    else:
        psi_snapshot = snapshot

    try:
        pm25_snapshot = fetch_pm25()
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as error:
        st.error(f"Could not load 1-hour PM2.5 data: {error}")
        st.caption(
            "Check your connection and try refreshing. No PM2.5 guidance was shown."
        )

region_key = REGIONS[selected_region]
if pm25_snapshot is not None:
    pm25_readings = pm25_snapshot["readings"]
    selected_pm25 = pm25_readings.get(region_key)
    if isinstance(selected_pm25, (int, float)) and not isinstance(selected_pm25, bool):
        selected_pm25 = int(selected_pm25)
        pm25_category = pm25_band(selected_pm25)
        updated_at = pm25_snapshot["timestamp"].strftime("%d %b %Y, %I:%M %p %Z")
        st.subheader("Event planning check · 1-hour PM2.5")
        metric_column, band_column = st.columns(2)
        metric_column.metric(
            f"{selected_region} region · 1-hour PM2.5",
            f"{selected_pm25} µg/m³",
        )
        band_column.metric("PM2.5 band", pm25_category)
        st.caption(f"Reading time: {updated_at} · Singapore time")

        healthy_guidance, vulnerable_guidance = pm25_guidance(selected_pm25)
        st.markdown(f"**{pm25_category} band guidance**")
        if vulnerable_guidance is None:
            st.write(healthy_guidance)
        else:
            st.write(f"Healthy persons: {healthy_guidance}")
            st.write(
                "Vulnerable persons (including the elderly, pregnant people, "
                "children, and people with chronic respiratory or heart "
                f"diseases): {vulnerable_guidance}"
            )
        if activity_type == "Indoor":
            st.info(
                "This guidance concerns outdoor activities. For an indoor "
                "event, also consider indoor air quality and official advisories."
            )
        else:
            st.info(
                "Use this activity guidance alongside your event setting, "
                "attendee needs, official advisories, and your organisation's "
                "event policy. It does not decide whether to cancel."
            )

        pm25_rows = []
        for region, key in REGIONS.items():
            value = pm25_readings.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = int(value)
                pm25_rows.append(
                    {
                        "Region": region,
                        "1-hour PM2.5 (µg/m³)": value,
                        "Band": pm25_band(value),
                    }
                )
        st.subheader("1-hour PM2.5 by region")
        if pm25_rows:
            st.dataframe(
                sorted(
                    pm25_rows,
                    key=lambda row: row["1-hour PM2.5 (µg/m³)"],
                    reverse=True,
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("The live feed did not include regional PM2.5 readings.")
    else:
        st.error(
            f"No current 1-hour PM2.5 reading is available for the "
            f"{selected_region} region."
        )
        st.caption("No PM2.5 guidance was shown because the reading is unavailable.")
else:
    st.info("The PM2.5 event-planning check is unavailable until readings load.")

st.subheader("24-hour PSI overview")
if psi_snapshot is not None:
    psi_readings = psi_snapshot["readings"]
    selected_psi = psi_readings.get(region_key)
    if isinstance(selected_psi, (int, float)) and not isinstance(selected_psi, bool):
        selected_psi = int(selected_psi)
        category = psi_category(selected_psi)
        updated_at = psi_snapshot["timestamp"].strftime("%d %b %Y, %I:%M %p %Z")
        metric_column, category_column = st.columns(2)
        metric_column.metric(f"{selected_region} region · 24-hour PSI", selected_psi)
        category_column.metric("PSI band", category)
        st.caption(f"Reading time: {updated_at} · Singapore time")
    else:
        st.warning(
            f"No current 24-hour PSI reading is available for the "
            f"{selected_region} region."
        )

    psi_rows = []
    for region, key in REGIONS.items():
        value = psi_readings.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = int(value)
            psi_rows.append(
                {"Region": region, "24-hour PSI": value, "PSI band": psi_category(value)}
            )
    if psi_rows:
        st.dataframe(
            sorted(psi_rows, key=lambda row: row["24-hour PSI"], reverse=True),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("The live feed did not include regional PSI readings.")

st.info(
    "The 1-hour PM2.5 guidance is a current snapshot, not a forecast for a "
    "future event time. Readings can change. Recheck close to your event, "
    "consult Singapore's NEA advisories, and follow your organisation's "
    "safety policy. This tool does not automatically cancel events or provide "
    "individual medical advice."
)
st.markdown(
    "Sources: [data.gov.sg live 1-hour PM2.5 API]"
    "(https://api-open.data.gov.sg/v2/real-time/api/pm25) · "
    "[data.gov.sg live PSI API]"
    "(https://api-open.data.gov.sg/v2/real-time/api/psi) · "
    "[NEA air pollution information]"
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/psi)"
)
st.caption(EDUCATIONAL_DISCLAIMER)
