import os
import io
import time
import uuid
import socket
from datetime import datetime, timezone

import streamlit as st
import qrcode

try:
    from supabase import create_client
except ImportError:
    create_client = None

st.set_page_config(
    page_title="Data Detective | Live Classroom",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Theme ----------
st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container{padding:20px 28px 28px;max-width:1540px;}
html,body,[class*="css"]{font-family:Inter,Arial,sans-serif;}
.hero{background:linear-gradient(135deg,#0f172a,#1e3a8a);color:#fff;border-radius:18px;padding:20px 26px;margin-bottom:18px;box-shadow:0 10px 30px rgba(15,23,42,.14);}
.hero h1{font-size:34px!important;margin:0!important;font-weight:800!important;letter-spacing:-.02em;}
.hero p{font-size:15px!important;margin:5px 0 0!important;opacity:.78;}
.panel{background:#fff;border:1px solid #dbe3ee;border-radius:18px;padding:24px;min-height:570px;box-shadow:0 6px 24px rgba(15,23,42,.06);}
.dataset-title{font-size:23px;font-weight:800;color:#0f172a;margin-bottom:16px;}
.stage{font-size:14px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#64748b;margin-bottom:10px;}
.question{font-size:34px;line-height:1.18;font-weight:800;color:#0f172a;letter-spacing:-.02em;margin:10px 0 25px;}
.big-stat{font-size:56px;font-weight:800;color:#0f172a;line-height:1;}
.muted{font-size:13px;color:#64748b;font-weight:700;letter-spacing:.08em;}
.answer-card{display:flex;justify-content:space-between;align-items:center;border:1px solid #dbe3ee;border-radius:12px;padding:15px 18px;margin:9px 0;background:#f8fafc;font-size:18px;}
.qr-wrap{text-align:center;font-size:18px;color:#0f172a;}
.statusbar{display:flex;justify-content:space-between;align-items:center;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px 16px;margin-bottom:14px;}
.status-pill{font-size:13px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#1d4ed8;}
.joined{font-size:15px;font-weight:800;color:#0f172a;}
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;}
[data-testid="stButton"] button{border-radius:11px!important;font-weight:800!important;min-height:48px;}
[data-testid="stRadio"] label{font-size:18px!important;}
[data-testid="stTextArea"] textarea{font-size:18px!important;border-radius:12px!important;}
@media(max-width:900px){.block-container{padding:12px 12px 24px}.hero h1{font-size:26px!important}.panel{min-height:auto;padding:18px}.question{font-size:27px}.big-stat{font-size:46px}}
</style>
""", unsafe_allow_html=True)

# ---------- Content from the teaching activity ----------
DATA = {
    "Jan": 75, "Feb": 80, "Mar": 78, "Apr": 85, "May": 90
}
OPTIONS = ["Line chart", "Bar chart", "Pie chart", "Histogram", "Scatter plot"]
CORRECT = "Line chart"
QUESTION = "How has attendance changed over the term?"
CONCLUSION = "Attendance is trending upward overall, with a small dip in March before recovering."

# ---------- Supabase ----------
def get_config():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    pin = os.getenv("TEACHER_PIN", "1234")
    app_url = os.getenv("APP_URL", "")
    try:
        url = st.secrets.get("SUPABASE_URL", url)
        key = st.secrets.get("SUPABASE_KEY", key)
        pin = st.secrets.get("TEACHER_PIN", pin)
        app_url = st.secrets.get("APP_URL", app_url)
    except Exception:
        pass
    return url, key, pin, app_url

SUPABASE_URL, SUPABASE_KEY, TEACHER_PIN, APP_URL = get_config()

@st.cache_resource
def db():
    if not create_client or not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

sb = db()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def db_get_state():
    if not sb:
        return None
    r = sb.table("data_detective_state").select("*").eq("id", 1).limit(1).execute()
    return r.data[0] if r.data else None

def db_update_state(stage=None, round_no=None):
    if not sb:
        return
    payload = {"updated_at": now_iso()}
    if stage is not None:
        payload["stage"] = stage
        payload["stage_started_at"] = now_iso()
    if round_no is not None:
        payload["round_no"] = round_no
    sb.table("data_detective_state").update(payload).eq("id", 1).execute()

def db_get_data_detective_pairs():
    if not sb:
        return []
    r = sb.table("data_detective_pairs").select("*").eq("round_no", int(db_get_state()["round_no"])).order("pair_no").execute()
    return r.data or []

def db_join_pair():
    if not sb:
        return None, "Database is not configured."
    state = db_get_state()
    round_no = int(state["round_no"])
    existing = sb.table("data_detective_pairs").select("*").eq("round_no", round_no).eq("session_token", st.session_state.token).limit(1).execute()
    if existing.data:
        return existing.data[0], None

    # Try each free slot. Verification after update prevents two clients
    # from believing they own the same slot.
    for n in range(1, 13):
        free = sb.table("data_detective_pairs").select("*").eq("round_no", round_no).eq("pair_no", n).is_("session_token", "null").limit(1).execute()
        if not free.data:
            continue
        sb.table("data_detective_pairs").update({
            "session_token": st.session_state.token,
            "joined_at": now_iso(),
        }).eq("round_no", round_no).eq("pair_no", n).is_("session_token", "null").execute()
        check = sb.table("data_detective_pairs").select("*").eq("round_no", round_no).eq("pair_no", n).limit(1).execute()
        if check.data and check.data[0].get("session_token") == st.session_state.token:
            return check.data[0], None
    return None, "All 12 data_detective_pairs are already occupied."

def db_submit_think(pair_no, answer):
    state = db_get_state()
    sb.table("data_detective_pairs").update({
        "think_answer": answer,
        "think_submitted_at": now_iso()
    }).eq("round_no", int(state["round_no"])).eq("pair_no", pair_no).execute()

def db_submit_share(pair_no, text):
    state = db_get_state()
    sb.table("data_detective_pairs").update({
        "share_text": text.strip(),
        "share_submitted_at": now_iso()
    }).eq("round_no", int(state["round_no"])).eq("pair_no", pair_no).execute()

def db_reset_round():
    state = db_get_state()
    new_round = int(state["round_no"]) + 1
    sb.table("data_detective_pairs").delete().eq("round_no", new_round).execute()
    rows = [{"round_no": new_round, "pair_no": n} for n in range(1, 13)]
    sb.table("data_detective_pairs").insert(rows).execute()
    sb.table("data_detective_state").update({
        "round_no": new_round, "stage": "WAITING",
        "stage_started_at": now_iso(), "updated_at": now_iso()
    }).eq("id", 1).execute()

def local_demo_state():
    return {"id": 1, "stage": st.session_state.get("demo_stage", "WAITING"), "round_no": 1}

# ---------- Helpers ----------
def join_url():
    if APP_URL:
        return APP_URL.rstrip("/") + "/?role=student"
    try:
        host = st.context.headers.get("Host")
        if host:
            return ("https://" if "localhost" not in host else "http://") + host + "/?role=student"
    except Exception:
        pass
    return ""

@st.cache_data
def make_qr(url):
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def answer_counts(data_detective_pairs):
    counts = {x: 0 for x in OPTIONS}
    for p in data_detective_pairs:
        a = p.get("think_answer")
        if a in counts:
            counts[a] += 1
    return counts

def stage_label(stage):
    return {"WAITING":"WAITING ROOM", "THINK":"THINK", "PAIR":"PAIR", "SHARE":"SHARE", "REVEAL":"REVEAL"}.get(stage, stage)

# ---------- Session ----------
if "token" not in st.session_state:
    st.session_state.token = str(uuid.uuid4())
if "pair" not in st.session_state:
    st.session_state.pair = None

role = st.query_params.get("role", "home")
if isinstance(role, list):
    role = role[0]

# ---------- Home ----------
if role == "home":
    st.markdown("""
    <div class="hero">
      <h1>📊 Data Detective — Live Classroom Challenge</h1>
      <p>Teacher controls the room • Students join by QR • 12 12 pairs maximum</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 👨‍🏫 Teacher")
        if st.button("Open Teacher / Projector", type="primary", use_container_width=True):
            st.query_params["role"] = "teacher"
            st.rerun()
    with c2:
        st.markdown("### 👩‍🎓 Student")
        if st.button("Join as Student", use_container_width=True):
            st.query_params["role"] = "student"
            st.rerun()
    if not sb:
        st.warning("Demo mode: Supabase is not configured. Configure the included secrets before using multiple phones.")

# ---------- Teacher ----------
elif role == "teacher":
    state = db_get_state() if sb else local_demo_state()
    if not state:
        st.error("Supabase is configured but the database schema has not been initialized.")
        st.stop()

    stage = state["stage"]
    data_detective_pairs = db_get_data_detective_pairs() if sb else []
    joined = sum(1 for p in data_detective_pairs if p.get("session_token"))

    st.markdown(f"""
    <div class="hero">
      <h1>📊 DATA DETECTIVE</h1>
      <p>Round {state["round_no"]} • {stage_label(stage)}</p>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([0.9, 1.1], gap="large")

    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="dataset-title">📋 DATASET — MONTHLY ATTENDANCE</div>', unsafe_allow_html=True)
        import pandas as pd
        st.dataframe(pd.DataFrame({"Month": list(DATA), "Attendance (%)": list(DATA.values())}),
                     hide_index=True, use_container_width=True)
        st.markdown(f"""
        <div style="margin-top:30px">
          <div class="muted">PAIRS JOINED</div>
          <div class="big-stat">{joined} <span style="font-size:25px">/ 12</span></div>
        </div>
        """, unsafe_allow_html=True)

        if stage == "WAITING":
            url = join_url()
            if url:
                st.markdown('<div class="qr-wrap" style="margin-top:20px"><b>SCAN TO JOIN</b></div>', unsafe_allow_html=True)
                st.image(make_qr(url), width=230)
                st.caption("Students can also use the Student button on this page.")
            else:
                st.info("Set APP_URL in secrets to display a QR code.")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        if stage == "WAITING":
            st.markdown('<div class="stage">Waiting</div>', unsafe_allow_html=True)
            st.markdown('<div class="question">Get your pairs ready.<br>Scan the QR code to join.</div>', unsafe_allow_html=True)
            st.info("Maximum: 12 pairs • One device per pair")
        elif stage == "THINK":
            st.markdown('<div class="stage">Think — 30 seconds</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="question">{QUESTION}<br><br>Which visualization should we use?</div>', unsafe_allow_html=True)
            counts = answer_counts(data_detective_pairs)
            for k, v in counts.items():
                st.markdown(f'<div class="answer-card"><b>{k}</b><span style="float:right">{v}</span></div>', unsafe_allow_html=True)
        elif stage == "PAIR":
            st.markdown('<div class="stage">Pair — 30 seconds</div>', unsafe_allow_html=True)
            st.markdown('<div class="question">Discuss with your partner:<br>Why is this visualization the best choice?</div>', unsafe_allow_html=True)
            counts = answer_counts(data_detective_pairs)
            st.markdown(f"**Responses received:** {sum(counts.values())} / {joined}")
        elif stage == "SHARE":
            st.markdown('<div class="stage">Share</div>', unsafe_allow_html=True)
            st.markdown('<div class="question">Give your final reasoning.<br>What conclusion can we draw?</div>', unsafe_allow_html=True)
            texts = [p.get("share_text") for p in data_detective_pairs if p.get("share_text")]
            st.markdown(f"**Responses received:** {len(texts)} / {joined}")
            for t in texts[-8:]:
                st.markdown(f'<div class="answer-card">{t}</div>', unsafe_allow_html=True)
        elif stage == "REVEAL":
            st.markdown('<div class="stage">Reveal</div>', unsafe_allow_html=True)
            st.markdown('<div class="question">✓ Correct visualization: LINE CHART</div>', unsafe_allow_html=True)
            st.success(CONCLUSION)
            st.markdown("**Why?** A line chart clearly shows change over time.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    b1,b2,b3,b4,b5 = st.columns(5)
    actions = [
        ("▶ START THINK", "THINK"),
        ("▶ START PAIR", "PAIR"),
        ("▶ OPEN SHARE", "SHARE"),
        ("✓ REVEAL", "REVEAL"),
    ]
    for col, (label, target) in zip([b1,b2,b3,b4], actions):
        with col:
            if st.button(label, type="primary" if target == "REVEAL" else "secondary", use_container_width=True):
                if sb:
                    db_update_state(stage=target)
                else:
                    st.session_state.demo_stage = target
                st.rerun()
    with b5:
        if st.button("↻ NEW ROUND", use_container_width=True):
            if sb:
                db_reset_round()
            else:
                st.session_state.demo_stage = "WAITING"
            st.rerun()

    # Auto-refresh without rebuilding the whole page manually.
    try:
        st.fragment(run_every=1)(lambda: None)
    except Exception:
        pass

# ---------- Student ----------
elif role == "student":
    state = db_get_state() if sb else local_demo_state()
    if not state:
        st.error("Database is not initialized.")
        st.stop()

    st.markdown("""
    <div class="hero">
      <h1>📊 DATA DETECTIVE</h1>
      <p>One device per pair</p>
    </div>
    """, unsafe_allow_html=True)

    if not sb:
        st.warning("Student demo mode. Configure Supabase for real multi-device classroom use.")
        st.stop()

    if not st.session_state.pair:
        st.markdown("### Join the classroom")
        st.caption("Enter the teacher PIN to claim one of the 12 pair slots.")
        pin = st.text_input("Teacher PIN", type="password", max_chars=20)
        if st.button("JOIN CLASS", type="primary", use_container_width=True):
            if pin != TEACHER_PIN:
                st.error("Incorrect PIN.")
            else:
                pair, err = db_join_pair()
                if err:
                    st.error(err)
                else:
                    st.session_state.pair = pair["pair_no"]
                    st.rerun()
        st.stop()

    pair_no = st.session_state.pair
    stage = state["stage"]

    st.markdown(f"### Pair {pair_no}  •  {stage_label(stage)}")

    if stage == "WAITING":
        st.info("Wait for the teacher to start the THINK stage.")
    elif stage == "THINK":
        st.markdown(f"## {QUESTION}")
        st.markdown("### Which visualization should we use?")
        answer = st.radio("Choose one", OPTIONS, index=None)
        if st.button("SUBMIT THINK ANSWER", type="primary", use_container_width=True):
            if answer:
                db_submit_think(pair_no, answer)
                st.success("Answer submitted. Wait for the next stage.")
            else:
                st.warning("Choose an option first.")
    elif stage == "PAIR":
        st.markdown("## Discuss with your partner")
        st.markdown("### Why is your chosen visualization the best choice?")
        st.info("Do not submit yet. Discuss first.")
    elif stage == "SHARE":
        st.markdown("## Final answer")
        st.markdown("### What conclusion can we draw?")
        text = st.text_area("Write your pair's answer", height=160, max_chars=500)
        if st.button("SUBMIT FINAL ANSWER", type="primary", use_container_width=True):
            if text.strip():
                db_submit_share(pair_no, text)
                st.success("Final answer submitted.")
            else:
                st.warning("Please enter your answer.")
    elif stage == "REVEAL":
        st.markdown("## ✓ Correct answer")
        st.success("LINE CHART")
        st.markdown(f"### {CONCLUSION}")
        st.markdown("**Reason:** The data are ordered by month, so a line chart shows the trend over time.")

    try:
        st.fragment(run_every=1)(lambda: None)
    except Exception:
        pass
else:
    st.query_params["role"] = "home"
    st.rerun()
