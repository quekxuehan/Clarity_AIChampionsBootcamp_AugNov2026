import json
import uuid
from html import escape
from datetime import date, datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st
from streamlit.components.v1 import html

from app_common import EDUCATIONAL_DISCLAIMER, require_admin_login, require_password
from event_planning import (
    FUTURE_PLANNING_HORIZON_DAYS,
    build_event_assessment,
    select_event_reading,
)
from event_store import EventPlanStore, plan_checklist_progress, plan_followup_status


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
is_admin = require_admin_login()

if "browser_owner_id" not in st.session_state:
    cookie_owner_id = getattr(st.context, "cookies", {}).get("clarity_owner_id")
    try:
        browser_owner_id = str(uuid.UUID(cookie_owner_id)) if cookie_owner_id else str(uuid.uuid4())
    except (TypeError, ValueError, AttributeError):
        browser_owner_id = str(uuid.uuid4())
    st.session_state["browser_owner_id"] = browser_owner_id

browser_owner_id = st.session_state["browser_owner_id"]
escaped_owner_id = json.dumps(browser_owner_id)
html(
    f"""
    <script>
      document.cookie = "clarity_owner_id={escaped_owner_id.strip('"')}; "
        + "Max-Age=31536000; Path=/; SameSite=Lax";
    </script>
    """,
    height=0,
)

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

with st.container(border=True):
    st.subheader("1. Event details")
    details_column, exposure_column = st.columns(2, gap="large")
    with details_column:
        event_name = st.text_input(
            "Event name",
            placeholder="Required for saving",
            key="event_name",
        )
        event_date = st.date_input(
            "Event date",
            value=date.today(),
            min_value=date.today(),
            key="event_date",
        )
        duration_hours = st.number_input(
            "Expected duration (hours)",
            min_value=0.5,
            max_value=72.0,
            value=4.0,
            step=0.5,
            key="event_duration",
        )
        activity_type = st.selectbox(
            "Event setting",
            ["Outdoor", "Mixed indoor and outdoor", "Indoor"],
            key="event_setting",
        )
    with exposure_column:
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

        today = date.today()
        if event_date == today:
            st.info("Planning mode: today — 1-hour PM2.5")
        elif event_date > today:
            days_until_event = (event_date - today).days
            if days_until_event <= FUTURE_PLANNING_HORIZON_DAYS:
                st.info(
                    f"Planning mode: 1–{FUTURE_PLANNING_HORIZON_DAYS} days — "
                    "24-hour PSI; recheck on event day"
                )
            else:
                st.warning(
                    "Planning mode: beyond 7 days — long-range guidance only. "
                    "Check 1-hour PM2.5 again on the event day."
                )
        else:
            st.info("Planning mode: past event — 24-hour PSI retrospective context")

with st.container(border=True):
    st.subheader("2. Event location")
    st.caption(
        "Choose the Singapore air-quality region closest to the event venue."
    )
    selected_region = st.selectbox(
        "Air-quality region",
        list(REGIONS),
        key="event_region",
    )

psi_snapshot = None
pm25_snapshot = None
today = date.today()
days_until_event = (event_date - today).days
needs_pm25 = event_date == today
needs_psi = 0 < days_until_event <= FUTURE_PLANNING_HORIZON_DAYS

with st.spinner("Loading the relevant Singapore air-quality reading…"):
    if needs_pm25:
        try:
            pm25_snapshot = fetch_pm25()
        except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as error:
            st.error(f"Could not load 1-hour PM2.5 data: {error}")
            st.caption(
                "Check your connection and try refreshing. No PM2.5 guidance was shown."
            )

    if needs_psi and event_date > today:
        try:
            psi_snapshot = fetch_psi()
        except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as error:
            st.error(f"Could not load the 24-hour PSI overview: {error}")

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
        current_pm25 = int(selected_pm25)

if psi_snapshot is not None:
    psi_readings = psi_snapshot["readings"]
    psi_updated_at = psi_snapshot["timestamp"]
    selected_psi = psi_readings.get(region_key)
    if isinstance(selected_psi, (int, float)) and not isinstance(selected_psi, bool):
        current_psi = int(selected_psi)

