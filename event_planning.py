from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


ActivitySetting = Literal["Outdoor", "Mixed indoor and outdoor", "Indoor"]
ActivityIntensity = Literal["Low", "Moderate", "Strenuous"]
AttendeeMix = Literal["Healthy adults", "Mixed or unknown", "Vulnerable attendees"]
ReadingKind = Literal["PM2.5", "PSI", "Planning"]
FUTURE_PLANNING_HORIZON_DAYS = 7
MAX_RECOMMENDED_ACTIONS = 5


@dataclass(frozen=True)
class EventAssessment:
    level: str
    summary: str
    actions: tuple[str, ...]
    reading_kind: str = "PM2.5"
    reading_value: int | None = None


def build_event_assessment(
    pm25_value: int | None,
    setting: ActivitySetting,
    intensity: ActivityIntensity,
    attendee_mix: AttendeeMix,
    duration_hours: float,
    event_date: date,
    today: date,
    reading_kind: ReadingKind = "PM2.5",
) -> EventAssessment:
    # A missing reading means the app cannot make a planning assessment.
    if pm25_value is None:
        if reading_kind == "Planning":
            summary = (
                "This event is beyond the 7-day planning horizon: "
                "the latest 24-hour PSI is not a useful event forecast."
            )
        else:
            summary = f"A current regional {reading_kind} reading is required."
        return EventAssessment(
            level="Unable to assess",
            summary=summary,
            actions=(
                (
                    "Keep the event flexible and use this as long-range planning only."
                    if reading_kind == "Planning"
                    else "Recheck the data feed before relying on this checklist."
                ),
                (
                    "Create a follow-up reminder to check 1-hour PM2.5 readings "
                    "on the event day."
                    if reading_kind == "Planning"
                    else "Choose another Singapore region only if the venue location supports it."
                ),
                "Follow official NEA advisories and your organisation's event policy.",
            ),
            reading_kind=reading_kind,
        )

    # PM2.5 and PSI use different category boundaries.
    if reading_kind == "PSI":
        if pm25_value <= 50:
            band = "Good"
        elif pm25_value <= 100:
            band = "Moderate"
        elif pm25_value <= 200:
            band = "Unhealthy"
        elif pm25_value <= 300:
            band = "Very unhealthy"
        else:
            band = "Hazardous"
    else:
        if pm25_value <= 55:
            band = "Normal"
        elif pm25_value <= 150:
            band = "Elevated"
        elif pm25_value <= 250:
            band = "High"
        else:
            band = "Very High"

    is_outdoor_exposure = setting != "Indoor"
    vulnerable = attendee_mix == "Vulnerable attendees"
    long_exposure = duration_hours >= 4

    if band in {"Normal", "Good"}:
        level = "Monitor"
        summary = f"{band} {reading_kind}: continue normal planning and recheck near the event."
    elif band in {"Elevated", "Moderate"}:
        level = "Prepare"
        summary = f"{band} {reading_kind}: reduce strenuous outdoor exertion, especially for vulnerable attendees."
    elif band in {"High", "Unhealthy"}:
        level = "Act"
        summary = f"{band} {reading_kind}: avoid strenuous outdoor exertion and limit outdoor attendance time."
    else:
        level = "Urgent review"
        summary = f"{band} {reading_kind}: minimise outdoor activity and review whether outdoor components should proceed."

    actions: list[str] = []

    # The first actions cover venue fallback; later actions add only relevant risks.
    if is_outdoor_exposure:
        actions.append("Prepare shaded or indoor fallback areas and plan frequent breaks.")
    else:
        actions.append("Keep indoor air-quality systems operating normally and prepare a monitored indoor fallback.")

    if setting == "Mixed indoor and outdoor":
        actions.append("Move prolonged or strenuous sessions indoors or under enclosed shelter.")

    if intensity == "Strenuous" and is_outdoor_exposure:
        if band in {"High", "Very High", "Unhealthy", "Very unhealthy", "Hazardous"}:
            actions.append("Reschedule or move strenuous outdoor activities.")
        else:
            actions.append("Reduce session intensity or duration.")

    if vulnerable:
        actions.append("Confirm alternatives for elderly, pregnant, and chronically ill attendees.")

    if is_outdoor_exposure and long_exposure:
        actions.append("Split exposure into shorter periods.")

    if event_date > today:
        actions.append(
            f"This is a future-dated event: use the 24-hour PSI overview as planning context, not a forecast."
        )
    elif event_date == today:
        actions.append("Recheck readings immediately before outdoor activities begin.")
    else:
        actions.append("The event date is in the past; use these results only for retrospective planning.")

    actions.append("Consult official NEA advisories and the organisation's event policy before making a decision.")
    return EventAssessment(
        level=level,
        summary=summary,
        actions=tuple(dict.fromkeys(actions))[:MAX_RECOMMENDED_ACTIONS],
        reading_kind=reading_kind,
        reading_value=pm25_value,
    )


def select_event_reading(
    event_date: date,
    today: date,
    pm25_value: int | None,
    psi_value: int | None,
) -> tuple[int | None, ReadingKind]:
    # Keep the selected reading tied to the event date, not both readings at once.
    if event_date == today:
        return pm25_value, "PM2.5"
    if event_date > today:
        if event_date <= today + timedelta(days=FUTURE_PLANNING_HORIZON_DAYS):
            return psi_value, "PSI"
        return None, "Planning"
    return psi_value, "PSI"
