# Data Detective V4 — Live Classroom

A real multi-device Streamlit classroom activity for the Matplotlib/Data Visualization mini-challenge.

## What it does

- Teacher/projector screen split into LEFT + RIGHT.
- LEFT keeps the monthly attendance dataset visible.
- LEFT also shows only `X / 12 PAIRS JOINED`.
- WAITING screen shows a QR code.
- Teacher controls the stage:
  - START THINK
  - START PAIR
  - OPEN SHARE
  - REVEAL
  - NEW ROUND
- Student phones join one of 12 pair slots.
- Student THINK answers are shared with the teacher.
- Student SHARE responses appear on the teacher screen.
- REVEAL shows the correct chart and interpretation.

## Supabase setup

1. Create a Supabase project.
2. Open SQL Editor.
3. Run `supabase_schema.sql`.
4. Get the project URL and API key.
5. Configure Streamlit secrets.

Example `.streamlit/secrets.toml`:

SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_KEY"
TEACHER_PIN = "1234"
APP_URL = "https://YOUR-APP.streamlit.app"

For a classroom deployment, use an appropriate Supabase key and security/RLS configuration. Do not commit secrets to GitHub.

## Local run

    pip install -r requirements.txt
    streamlit run app.py

Open Teacher / Projector. The QR code should point to the configured APP_URL.

## Deploy

Push `app.py`, `requirements.txt`, and `supabase_schema.sql` to GitHub, deploy the app with Streamlit Community Cloud, and add the same values under the deployment's Secrets settings.

## Important

This version uses a shared Supabase database, so different phones can see the same classroom state. It is not based on Streamlit session_state for classroom synchronization.
