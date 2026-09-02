# Data Detective v4 — Think–Pair–Share–Interpret

This version follows the requested classroom flow exactly:

1. Teacher displays the attendance dataset as a table.
2. THINK — students choose the most suitable chart.
3. PAIR — partners discuss why they chose it.
4. SHARE — each pair submits its chart choice + reason in a text box.
5. Teacher screen builds a live word cloud from the submitted reasons.
6. INTERPRET — students choose: Continuous increase / Increase with a dip / Continuous decrease.
7. REVEAL — teacher shows the correct chart, correct interpretation, and number of pairs correct.
8. RESET CLASS clears all 12 slots and answers for the next quiz.

Dataset: June 60, July 65, August 72, September 68, October 80.
Correct chart: Line chart.
Correct interpretation: Increase with a dip.

## Supabase
Run `supabase_update.sql` once after the previous schema. It adds the interpretation columns and resets the round.

## Streamlit Secrets
```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SECRET-KEY"
TEACHER_PIN = "2468"
APP_URL = "https://YOUR-APP.streamlit.app"
```

Do not commit real secrets to GitHub.
