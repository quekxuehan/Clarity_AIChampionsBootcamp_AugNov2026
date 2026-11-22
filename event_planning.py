from dataclasses import dataclass
from datetime import date
from typing import Literal


ActivitySetting = Literal["Outdoor", "Mixed indoor and outdoor", "Indoor"]
ActivityIntensity = Literal["Low", "Moderate", "Strenuous"]
AttendeeMix = Literal["Healthy adults", "Mixed or unknown", "Vulnerable attendees"]


@dataclass(frozen=True)
class EventAssessment:
    level: str
    summary: str
    actions: tuple[str, ...]


def threshold_for_label(label: str) -> int | None:
    thresholds = {
        "Off": None,
        "Elevated (56 µg/m³)": 56,
        "High (151 µg/m³)": 151,
        "Very High (251 µg/m³)": 251,
    }
    return thresholds.get(label)


def threshold_status(pm25_value: int | None, threshold_label: str) -> str:
    threshold = threshold_for_label(threshold_label)
    if threshold is None:
        return "Alert threshold off"
    if pm25_value is None:
        return "Cannot determine: PM2.5 unavailable"
    if pm25_value >= threshold:
        return f"ALERT: PM2.5 is at or above {threshold} µg/m³"
    return f"Below alert threshold ({threshold} µg/m³)"


def build_event_assessment(
    pm25_value: int | None,
    setting: ActivitySetting,
    intensity: ActivityIntensity,
    attendee_mix: AttendeeMix,
    duration_hours: float,
    event_date: date,
    today: date,
) -> EventAssessment:
    if pm25_value is None:
        return EventAssessment(
            level="Unable to assess",
            summary="A current regional PM2.5 reading is required.",
            actions=(
                "Recheck the data feed before relying on this checklist.",
                "Choose another Singapore region only if the venue location supports it.",
                "Keep the event flexible and follow official NEA advisories.",
            ),
        )

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

    if band == "Normal":
        level = "Monitor"
        summary = f"{band} PM2.5: continue normal planning and recheck near the event."
    elif band == "Elevated":
        level = "Prepare"
        summary = f"{band} PM2.5: reduce strenuous outdoor exertion, especially for vulnerable attendees."
    elif band == "High":
        level = "Act"
        summary = f"{band} PM2.5: avoid strenuous outdoor exertion and limit outdoor attendance time."
    else:
        level = "Urgent review"
        summary = f"{band} PM2.5: minimise outdoor activity and review whether outdoor components should proceed."

    actions: list[str] = []

    if is_outdoor_exposure:
        actions.append("Assign a named safety lead to recheck the live reading before and during the event.")
        actions.append("Prepare shaded, indoor, or filtered-air fallback areas for exposed participants.")
        actions.append("Plan more frequent breaks and shorten continuous outdoor sessions.")
    else:
        actions.append("Keep indoor air-quality systems operating normally and prepare a monitored indoor fallback.")

    if setting == "Mixed indoor and outdoor":
        actions.append("Move prolonged or strenuous sessions indoors or under an enclosed shelter.")

    if intensity == "Strenuous" and is_outdoor_exposure:
        if band in {"High", "Very High"}:
            actions.append("Reschedule or move strenuous outdoor activities; do not rely on masks as a substitute for activity modification.")
        else:
            actions.append("Reduce session intensity or duration during elevated PM2.5 conditions.")

    if vulnerable:
        actions.append("Confirm alternatives for elderly, pregnant, and chronically ill attendees, including children and people with heart or lung conditions.")

    if is_outdoor_exposure and long_exposure:
        actions.append("Split exposure into shorter periods and monitor conditions at least hourly.")

    if event_date > today:
        actions.append(
            "This is a future-dated event: treat the current reading as planning context, not a forecast."
        )
    elif event_date == today:
        actions.append("Recheck readings immediately before outdoor activities begin.")
    else:
        actions.append("The event date is in the past; use these results only for retrospective planning.")

    actions.append("Consult official NEA advisories and the organisation's event policy before making a decision.")
    return EventAssessment(level=level, summary=summary, actions=tuple(dict.fromkeys(actions)))
