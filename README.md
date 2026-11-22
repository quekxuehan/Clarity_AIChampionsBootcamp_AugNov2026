# Clarity SG

For AI Champions Bootcamp Aug-Nov 2026. A Streamlit app for event planners to cross-reference Singapore's latest
24-hour PSI readings by region against an event's chosen action threshold.
It uses the live PSI API published by [data.gov.sg](https://api-open.data.gov.sg/v2/real-time/api/psi).

The app includes a PSI dashboard, an **About Us** page covering the project
scope and data sources, and a **Methodology** page explaining the data flow
and event-threshold logic.

## Run locally

1. Install [uv](https://docs.astral.sh/uv/).
2. Create a `.streamlit` folder if needed, then create
   `.streamlit/secrets.toml` and choose a private password:

   ```toml
   app_password = "replace-this-with-your-own-password"
   ```

   Keep this file private; it is excluded from Git.
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
```

The app uses one shared password, not individual accounts. Anyone with the
password can access it, so do not reuse an important personal password.

Choose the event region and set the PSI value at which your organization wants
to review or change its event plan. The default threshold is 101, the start of
the NEA "Unhealthy" PSI band; it is only a starting point, not a universal
cancellation rule.

The app displays a live 24-hour PSI snapshot, not a forecast. Recheck close to
the event, consult official NEA advisories, and follow your organization's
safety policy. It does not automatically cancel events or provide medical
advice.
