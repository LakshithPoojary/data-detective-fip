# Data Detective — Live Think–Pair–Share

A projector-friendly, cloud-ready Streamlit classroom activity for the Matplotlib lesson.

## What it does

- Exactly 12 fixed pair slots.
- One device per pair.
- Teacher PIN protected.
- QR code on teacher dashboard for students.
- THINK: 30 seconds.
- PAIR: 30 seconds.
- SHARE: pairs submit one final answer/reasoning.
- Teacher sees joined/submitted status live.
- Share responses become a live word cloud.
- REVEAL shows the correct Line chart and interpretation.
- Teacher projector view uses very large typography.
- Student view is responsive for phones of different sizes.
- Shared state is stored in Supabase, not local SQLite.

## 1. Create the Supabase database

Create a Supabase project and open SQL Editor.

Paste and run `supabase_schema.sql`.

## 2. Put the app on GitHub

Repository should contain:

    app.py
    requirements.txt
    supabase_schema.sql
    secrets.toml.example
    README.md

Do NOT commit your real secrets.

## 3. Deploy to Streamlit Community Cloud

Create the app from GitHub and select `app.py` as the entrypoint.

In Advanced settings > Secrets, paste:

    SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
    SUPABASE_KEY = "YOUR-SUPABASE-SERVICE-ROLE-KEY"
    TEACHER_PIN = "2468"
    APP_URL = "https://YOUR-APP.streamlit.app"

After deployment, open the teacher URL.

## 4. Classroom workflow

Teacher:
1. Open the deployed app.
2. Enter the teacher PIN.
3. Put the dashboard into browser full-screen (F11).
4. Show the QR code.
5. Students scan it and choose Pair 01–12.
6. Start THINK.
7. Start PAIR.
8. Open SHARE.
9. Watch the live word cloud.
10. Reveal.
11. Start a new round if required.

Students:
1. Scan QR.
2. Select the assigned pair slot.
3. THINK: choose the chart.
4. PAIR: discuss.
5. SHARE: submit final answer and reason.
6. Watch the teacher screen for the reveal.

## Projector settings

Recommended:
- Browser full-screen: F11.
- Browser zoom: 100%.
- Projector resolution: 1080p or higher if available.
- Teacher dashboard is deliberately oversized for last-bench visibility.
- Student layout automatically adapts to mobile width.

## Security

The Supabase service-role key and teacher PIN belong in Streamlit Secrets only.
Never commit them to GitHub.

## Notes

The live refresh uses Streamlit fragments so the teacher dashboard and student screens can update without rebuilding the entire app every second.
