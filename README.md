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

## Run locally

1. Install [uv](https://docs.astral.sh/uv/).
2. Create a `.streamlit` folder if needed, then create
   `.streamlit/secrets.toml` and choose a private password:

   ```toml
   app_password = "replace-this-with-your-own-password"
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
openai_api_key = "your-openai-api-key"
```

The app uses one shared password, not individual accounts. Anyone with the
password can access it, so do not reuse an important personal password.

Ask Clarity answers questions about the app's guidance using a curated local
knowledge base and OpenAI. It does not provide live readings, forecasts,
medical advice, or event-cancellation decisions. Do not enter personal or
sensitive information.

Choose the event setting in the sidebar. In the **Event location** section,
choose an air-quality region manually, click the map, or submit a Singapore
address to get an approximate region suggestion. Address lookup sends the
submitted address to OpenStreetMap's public Nominatim service; avoid entering
sensitive addresses. The map also loads OpenStreetMap tiles. The suggested
region is based on the nearest reference point, not official boundary
polygons, and can be changed manually.

The selected region and event setting show the current 1-hour PM2.5 band and
its associated activity guidance:

- **Normal:** 0-55 µg/m³; all persons can continue with their activities.
- **Elevated:** 56-150 µg/m³; healthy persons should reduce strenuous outdoor
  activities; vulnerable persons should avoid strenuous outdoor activities.
- **High:** 151-250 µg/m³; healthy persons should avoid strenuous outdoor
  activities; vulnerable persons should avoid all outdoor activities.
- **Very High:** above 250 µg/m³; healthy persons should minimise all outdoor
  activities; vulnerable persons should avoid all outdoor activities.

In this guidance, **reduce** means do less, **minimise** means do as little as
possible, and **avoid** means do not do the specified activity.

These are activity-guidance bands, not automatic cancellation rules. The
dashboard also shows the 24-hour PSI reading as a separate overview.

Both feeds show current readings, not a forecast for a future event time.
Recheck close to the event, consult official NEA advisories, and follow your
organization's safety policy. The app does not automatically cancel events or
provide individual medical advice.
