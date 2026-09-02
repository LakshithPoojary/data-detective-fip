import io
import os
import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from PIL import Image
import qrcode
from wordcloud import WordCloud

st.set_page_config(
    page_title="Data Detective • Think–Pair–Share",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_PAIRS = 12
THINK_SECONDS = 30
PAIR_SECONDS = 30

CHARTS = ["Line", "Bar", "Pie", "Histogram", "Scatter"]

# The challenge is based on the user's Matplotlib lesson:
# Jan 75, Feb 80, Mar 78, Apr 85, May 90
# Question: How has attendance changed over the term?
# Correct visualization: Line chart
ATTENDANCE = {"Jan": 75, "Feb": 80, "Mar": 78, "Apr": 85, "May": 90}


def utc_now():
    return datetime.now(timezone.utc)


def get_secrets():
    try:
        return st.secrets
    except Exception:
        return {}


SECRETS = get_secrets()
SUPABASE_URL = SECRETS.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = SECRETS.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
TEACHER_PIN = str(SECRETS.get("TEACHER_PIN", os.getenv("TEACHER_PIN", "1234")))
APP_URL = str(SECRETS.get("APP_URL", os.getenv("APP_URL", ""))).strip()

try:
    from supabase import create_client
except Exception:
    create_client = None


@st.cache_resource
def get_db():
    if not (SUPABASE_URL and SUPABASE_KEY and create_client):
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


db = get_db()


def db_ready():
    return db is not None


def read_state():
    if not db:
        return {
            "id": 1,
            "stage": "WAITING",
            "stage_started_at": None,
            "round_no": 1,
        }
    res = db.table("session_state").select("*").eq("id", 1).single().execute()
    return res.data


def update_state(**kwargs):
    if not db:
        return
    db.table("session_state").update(kwargs).eq("id", 1).execute()


def read_pairs():
    if not db:
        return []
    res = db.table("pairs").select("*").order("pair_no").execute()
    return res.data or []


def read_pair(pair_no):
    if not db:
        return None
    res = db.table("pairs").select("*").eq("pair_no", pair_no).single().execute()
    return res.data


def reset_pairs():
    if not db:
        return
    db.table("pairs").update({
        "joined": False,
        "joined_at": None,
        "think_answer": None,
        "think_submitted_at": None,
        "share_text": None,
        "share_submitted_at": None,
    }).gte("pair_no", 1).lte("pair_no", MAX_PAIRS).execute()


def join_pair(pair_no):
    if not db:
        return False, "Database is not connected."
    current = read_pair(pair_no)
    if not current:
        return False, "Pair slot not found."
    if current.get("joined"):
        return False, "That pair slot is already occupied."
    # Re-check the slot immediately before write.
    db.table("pairs").update({
        "joined": True,
        "joined_at": utc_now().isoformat(),
    }).eq("pair_no", pair_no).eq("joined", False).execute()
    verify = read_pair(pair_no)
    if verify and verify.get("joined"):
        return True, "Joined."
    return False, "That slot was just taken. Choose another slot."


def submit_think(pair_no, answer):
    if not db:
        return
    db.table("pairs").update({
        "think_answer": answer,
        "think_submitted_at": utc_now().isoformat(),
    }).eq("pair_no", pair_no).execute()


def submit_share(pair_no, text):
    if not db:
        return
    db.table("pairs").update({
        "share_text": text.strip(),
        "share_submitted_at": utc_now().isoformat(),
    }).eq("pair_no", pair_no).execute()


def clear_round_answers():
    if not db:
        return
    db.table("pairs").update({
        "think_answer": None,
        "think_submitted_at": None,
        "share_text": None,
        "share_submitted_at": None,
    }).gte("pair_no", 1).lte("pair_no", MAX_PAIRS).execute()


def stage_seconds(state):
    started = state.get("stage_started_at")
    if not started:
        return None
    try:
        dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        return max(0, int((utc_now() - dt).total_seconds()))
    except Exception:
        return None


def set_stage(stage):
    update_state(stage=stage, stage_started_at=utc_now().isoformat())


def inject_css(projector=False, student=False):
    base = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap');
      html, body, [class*="css"] { font-family: Inter, sans-serif; }
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }
      .hero {
        border-radius: 24px; padding: 26px 30px; margin-bottom: 18px;
        background: linear-gradient(135deg, #0b1f3a 0%, #173e6d 55%, #245b91 100%);
        color: white; box-shadow: 0 10px 30px rgba(11,31,58,.18);
      }
      .hero .eyebrow { font-size: 1rem; letter-spacing: .14em; font-weight: 800; opacity: .78; }
      .hero h1 { font-size: clamp(2rem, 4vw, 4rem); line-height: 1; margin: 8px 0 10px; font-weight: 900; }
      .hero p { font-size: clamp(1rem, 1.7vw, 1.45rem); margin: 0; opacity: .92; }
      .stage {
        border-radius: 20px; padding: 18px 24px; margin: 14px 0;
        border: 2px solid #dbe5ef; background: #f7fafc;
      }
      .stage-name { font-size: clamp(1.5rem, 3vw, 3.2rem); font-weight: 900; }
      .timer { font-size: clamp(2.4rem, 6vw, 5.6rem); font-weight: 900; line-height: 1; text-align: center; }
      .status-grid { display:grid; grid-template-columns:repeat(4,minmax(130px,1fr)); gap:12px; }
      .slot {
        border: 2px solid #dbe5ef; border-radius: 16px; padding: 14px;
        min-height: 105px; background:white;
      }
      .slot .num { font-size: 1rem; font-weight:900; opacity:.6; }
      .slot .state { font-size: 1.25rem; font-weight:800; margin-top:8px; }
      .slot .sub { font-size:.95rem; opacity:.68; margin-top:3px; }
      .metric {
        border-radius: 18px; padding: 18px; background:white; border:2px solid #dbe5ef;
        text-align:center; min-height:105px;
      }
      .metric .big { font-size:clamp(2rem,4vw,3.5rem); font-weight:900; line-height:1; }
      .metric .label { font-size:1rem; font-weight:700; opacity:.68; margin-top:8px; }
      .choice {
        border:2px solid #dbe5ef; border-radius:18px; padding:18px; text-align:center;
        background:white; font-size:1.25rem; font-weight:800;
      }
      .small-note { font-size:1rem; opacity:.7; }
      div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        min-height: 3.2rem; font-size: 1.05rem; font-weight: 800; border-radius: 14px;
      }
      textarea, input { font-size: 1.1rem !important; }
      @media (max-width: 800px) {
        .block-container { padding: 0.8rem 0.8rem 1.5rem; }
        .status-grid { grid-template-columns:repeat(2,minmax(120px,1fr)); }
        .hero { padding: 20px; border-radius: 18px; }
      }
    </style>
    """
    if projector:
        base += """
        <style>
          .block-container { max-width: 1700px; padding: 1.5rem 2.5rem 3rem; }
          .hero h1 { font-size: clamp(3.2rem, 6vw, 6.5rem); }
          .hero p { font-size: clamp(1.35rem, 2vw, 2rem); }
          .hero { padding: 34px 42px; }
          .stage { padding: 24px 32px; }
          .stage-name { font-size: clamp(2.5rem, 4vw, 4.6rem); }
          .status-grid { grid-template-columns:repeat(4,1fr); gap:18px; }
          .slot { min-height:150px; padding:20px; }
          .slot .num { font-size:1.3rem; }
          .slot .state { font-size:1.7rem; }
          .slot .sub { font-size:1.15rem; }
          .metric { min-height:135px; padding:24px; }
          .metric .big { font-size:clamp(3rem, 5vw, 5.5rem); }
          .metric .label { font-size:1.25rem; }
          div.stButton > button { min-height:4.2rem; font-size:1.35rem; }
        </style>
        """
    if student:
        base += """
        <style>
          .block-container { max-width: 720px; margin:auto; padding:1rem 1rem 2rem; }
          .hero h1 { font-size:clamp(2rem,8vw,3.3rem); }
          .hero p { font-size:clamp(1rem,4vw,1.35rem); }
          .stage-name { font-size:clamp(1.8rem,8vw,3rem); }
          .timer { font-size:clamp(3.2rem,16vw,5.5rem); }
          .choice { padding:16px 10px; font-size:1.15rem; }
          div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
             min-height:3.8rem; font-size:1.1rem;
          }
        </style>
        """
    st.html(base)


def hero(title, subtitle, eyebrow="DATA DETECTIVE"):
    st.html(
        f'<div class="hero"><div class="eyebrow">{eyebrow}</div>'
        f'<h1>{title}</h1><p>{subtitle}</p></div>'
    )


def countdown(stage, state):
    secs = stage_seconds(state)
    limit = THINK_SECONDS if stage == "THINK" else PAIR_SECONDS
    if secs is None:
        return limit
    return max(0, limit - secs)


def wordcloud_image(texts):
    text = " ".join(t for t in texts if t)
    if not text.strip():
        return None
    wc = WordCloud(width=1600, height=700, background_color="white", collocations=False).generate(text)
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    buf.seek(0)
    return Image.open(buf)


def qr_image(url):
    # Return PNG bytes instead of qrcode's wrapper object.
    # This is reliably accepted by Streamlit Cloud's image renderer.
    qr = qrcode.QRCode(box_size=9, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@st.fragment(run_every="1s")
def projector_dashboard():
    inject_css(projector=True)
    hero(
        "THINK • PAIR • SHARE",
        "Data Detective Challenge — look at the question, choose the visualization, defend your choice.",
        "FIP • DATA VISUALIZATION WITH MATPLOTLIB",
    )

    state = read_state()
    pairs = read_pairs()
    joined = sum(bool(p.get("joined")) for p in pairs)
    think_done = sum(bool(p.get("think_submitted_at")) for p in pairs)
    share_done = sum(bool(p.get("share_submitted_at")) for p in pairs)

    stage = state["stage"]
    remaining = countdown(stage, state) if stage in ("THINK", "PAIR") else None

    st.markdown(
        f'<div class="stage"><div class="stage-name">CURRENT STAGE: {stage}</div>'
        + (f'<div class="timer">{remaining}s</div>' if remaining is not None else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    if stage == "THINK" and remaining == 0:
        set_stage("PAIR")
        st.rerun()
    if stage == "PAIR" and remaining == 0:
        set_stage("SHARE")
        st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    for col, value, label in [
        (m1, joined, "PAIRS JOINED"),
        (m2, think_done, "THINK ANSWERS"),
        (m3, share_done, "SHARE ANSWERS"),
        (m4, MAX_PAIRS, "MAX PAIRS"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric"><div class="big">{value}</div><div class="label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Pair Status")
    cards = []
    for p in pairs:
        if p.get("joined"):
            if p.get("share_submitted_at"):
                status, sub = "SHARED ✓", "Answer received"
            elif p.get("think_submitted_at"):
                status, sub = "THINK ✓", "Choice locked"
            else:
                status, sub = "JOINED", "Thinking…"
        else:
            status, sub = "AVAILABLE", "Waiting"
        cards.append(
            f'<div class="slot"><div class="num">PAIR {p["pair_no"]:02d}</div>'
            f'<div class="state">{status}</div><div class="sub">{sub}</div></div>'
        )
    st.markdown('<div class="status-grid">' + "".join(cards) + '</div>', unsafe_allow_html=True)

    st.markdown("---")
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("### Challenge")
        st.markdown(
            "<div class='stage'><div style='font-size:1.55rem;font-weight:800'>"
            "Monthly Attendance</div><p style='font-size:1.3rem'>"
            "Jan 75 • Feb 80 • Mar 78 • Apr 85 • May 90</p>"
            "<p style='font-size:1.35rem;font-weight:700'>"
            "Question: How has attendance changed over the term?</p></div>",
            unsafe_allow_html=True,
        )
        if stage == "REVEAL":
            st.success("✓ Correct visualization: LINE CHART")
            st.info("Interpretation: Attendance trends upward overall, with a small dip in March before recovering.")
            chart_df = pd.DataFrame({"Attendance": list(ATTENDANCE.values())}, index=list(ATTENDANCE.keys()))
            st.line_chart(chart_df, height=430)
    with right:
        st.markdown("### Live Share Wall")
        texts = [p.get("share_text") for p in pairs if p.get("share_text")]
        img = wordcloud_image(texts)
        if img:
            st.image(img, use_container_width=True)
        else:
            st.markdown(
                "<div class='stage' style='min-height:260px;display:flex;align-items:center;justify-content:center'>"
                "<div style='font-size:1.6rem;font-weight:800;opacity:.6;text-align:center'>"
                "Waiting for pair responses…</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### Teacher Controls")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("▶ START THINK", use_container_width=True, disabled=stage not in ("WAITING", "REVEAL")):
            if stage == "REVEAL":
                clear_round_answers()
                state["round_no"] += 1
                update_state(round_no=state["round_no"])
            set_stage("THINK")
            st.rerun()
    with c2:
        if st.button("▶ START PAIR", use_container_width=True, disabled=stage != "THINK"):
            set_stage("PAIR")
            st.rerun()
    with c3:
        if st.button("▶ OPEN SHARE", use_container_width=True, disabled=stage != "PAIR"):
            set_stage("SHARE")
            st.rerun()
    with c4:
        if st.button("★ REVEAL", use_container_width=True, disabled=stage != "SHARE"):
            set_stage("REVEAL")
            st.rerun()
    with c5:
        if st.button("↺ NEW ROUND", use_container_width=True, disabled=stage not in ("REVEAL", "WAITING")):
            clear_round_answers()
            set_stage("WAITING")
            st.rerun()

    st.markdown("---")
    qleft, qright = st.columns([1, 1.2])
    with qleft:
        st.markdown("### Student Join QR")
        join_url = APP_URL
        if not join_url:
            join_url = st.text_input("Paste your deployed app URL once", placeholder="https://your-app.streamlit.app")
        if join_url:
            pair_url = join_url.rstrip("/") + "/?role=pair"
            st.image(qr_image(pair_url), width=300)
            st.code(pair_url, language=None)
        else:
            st.warning("Set APP_URL in Streamlit Secrets after deployment to show the QR automatically.")
    with qright:
        st.markdown("### Projector tip")
        st.info(
            "Use browser full-screen (F11) and browser zoom 100%. "
            "The teacher view is intentionally oversized for projection and last-bench visibility."
        )



def teacher_login():
    inject_css(projector=True)
    hero("TEACHER CONTROL ROOM", "Enter the teacher PIN to open the projector dashboard.")
    pin = st.text_input("Teacher PIN", type="password", max_chars=12)
    if st.button("OPEN DASHBOARD", use_container_width=True):
        if pin == TEACHER_PIN:
            st.session_state.teacher_ok = True
            st.rerun()
        else:
            st.error("Incorrect PIN.")


@st.fragment(run_every="1s")
def student_view():
    inject_css(student=True)
    hero("YOUR PAIR • YOUR ANSWER", "One device per pair. Choose together, then submit once.")
    state = read_state()

    if "pair_no" not in st.session_state:
        pairs = read_pairs()
        available = [p["pair_no"] for p in pairs if not p.get("joined")]
        if not available:
            st.error("All 12 pair slots are occupied. Please ask the teacher to free a slot.")
            return
        st.markdown("### Choose your pair number")
        cols = st.columns(3)
        for i in range(MAX_PAIRS):
            p = pairs[i] if i < len(pairs) else None
            occupied = bool(p and p.get("joined"))
            with cols[i % 3]:
                if st.button(
                    f"PAIR {i+1:02d}\n" + ("OCCUPIED" if occupied else "JOIN"),
                    key=f"join_{i+1}",
                    use_container_width=True,
                    disabled=occupied,
                ):
                    ok, msg = join_pair(i + 1)
                    if ok:
                        st.session_state.pair_no = i + 1
                        st.rerun()
                    else:
                        st.warning(msg)
        st.markdown(
            "<p class='small-note'>Only one device can occupy each pair slot. "
            "The teacher dashboard will show your pair as soon as you join.</p>",
            unsafe_allow_html=True,
        )
        return

    pair_no = st.session_state.pair_no
    p = read_pair(pair_no)
    if not p or not p.get("joined"):
        st.error("This pair slot is no longer active.")
        st.session_state.pop("pair_no", None)
        return

    stage = state["stage"]
    remaining = countdown(stage, state) if stage in ("THINK", "PAIR") else None

    st.markdown(
        f"<div class='stage'><div class='stage-name'>PAIR {pair_no:02d} • {stage}</div>"
        + (f"<div class='timer'>{remaining}s</div>" if remaining is not None else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    if stage == "WAITING":
        st.info("Waiting for the teacher to start THINK.")
    elif stage == "THINK":
        st.markdown("### THINK — choose individually first")
        st.markdown(
            "<p style='font-size:1.25rem;font-weight:700'>"
            "Which visualization best answers: How has attendance changed over the term?</p>",
            unsafe_allow_html=True,
        )
        if p.get("think_submitted_at"):
            st.success(f"Choice locked: {p.get('think_answer')}. Wait for PAIR.")
        else:
            choice = st.radio(
                "Your choice",
                CHARTS,
                horizontal=False,
                label_visibility="collapsed",
            )
            if st.button("LOCK MY CHOICE", use_container_width=True):
                submit_think(pair_no, choice)
                st.rerun()
    elif stage == "PAIR":
        st.success("PAIR — discuss your choices now. The teacher will open SHARE next.")
        if p.get("think_answer"):
            st.markdown(
                f"<div class='choice'>Your pair's locked choice: {p['think_answer']}</div>",
                unsafe_allow_html=True,
            )
    elif stage == "SHARE":
        st.markdown("### SHARE — submit your final reasoning")
        st.markdown(
            "<p style='font-size:1.2rem;font-weight:700'>"
            "Write your final chart choice and one short reason. "
            "Your response will appear on the teacher's live word cloud.</p>",
            unsafe_allow_html=True,
        )
        if p.get("share_submitted_at"):
            st.success("✓ Submitted. Look at the projector for the live class discussion.")
            st.markdown(
                f"<div class='choice'>{p.get('share_text','')}</div>",
                unsafe_allow_html=True,
            )
        else:
            with st.form("share_form"):
                answer = st.text_area(
                    "Final answer",
                    placeholder="Example: Line chart — because attendance changes across months.",
                    height=150,
                    max_chars=280,
                )
                submitted = st.form_submit_button("SUBMIT FINAL ANSWER", use_container_width=True)
                if submitted:
                    if answer.strip():
                        submit_share(pair_no, answer)
                        st.rerun()
                    else:
                        st.warning("Please enter your final answer.")
    elif stage == "REVEAL":
        st.success("REVEAL")
        st.markdown("### ✓ Correct answer: LINE CHART")
        st.markdown(
            "<p style='font-size:1.2rem'>Attendance increases overall, dips slightly in March, then rises again.</p>",
            unsafe_allow_html=True,
        )
        chart_df = pd.DataFrame({"Attendance": list(ATTENDANCE.values())}, index=list(ATTENDANCE.keys()))
        st.line_chart(chart_df, height=330)



def app():
    role = st.query_params.get("role", "home")
    if isinstance(role, list):
        role = role[0]

    if not db_ready():
        inject_css()
        hero("SETUP NEEDED", "The live classroom database is not connected yet.")
        st.error(
            "Add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets, then restart the app."
        )
        st.code(
            'SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"\n'
            'SUPABASE_KEY = "YOUR-SERVICE-ROLE-KEY"\n'
            'TEACHER_PIN = "2468"\n'
            'APP_URL = "https://YOUR-APP.streamlit.app"',
            language="toml",
        )
        return

    if role == "pair":
        student_view()
        return

    if st.session_state.get("teacher_ok"):
        projector_dashboard()
        return

    teacher_login()


if __name__ == "__main__":
    app()
