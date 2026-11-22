import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

import folium
import streamlit as st
from streamlit_folium import st_folium

from app_common import EDUCATIONAL_DISCLAIMER, require_password
from event_location import REGION_REFERENCE_POINTS, geocode_address, nearest_region


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

pending_region = st.session_state.pop("pending_event_region", None)
if pending_region in REGIONS:
    st.session_state["event_region"] = pending_region
if st.session_state.pop("clear_event_address", False):
    st.session_state["event_address"] = ""
location_notice = st.session_state.pop("event_location_notice", None)
location_notice_type = st.session_state.pop("event_location_notice_type", "info")
st.session_state.setdefault("event_map_revision", 0)

with st.sidebar:
    st.header("Event settings")
    activity_type = st.selectbox(
        "Event setting",
        ["Outdoor", "Mixed indoor and outdoor", "Indoor"],
    )
    if st.button("Refresh live readings", use_container_width=True):
        fetch_psi.clear()
        fetch_pm25.clear()
        st.rerun()

with st.container(border=True):
    st.subheader("Event location")
    st.caption(
        "Search a Singapore address or click the map. The assigned region is "
        "an estimate based on the nearest data.gov.sg regional reference point; "
        "confirm or change it below."
    )
    location_column, map_column = st.columns([0.85, 1.15], gap="medium")
    with location_column:
        selected_region = st.selectbox(
            "Air-quality region",
            list(REGIONS),
            key="event_region",
        )
        if location_notice:
            if location_notice_type == "warning":
                st.warning(location_notice)
            else:
                st.info(location_notice)
        with st.form("event_address_lookup"):
            event_address = st.text_input(
                "Event address in Singapore",
                key="event_address",
                placeholder="e.g. 1 Marina Boulevard, Singapore",
            )
            address_submitted = st.form_submit_button("Find approximate region")

        st.caption(
            "Submitting an address sends it to OpenStreetMap's public "
            "Nominatim geocoder. Avoid sensitive addresses; only the region "
            "selection is needed for this dashboard."
        )
        st.markdown(
            "[Geocoding by Nominatim](https://nominatim.openstreetmap.org/) · "
            "© OpenStreetMap contributors"
        )
        if address_submitted:
            if not event_address.strip():
                st.warning("Enter an address to search.")
            else:
                try:
                    with st.spinner("Looking up the address…"):
                        place = geocode_address(event_address)
                except (URLError, TimeoutError) as error:
                    st.error(
                        "Could not reach the address lookup service. Try again "
                        "or choose a region manually."
                    )
                except (json.JSONDecodeError, ValueError) as error:
                    st.error(f"Could not look up that address: {error}")
                else:
                    if place is None:
                        st.warning(
                            "No Singapore location was found. Check the address "
                            "or choose a region manually."
                        )
                    else:
                        address_region = nearest_region(*place)
                        if address_region is None:
                            st.warning(
                                "The address could not be matched to a Singapore "
                                "region. Choose a region manually."
                            )
                        else:
                            st.session_state["pending_event_region"] = address_region
                            st.session_state["clear_event_address"] = True
                            st.session_state["event_location_notice"] = (
                                f"Approximate match: {address_region}. "
                                "Please confirm the region selection."
                            )
                            st.session_state["event_location_notice_type"] = "info"
                            st.session_state["event_map_revision"] += 1
                            st.rerun()

    with map_column:
        region_map = folium.Map(
            location=(1.35735, 103.82),
            zoom_start=10,
            control_scale=True,
        )
        for region, coordinates in REGION_REFERENCE_POINTS.items():
            folium.Marker(
                location=coordinates,
                tooltip=f"{region} region",
                popup=f"{region} region reference point",
                icon=folium.Icon(
                    color="blue" if region == selected_region else "cadetblue",
                    icon="map-marker",
                ),
            ).add_to(region_map)

        map_result = st_folium(
            region_map,
            key=f"event_region_map_{st.session_state['event_map_revision']}",
            height=360,
            use_container_width=True,
            returned_objects=["last_clicked", "last_object_clicked"],
        )
        clicked_point = None
        if isinstance(map_result, dict):
            clicked_point = map_result.get("last_clicked") or map_result.get(
                "last_object_clicked"
            )
        if isinstance(clicked_point, dict):
            latitude = clicked_point.get("lat")
            longitude = clicked_point.get("lng")
            if isinstance(latitude, (int, float)) and isinstance(
                longitude, (int, float)
            ):
                map_region = nearest_region(latitude, longitude)
                if map_region is None:
                    st.session_state["event_location_notice"] = (
                        "Click within Singapore to choose a region."
                    )
                    st.session_state["event_location_notice_type"] = "warning"
                else:
                    st.session_state["event_location_notice"] = (
                        f"Approximate map selection: {map_region}. "
                        "Please confirm the region selection."
                    )
                    st.session_state["event_location_notice_type"] = "info"
                    st.session_state["pending_event_region"] = map_region
                st.session_state["event_map_revision"] += 1
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
        st.caption(
            "Guidance wording: reduce = do less; minimise = do as little as "
            "possible; avoid = do not do the specified activity."
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