assessment_value, reading_kind = select_event_reading(
    event_date,
    date.today(),
    current_pm25,
    current_psi,
)

if event_date == date.today():
    reading_title = "Today's event · 1-hour PM2.5"
    reading_unit = "µg/m³"
    reading_updated_at = pm25_updated_at
elif event_date > date.today():
    if reading_kind == "Planning":
        reading_title = "Long-range event · planning context only"
        reading_unit = ""
        reading_updated_at = None
    else:
        reading_title = "Future event · 24-hour PSI"
        reading_unit = ""
        reading_updated_at = psi_updated_at
else:
    reading_title = "Past event · 24-hour PSI overview"
    reading_unit = ""
    reading_updated_at = psi_updated_at

reading_freshness = (
    freshness_label(reading_updated_at)
    if reading_updated_at is not None
    else "Reading unavailable"
)
reading_badge = (
    pm25_band(assessment_value)
    if reading_kind == "PM2.5" and assessment_value is not None
    else psi_category(assessment_value)
    if reading_kind == "PSI" and assessment_value is not None
    else "Unavailable"
)

with st.container(border=True):
    st.subheader(f"3. {reading_title}")
    value_column, region_column, update_column = st.columns(3)
    with value_column:
        st.metric(
            f"{reading_kind} reading",
            f"{assessment_value if assessment_value is not None else '—'}"
            f"{' ' + reading_unit if reading_unit else ''}",
        )
    with region_column:
        st.metric("Region", selected_region)
    with update_column:
        st.metric("Band / category", reading_badge)
        st.caption(reading_freshness)

    if event_date == date.today():
        st.caption("Uses the latest 1-hour PM2.5 reading because the event is today.")
    elif event_date > date.today():
        if reading_kind == "Planning":
            st.warning(
                f"This event is more than {FUTURE_PLANNING_HORIZON_DAYS} days away. "
                "Long-range air quality cannot be predicted reliably. "
                "Use this only for initial planning; check 1-hour PM2.5 again on the event day."
            )
        else:
            st.info(
                "Uses the latest 24-hour PSI only as near-future planning context. "
                "Check 1-hour PM2.5 again on the event day."
            )
    else:
        st.caption("Uses the 24-hour PSI overview only for retrospective planning.")

