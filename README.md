# Clarity SG

For AI Champions Bootcamp Aug-Nov 2026. A Streamlit app for event planners to
review Singapore's latest 1-hour PM2.5 activity guidance by region, alongside
the 24-hour PSI overview. It uses live APIs published by
[data.gov.sg](https://api-open.data.gov.sg/v2/real-time/api/pm25) for PM2.5 and
[data.gov.sg](https://api-open.data.gov.sg/v2/real-time/api/psi) for PSI.

The app includes a PSI dashboard, an **About Us** page covering the project
scope and data sources, a **Methodology** page explaining the data flow and
PM2.5 activity-guidance bands, and an **Ask Clarity** page for source-cited
answers about the app's guidance.

## Main features

- Live 1-hour PM2.5 and 24-hour PSI readings for Central, East, North, South,
  and West Singapore.
- A dynamic event assessment: 1-hour PM2.5 today, 24-hour PSI for future
  events within 7 days, and long-range planning guidance beyond 7 days.
- A streamlined status summary with the relevant reading, freshness, and band.
- Singapore address lookup and an approximate region map.
- Editable recommended actions with confirmation, text editing, add, and delete controls.
- An Event Planning Assessment based on date, duration, event setting,
  activity intensity, and attendee mix.
- A downloadable Markdown checklist with completed-item status.
- Browser-private SQLite event plans with follow-up owner, threshold, next-check,
  follow-up note, and checklist details.
- PM2.5 or PSI threshold alerts matched to the event-date reading type.
- Source-cited Ask Clarity responses from app guidance and official NEA pages.

## Run locally

1. Install [uv](https://docs.astral.sh/uv/).
2. Create a `.streamlit` folder if needed, then create
   `.streamlit/secrets.toml` and choose a private password:

   ```toml
   app_password = "replace-this-with-your-own-password"
   admin_password = "replace-this-with-a-separate-admin-password"
   openai_api_key = "your-openai-api-key"
   ```

   Keep this file private; it is excluded from Git. Ask Clarity sends questions
   and knowledge-base excerpts to OpenAI to create embeddings and answers.
3. Sync dependencies:

   ```sh
   uv sync
   ```

4. Start the app:

   ```sh
   uv run streamlit run streamlit_app.py
   ```

For Streamlit Community Cloud, add the same setting in the app's **Settings →
Secrets** before sharing the app:

```toml
app_password = "your-private-password"
admin_password = "your-separate-admin-password"
openai_api_key = "your-openai-api-key"
```

The app uses one shared password, not individual accounts. Saved plans are
separated by browser identity, but browser identity is a convenience boundary,
not strong security. Anyone with app/database access can inspect stored plans.

Ask Clarity answers questions about the app's guidance using a curated local
guidance base and current content from NEA's air-pollution FAQs and haze
guidance pages. NEA content is cached for up to one hour, with a manual refresh
option, and cited answers show when those pages were fetched. It does not
provide live readings, forecasts, medical advice, or event-cancellation
decisions. Questions and retrieved excerpts are sent to OpenAI; do not enter
personal or sensitive information.

Choose the event setting in the sidebar. In the **Event location** section,
choose an air-quality region manually, click the map, or submit a Singapore
address to get an approximate region suggestion. Address lookup sends the
submitted address to OpenStreetMap's public Nominatim service; avoid entering
sensitive addresses. The map also loads OpenStreetMap tiles. The suggested
region is based on the nearest reference point, not official boundary
polygons, and can be changed manually.

The 1-hour PM2.5 reading is used for events held today and shows its associated
activity guidance:

- **Normal:** 0-55 µg/m³; all persons can continue with their activities.
- **Elevated:** 56-150 µg/m³; healthy persons should reduce strenuous outdoor
  activities; vulnerable persons should avoid strenuous outdoor activities.
- **High:** 151-250 µg/m³; healthy persons should avoid strenuous outdoor
  activities; vulnerable persons should avoid all outdoor activities.
- **Very High:** above 250 µg/m³; healthy persons should minimise all outdoor
  activities; vulnerable persons should avoid all outdoor activities.

In this guidance, **reduce** means do less, **minimise** means do as little as
possible, and **avoid** means do not do the specified activity.

These are activity-guidance bands, not automatic cancellation rules.

The Event Planning Assessment uses the latest regional 1-hour PM2.5 reading
for events held today and the latest 24-hour PSI overview for future events
within 7 days. Events more than 7 days away use long-range planning guidance
instead of an air-quality forecast. They should be checked again with 1-hour
PM2.5 readings on the event day. Past events use 24-hour PSI only as retrospective context. The assessment also
uses event duration, setting, highest activity intensity, and attendee mix.
It creates a checklist for monitoring, venue alternatives,
exposure reduction, and vulnerable attendees. The checklist can be downloaded
as Markdown. It is operational planning support, not an official advisory,
forecast, or automatic cancellation decision.

Event plans can be saved locally in SQLite with a follow-up owner, next-check
details, threshold selection, personal follow-up notes, and checklist status. The
database is stored in `.data/event_plans.sqlite3` and is excluded from Git.
Plans are separated by browser identity and are not designed for secure,
sensitive, or personally identifiable information.

Saved plans appear as cards with date, region, follow-up owner, threshold, checklist
progress, and follow-up status. Each card can be loaded or deleted, with delete
confirmation to prevent accidental removal. On smaller screens, dashboard,
status, regional, and saved-plan cards stack for easier use.

The threshold status is recalculated when live readings are refreshed or a
saved plan is loaded. It is an on-screen planning alert, not a push
notification, continuously running monitor, forecast, or cancellation rule.

Both feeds show current readings, not a forecast for a future event time.
Future events within 7 days may use the 24-hour PSI as near-term context.
Longer-range events do not receive an air-quality forecast and must be checked
again with 1-hour PM2.5 on the event day. Recheck close to the event,
consult official NEA advisories, and follow your
organization's safety policy. The app does not automatically cancel events or
provide individual medical advice.
