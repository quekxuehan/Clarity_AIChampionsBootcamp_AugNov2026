import json
from html import escape
from datetime import date, datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

import folium
import streamlit as st
from streamlit_folium import st_folium

from app_common import EDUCATIONAL_DISCLAIMER, require_password
from event_location import REGION_REFERENCE_POINTS, geocode_address, nearest_region
from event_planning import build_event_assessment, threshold_status
from event_store import EventPlanStore, plan_checklist_progress, plan_handover_status


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


def pm25_color(value: int) -> str:
    if value <= 55:
        return "#16826d"
    if value <= 150:
        return "#b7791f"
    if value <= 250:
        return "#c75a14"
    return "#b42318"


def freshness_label(updated_at: datetime) -> str:
    now = datetime.now(updated_at.tzinfo) if updated_at.tzinfo else datetime.now()
    age_minutes = max(0, int((now - updated_at).total_seconds() // 60))
    if age_minutes < 1:
        return "Updated just now"
    if age_minutes < 60:
        return f"Updated {age_minutes} min ago"
    age_hours = age_minutes // 60
    return f"Updated {age_hours} hr ago"


def freshness_is_stale(updated_at: datetime | None) -> bool:
    if updated_at is None:
        return True
    now = datetime.now(updated_at.tzinfo) if updated_at.tzinfo else datetime.now()
    return (now - updated_at).total_seconds() > 3600


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

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background: #f6f8fb;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e7edf4;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #526175;
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #e5ebf2 !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 18px rgba(28, 44, 69, 0.05);
    }
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #edf1f6;
        border-radius: 12px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #e7edf4;
        border-radius: 12px;
        overflow: hidden;
    }
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 9px;
        min-height: 2.65rem;
        border: 1px solid #dbe4ee;
        box-shadow: none;
    }
    .stButton > button[kind="primary"] {
        border: 0;
    }
    .clarity-status-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.25rem 0 1.25rem;
    }
    .clarity-status-card {
        background: #ffffff;
        border: 1px solid #e5ebf2;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        min-height: 92px;
    }
    .clarity-status-card span {
        display: block;
        color: #718096;
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .clarity-status-card strong {
        color: #1f2d3d;
        font-size: 1.05rem;
    }
    .clarity-freshness {
        color: #16826d;
        font-size: 0.78rem;
        margin-top: 0.25rem;
    }
    .clarity-freshness.stale {
        color: #b7791f;
    }
    .clarity-plan-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.5rem 0 0.9rem;
    }
    .clarity-plan-card {
        background: #ffffff;
        border: 1px solid #e5ebf2;
        border-radius: 12px;
        padding: 0.9rem;
        min-height: 170px;
    }
    .clarity-plan-card strong {
        color: #1f2d3d;
        display: block;
        font-size: 1rem;
        margin-bottom: 0.45rem;
    }
    .clarity-plan-meta {
        color: #526175;
        font-size: 0.82rem;
        line-height: 1.55;
    }
    .clarity-plan-status {
        display: inline-block;
        border-radius: 999px;
        background: #edf7f4;
        color: #16826d;
        font-size: 0.75rem;
        font-weight: 700;
        margin-top: 0.55rem;
        padding: 0.25rem 0.55rem;
    }
    .clarity-plan-status.warning {
        background: #fff7e8;
        color: #975a16;
    }
    .clarity-plan-status.neutral {
        background: #f1f4f8;
        color: #526175;
    }
    @media (max-width: 900px) {
        .clarity-status-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .clarity-plan-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .block-container {
            max-width: 100%;
            padding: 1rem 0.75rem 2rem;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    @media (max-width: 600px) {
        .clarity-status-strip,
        .clarity-plan-grid {
            grid-template-columns: 1fr;
        }
        .clarity-status-card,
        .clarity-plan-card {
            min-height: auto;
        }
        [data-testid="stTitle"] h1 {
            font-size: 1.85rem;
        }
        .stButton > button,
        .stDownloadButton > button {
            width: 100%;
        }
        [data-testid="stDataFrame"] {
            max-width: calc(100vw - 2rem);
        }
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] > div,
    [data-testid="stDateInput"] > div,
    [data-testid="stNumberInput"] > div {
        border-radius: 9px;
    }
    hr {
        border-color: #edf1f6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

title_column, refresh_column = st.columns([0.78, 0.22], vertical_alignment="center")
with title_column:
    st.title("Clarity SG")
    st.markdown(
        "Singapore air-quality planning for events, with live readings, "
        "practical checklists, and saved plans."
    )
with refresh_column:
    if st.button("Refresh readings", use_container_width=True):
        fetch_psi.clear()
        fetch_pm25.clear()
        st.rerun()

pending_region = st.session_state.pop("pending_event_region", None)
if pending_region in REGIONS:
    st.session_state["event_region"] = pending_region
if st.session_state.pop("clear_event_address", False):
    st.session_state["event_address"] = ""
location_notice = st.session_state.pop("event_location_notice", None)
location_notice_type = st.session_state.pop("event_location_notice_type", "info")
st.session_state.setdefault("event_map_revision", 0)

with st.sidebar:
    st.header("Event details")
    with st.expander("Plan information", expanded=True):
        activity_type = st.selectbox(
            "Event setting",
            ["Outdoor", "Mixed indoor and outdoor", "Indoor"],
            key="event_setting",
        )
        event_name = st.text_input(
            "Event name",
            placeholder="Required for saving",
            key="event_name",
        )
        event_date = st.date_input("Event date", value=date.today(), key="event_date")
        duration_hours = st.number_input(
            "Expected duration (hours)",
            min_value=0.5,
            max_value=72.0,
            value=4.0,
            step=0.5,
            key="event_duration",
        )
    with st.expander("Exposure profile", expanded=True):
        activity_intensity = st.selectbox(
            "Highest activity intensity",
            ["Low", "Moderate", "Strenuous"],
            key="event_intensity",
        )
        attendee_mix = st.selectbox(
            "Attendee mix",
            ["Healthy adults", "Mixed or unknown", "Vulnerable attendees"],
            key="event_attendee_mix",
        )

with st.container(border=True):
    st.subheader("Event location")
    st.caption(
        "Choose a region manually, search an address, or click the map. "
        "Selections are estimates based on regional reference points."
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
current_pm25 = None
current_psi = None
pm25_updated_at = None
psi_updated_at = None
if pm25_snapshot is not None:
    pm25_readings = pm25_snapshot["readings"]
    pm25_updated_at = pm25_snapshot["timestamp"]
    selected_pm25 = pm25_readings.get(region_key)
    if isinstance(selected_pm25, (int, float)) and not isinstance(selected_pm25, bool):
        selected_pm25 = int(selected_pm25)
        current_pm25 = selected_pm25
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
        st.subheader("Regional comparison")
        if pm25_rows:
            comparison_columns = st.columns(len(pm25_rows))
            for column, row in zip(comparison_columns, sorted(pm25_rows, key=lambda item: item["Region"])):
                band_value = row["Band"]
                value = row["1-hour PM2.5 (µg/m³)"]
                band_color = pm25_color(value)
                with column:
                    st.markdown(
                        f"""
                        <div class="clarity-status-card">
                          <span>{row["Region"]}</span>
                          <strong style="color:{band_color}">{value} µg/m³</strong>
                          <div style="color:{band_color};font-size:0.78rem;margin-top:0.25rem;">{band_value}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            with st.expander("View full regional data"):
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

if psi_snapshot is not None:
    psi_readings = psi_snapshot["readings"]
    psi_updated_at = psi_snapshot["timestamp"]
    selected_psi = psi_readings.get(region_key)
    if isinstance(selected_psi, (int, float)) and not isinstance(selected_psi, bool):
        current_psi = int(selected_psi)

pm25_badge = pm25_band(current_pm25) if current_pm25 is not None else "Unavailable"
pm25_badge_color = pm25_color(current_pm25) if current_pm25 is not None else "#718096"
pm25_freshness = (
    freshness_label(pm25_updated_at)
    if pm25_updated_at is not None
    else "Live feed unavailable"
)
psi_freshness = (
    freshness_label(psi_updated_at)
    if psi_updated_at is not None
    else "Live feed unavailable"
)
st.markdown(
    f"""
    <div class="clarity-status-strip">
      <div class="clarity-status-card"><span>Selected region</span><strong>{selected_region}</strong></div>
      <div class="clarity-status-card"><span>1-hour PM2.5</span><strong style="color:{pm25_badge_color}">{current_pm25 if current_pm25 is not None else '—'} µg/m³</strong><div class="{'clarity-freshness stale' if freshness_is_stale(pm25_updated_at) else 'clarity-freshness'}">{pm25_freshness}</div></div>
      <div class="clarity-status-card"><span>24-hour PSI</span><strong>{current_psi if current_psi is not None else '—'}</strong><div class="clarity-freshness">{psi_freshness}</div></div>
      <div class="clarity-status-card"><span>PM2.5 band</span><strong style="color:{pm25_badge_color}">{pm25_badge}</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Event planning assessment")
    assessment = build_event_assessment(
        pm25_value=current_pm25,
        setting=activity_type,
        intensity=activity_intensity,
        attendee_mix=attendee_mix,
        duration_hours=float(duration_hours),
        event_date=event_date,
        today=date.today(),
    )
    level_column, summary_column = st.columns([0.28, 0.72])
    level_column.metric("Assessment level", assessment.level)
    summary_column.markdown(f"**{assessment.summary}**")

    st.session_state.setdefault("event_safety_owner", "")
    st.session_state.setdefault("event_threshold", "High (151 µg/m³)")
    st.session_state.setdefault("event_handover_note", "")
    st.session_state.setdefault("event_next_check", "")

    completed_actions = sum(
        1
        for index in range(len(assessment.actions))
        if st.session_state.get(f"assessment_action_{index}", False)
    )
    progress = completed_actions / len(assessment.actions) if assessment.actions else 0
    st.progress(progress, text=f"{completed_actions} of {len(assessment.actions)} checklist items complete")

    with st.expander("Handover and threshold settings", expanded=False):
        control_column, alert_column = st.columns(2)
        with control_column:
            st.text_input("Safety lead / owner", key="event_safety_owner")
            st.text_input(
                "Next planned check",
                key="event_next_check",
                placeholder="e.g. 22 Nov 2026, 5:00 PM",
            )
        with alert_column:
            st.selectbox(
                "PM2.5 alert threshold",
                [
                    "Off",
                    "Elevated (56 µg/m³)",
                    "High (151 µg/m³)",
                    "Very High (251 µg/m³)",
                ],
                key="event_threshold",
            )
            alert_status = threshold_status(current_pm25, st.session_state["event_threshold"])
            if alert_status.startswith("ALERT"):
                st.error(alert_status)
            elif alert_status.startswith("Below"):
                st.success(alert_status)
            else:
                st.info(alert_status)
        st.text_area("Handover / shift notes", key="event_handover_note")

    st.markdown("**Action checklist**")
    checklist_column, guidance_column = st.columns([0.68, 0.32], gap="medium")
    with checklist_column:
        for index, action in enumerate(assessment.actions):
            st.checkbox(action, key=f"assessment_action_{index}")
    with guidance_column:
        st.markdown(
            """
            <div class="clarity-status-card">
              <span>Planning note</span>
              <strong>Live conditions, not a forecast</strong>
              <div style="color:#526175;font-size:0.88rem;margin-top:0.45rem;">
                Recheck close to the event and use official NEA advice for decisions.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Saved event plans", expanded=bool(event_name.strip())):
        plan_store = EventPlanStore()
        saved_plans = plan_store.list_plans()
        save_column, delete_column = st.columns([0.72, 0.28])
        with save_column:
            if st.button("Save / update", type="primary", use_container_width=True):
                checklist_state = {
                    str(index): st.session_state.get(f"assessment_action_{index}", False)
                    for index in range(len(assessment.actions))
                }
                plan_data = {
                    "event_name": event_name,
                    "event_date": event_date.isoformat(),
                    "region": selected_region,
                    "setting": activity_type,
                    "duration_hours": float(duration_hours),
                    "activity_intensity": activity_intensity,
                    "attendee_mix": attendee_mix,
                    "alert_threshold": st.session_state["event_threshold"],
                    "safety_owner": st.session_state["event_safety_owner"],
                    "next_check": st.session_state["event_next_check"],
                    "handover_note": st.session_state["event_handover_note"],
                    "checklist": checklist_state,
                }
                try:
                    plan_store.save(event_name, plan_data)
                except ValueError as error:
                    st.warning(str(error))
                else:
                    st.success("Event plan saved locally.")
                    st.rerun()
        with delete_column:
            st.session_state.setdefault("confirm_delete_plan", None)

        if not saved_plans:
            st.caption("No saved plans yet.")
        else:
            for plan in saved_plans:
                completed, total = plan_checklist_progress(plan)
                progress_percent = int(completed / total * 100) if total else 0
                handover_status = plan_handover_status(plan)
                status_class = (
                    "neutral"
                    if handover_status == "Not handed over"
                    else "warning"
                    if handover_status == "Needs handover details"
                    else ""
                )
                plan_data = plan.data
                card_name = escape(str(plan.name))
                card_date = escape(str(plan_data.get("event_date", "Date not set")))
                card_region = escape(str(plan_data.get("region", "Region not set")))
                card_owner = escape(str(plan_data.get("safety_owner", "Not assigned")))
                card_next_check = escape(str(plan_data.get("next_check", "Not set")))
                card_threshold = escape(str(plan_data.get("alert_threshold", "Off")))
                st.markdown(
                    f"""
                    <div class="clarity-plan-card">
                      <strong>{card_name}</strong>
                      <div class="clarity-plan-meta">
                        {card_date} · {card_region}<br>
                        Owner: {card_owner}<br>
                        Next check: {card_next_check}<br>
                        Progress: {completed}/{total} · {progress_percent}%<br>
                        Threshold: {card_threshold}
                      </div>
                      <span class="clarity-plan-status {status_class}">{handover_status}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                card_column, delete_card_column = st.columns([0.72, 0.28])
                with card_column:
                    if st.button("Load", key=f"load_plan_{plan.id}", use_container_width=True):
                        data = plan.data
                        st.session_state["event_name"] = data.get("event_name", plan.name)
                        st.session_state["event_date"] = date.fromisoformat(
                            data.get("event_date", date.today().isoformat())
                        )
                        st.session_state["event_region"] = data.get("region", selected_region)
                        st.session_state["event_setting"] = data.get("setting", "Outdoor")
                        st.session_state["event_duration"] = float(data.get("duration_hours", 4))
                        st.session_state["event_intensity"] = data.get(
                            "activity_intensity", "Low"
                        )
                        st.session_state["event_attendee_mix"] = data.get(
                            "attendee_mix", "Healthy adults"
                        )
                        st.session_state["event_threshold"] = data.get(
                            "alert_threshold", "Off"
                        )
                        st.session_state["event_safety_owner"] = data.get("safety_owner", "")
                        st.session_state["event_next_check"] = data.get("next_check", "")
                        st.session_state["event_handover_note"] = data.get("handover_note", "")
                        for index, checked in data.get("checklist", {}).items():
                            st.session_state[f"assessment_action_{index}"] = bool(checked)
                        st.rerun()
                with delete_card_column:
                    if st.button("Delete", key=f"delete_plan_{plan.id}", use_container_width=True):
                        st.session_state["confirm_delete_plan"] = plan.id

                if st.session_state["confirm_delete_plan"] == plan.id:
                    st.warning(f'Delete "{plan.name}"?')
                    confirm_column, cancel_column = st.columns(2)
                    with confirm_column:
                        if st.button("Confirm", key=f"confirm_delete_{plan.id}", use_container_width=True):
                            plan_store.delete(plan.id)
                            st.session_state["confirm_delete_plan"] = None
                            st.success("Saved event plan deleted.")
                            st.rerun()
                    with cancel_column:
                        if st.button("Cancel", key=f"cancel_delete_{plan.id}", use_container_width=True):
                            st.session_state["confirm_delete_plan"] = None

    st.caption(
        "This is an operational checklist based on the app's PM2.5 bands, "
        "not an official advisory or a decision to cancel, modify, or proceed "
        "with an event."
    )

    assessment_lines = [
        f"# Event planning assessment: {event_name.strip() or 'Unnamed event'}",
        "",
        f"- Date: {event_date.isoformat()}",
        f"- Region: {selected_region}",
        f"- Setting: {activity_type}",
        f"- Duration: {duration_hours:g} hours",
        f"- Activity intensity: {activity_intensity}",
        f"- Attendee mix: {attendee_mix}",
        f"- Assessment: {assessment.level}",
        f"- Safety lead: {st.session_state['event_safety_owner'] or 'Not assigned'}",
        f"- Next check: {st.session_state['event_next_check'] or 'Not set'}",
        f"- Alert threshold: {st.session_state['event_threshold']}",
        (
            f"- Current 1-hour PM2.5: {current_pm25} µg/m³"
            if current_pm25 is not None
            else "- Current 1-hour PM2.5: unavailable"
        ),
        "",
        assessment.summary,
        "",
        "## Checklist",
    ]
    assessment_lines.extend(
        (
            "- [x] " if st.session_state.get(f"assessment_action_{index}", False)
            else "- [ ] "
        ) + action
        for index, action in enumerate(assessment.actions)
    )
    assessment_lines.extend(
        [
            "",
            "This checklist is not an official advisory or event decision.",
            "Consult NEA advisories and the organisation's event policy.",
        ]
    )
    st.download_button(
        "Download event checklist",
        data="\n".join(assessment_lines),
        file_name="clarity-event-checklist.md",
        mime="text/markdown",
        use_container_width=True,
    )

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
        with st.expander("View PSI by region"):
            st.dataframe(
                sorted(psi_rows, key=lambda row: row["24-hour PSI"], reverse=True),
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("The live feed did not include regional PSI readings.")

with st.expander("Planning limitations and source notes"):
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
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/managing-haze)"
)
st.caption(EDUCATIONAL_DISCLAIMER)