with st.container(border=True):
    st.subheader("4. Assessment and recommended actions")
    assessment = build_event_assessment(
        pm25_value=assessment_value,
        setting=activity_type,
        intensity=activity_intensity,
        attendee_mix=attendee_mix,
        duration_hours=float(duration_hours),
        event_date=event_date,
        today=date.today(),
        reading_kind=reading_kind,
    )
    level_column, summary_column = st.columns([0.28, 0.72])
    level_column.metric("Assessment level", assessment.level)
    summary_column.markdown(f"**{assessment.summary}**")

    st.session_state.setdefault("event_handover_note", "")

    checklist_source = (
        reading_kind,
        assessment_value,
        assessment.summary,
        *assessment.actions,
    )
    if (
        "event_checklist_source" not in st.session_state
        or st.session_state["event_checklist_source"] != checklist_source
        or "event_checklist_items" not in st.session_state
    ):
        st.session_state["event_checklist_source"] = checklist_source
        st.session_state["event_checklist_items"] = [
            {"text": action, "completed": False}
            for action in assessment.actions
        ]
        for index, item in enumerate(st.session_state["event_checklist_items"]):
            st.session_state[f"event_checklist_text_{index}"] = item["text"]
            st.session_state[f"event_checklist_confirm_{index}"] = item["completed"]

    checklist_items = st.session_state["event_checklist_items"]
    for index, item in enumerate(checklist_items):
        item["text"] = st.session_state.get(
            f"event_checklist_text_{index}",
            item["text"],
        )
        item["completed"] = st.session_state.get(
            f"event_checklist_confirm_{index}",
            item["completed"],
        )
    st.session_state["event_checklist_items"] = checklist_items
    completed_actions = sum(1 for item in checklist_items if item["completed"])
    progress = completed_actions / len(checklist_items) if checklist_items else 0
    st.progress(progress, text=f"{completed_actions} of {len(checklist_items)} checklist items complete")

    with st.expander("Personal follow-up notes", expanded=False):
        st.text_area(
            "Notes",
            key="event_handover_note",
            placeholder="Add private reminders or planning details",
        )

    st.markdown("**Recommended actions**")
    st.caption("Confirm each item, edit the text, or remove it if it is not relevant.")
    checklist_items = st.session_state["event_checklist_items"]
    for index, item in enumerate(checklist_items):
        confirmed_column, text_column, delete_column = st.columns([0.12, 0.72, 0.16])
        with confirmed_column:
            confirmed = st.checkbox(
                "Done",
                value=item["completed"],
                key=f"event_checklist_confirm_{index}",
            )
        with text_column:
            text = st.text_input(
                "Checklist action",
                value=item["text"],
                key=f"event_checklist_text_{index}",
                label_visibility="collapsed",
            )
        with delete_column:
            if st.button("Remove", key=f"delete_checklist_{index}", use_container_width=True):
                checklist_items.pop(index)
                st.session_state["event_checklist_items"] = checklist_items
                st.rerun()
        checklist_items[index] = {"text": text, "completed": confirmed}
    st.session_state["event_checklist_items"] = checklist_items

    new_action_column, add_action_column = st.columns([0.84, 0.16])
    with new_action_column:
        new_action = st.text_input(
            "Add a checklist action",
            key="event_checklist_new_text",
            placeholder="Add your own action",
        )
    with add_action_column:
        st.write("")
        if st.button("Add", use_container_width=True):
            if new_action.strip():
                new_index = len(checklist_items)
                checklist_items.append(
                    {"text": new_action.strip(), "completed": False}
                )
                st.session_state["event_checklist_items"] = checklist_items
                st.session_state[f"event_checklist_confirm_{new_index}"] = False
                st.session_state[f"event_checklist_text_{new_index}"] = new_action.strip()
                st.session_state["event_checklist_new_text"] = ""
                st.rerun()

    with st.expander("Saved event plans", expanded=bool(event_name.strip())):
        plan_store = EventPlanStore()
        saved_plans = plan_store.list_plans(
            owner_id=None if is_admin else browser_owner_id
        )
        st.caption(
            "Plans are separated by browser identity, not individual accounts. "
            "They are private from normal visitors, but should not contain sensitive information."
        )
        save_column, delete_column = st.columns([0.72, 0.28])
        with save_column:
            if st.button("Save / update", type="primary", use_container_width=True):
                checklist_items = st.session_state["event_checklist_items"]
                checklist_state = {
                    str(index): item["completed"]
                    for index, item in enumerate(checklist_items)
                }
                checklist_items_data = [
                    {
                        "text": str(item["text"]).strip(),
                        "completed": bool(item["completed"]),
                    }
                    for item in checklist_items
                    if str(item["text"]).strip()
                ]
                plan_data = {
                    "event_name": event_name,
                    "event_date": event_date.isoformat(),
                    "region": selected_region,
                    "setting": activity_type,
                    "duration_hours": float(duration_hours),
                    "activity_intensity": activity_intensity,
                    "attendee_mix": attendee_mix,
                    "handover_note": st.session_state["event_handover_note"],
                    "checklist": checklist_state,
                    "checklist_items": checklist_items_data,
                }
                try:
                    plan_store.save(event_name, plan_data, browser_owner_id)
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
                followup_status = plan_followup_status(plan)
                status_class = (
                    "neutral"
                    if followup_status == "No notes"
                    else ""
                )
                plan_data = plan.data
                card_name = escape(str(plan.name))
                card_date = escape(str(plan_data.get("event_date", "Date not set")))
                card_region = escape(str(plan_data.get("region", "Region not set")))
                st.markdown(
                    f"""
                    <div class="clarity-plan-card">
                      <strong>{card_name}</strong>
                      <div class="clarity-plan-meta">
                        {card_date} · {card_region}<br>
                        Progress: {completed}/{total} · {progress_percent}%<br>
                      </div>
                      <span class="clarity-plan-status {status_class}">{followup_status}</span>
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
                        if st.session_state["event_date"] < date.today():
                            st.session_state["event_date"] = date.today()
                        st.session_state["event_region"] = data.get("region", selected_region)
                        st.session_state["event_setting"] = data.get("setting", "Outdoor")
                        st.session_state["event_duration"] = float(data.get("duration_hours", 4))
                        st.session_state["event_intensity"] = data.get(
                            "activity_intensity", "Low"
                        )
                        st.session_state["event_attendee_mix"] = data.get(
                            "attendee_mix", "Healthy adults"
                        )
                        st.session_state["event_handover_note"] = data.get("handover_note", "")
                        stored_items = data.get("checklist_items")
                        if isinstance(stored_items, list):
                            loaded_items = [
                                {
                                    "text": str(item.get("text", "")).strip(),
                                    "completed": bool(item.get("completed", False)),
                                }
                                for item in stored_items
                                if isinstance(item, dict)
                                and str(item.get("text", "")).strip()
                            ]
                        else:
                            legacy_checklist = data.get("checklist", {})
                            loaded_items = [
                                {
                                    "text": action,
                                    "completed": bool(
                                        legacy_checklist.get(str(index), False)
                                    ),
                                }
                                for index, action in enumerate(assessment.actions)
                            ]
                        st.session_state["event_checklist_items"] = loaded_items
                        st.session_state["event_checklist_source"] = (
                            reading_kind,
                            assessment_value,
                            assessment.summary,
                            *assessment.actions,
                        )
                        for index, item in enumerate(loaded_items):
                            st.session_state[f"event_checklist_text_{index}"] = item["text"]
                            st.session_state[
                                f"event_checklist_confirm_{index}"
                            ] = item["completed"]
                        st.rerun()
                with delete_card_column:
                    if st.button("Delete", key=f"delete_plan_{plan.id}", use_container_width=True):
                        st.session_state["confirm_delete_plan"] = plan.id

                if st.session_state["confirm_delete_plan"] == plan.id:
                    st.warning(f'Delete "{plan.name}"?')
                    confirm_column, cancel_column = st.columns(2)
                    with confirm_column:
                        if st.button("Confirm", key=f"confirm_delete_{plan.id}", use_container_width=True):
                            plan_store.delete(
                                plan.id,
                                owner_id=None if is_admin else browser_owner_id,
                            )
                            st.session_state["confirm_delete_plan"] = None
                            st.success("Saved event plan deleted.")
                            st.rerun()
                    with cancel_column:
                        if st.button("Cancel", key=f"cancel_delete_{plan.id}", use_container_width=True):
                            st.session_state["confirm_delete_plan"] = None

    st.caption(
        f"This is an operational checklist based on the selected {reading_kind} reading, "
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
        (
            "- Personal follow-up notes: "
            f"{st.session_state['event_handover_note'] or 'None'}"
        ),
        (
            f"- Event reading: {reading_kind} {assessment_value}"
            f"{' µg/m³' if reading_kind == 'PM2.5' else ''}"
            if assessment_value is not None
            else f"- Event reading: {reading_kind} unavailable"
        ),
        "",
        assessment.summary,
        "",
        "## Checklist",
    ]
    assessment_lines.extend(
        (
            "- [x] "
            if st.session_state.get(
                f"event_checklist_confirm_{index}",
                item["completed"],
            )
            else "- [ ] "
        )
        + str(
            st.session_state.get(
                f"event_checklist_text_{index}",
                item["text"],
            )
        ).strip()
        for index, item in enumerate(st.session_state["event_checklist_items"])
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

st.markdown(
    "Sources: [data.gov.sg live 1-hour PM2.5 API]"
    "(https://api-open.data.gov.sg/v2/real-time/api/pm25) · "
    "[data.gov.sg live PSI API]"
    "(https://api-open.data.gov.sg/v2/real-time/api/psi) · "
    "[NEA air pollution information]"
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/managing-haze)"
)
st.caption(EDUCATIONAL_DISCLAIMER)
