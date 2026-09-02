import io
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from PIL import Image
import qrcode
from wordcloud import WordCloud

st.set_page_config(page_title="Data Detective • Think–Pair–Share", page_icon="🔎", layout="wide", initial_sidebar_state="collapsed")

MAX_PAIRS = 12
THINK_SECONDS = 30
PAIR_SECONDS = 30
CHARTS = ["Line", "Bar", "Pie", "Histogram", "Scatter"]
INTERPRETATIONS = [
    "Continuous increase",
    "Increase with a dip",
    "Continuous decrease",
]
ATTENDANCE = {"June": 60, "July": 65, "August": 72, "September": 68, "October": 80}

# ---------- secrets / database ----------
def secret_or_env(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)

SUPABASE_URL = secret_or_env("SUPABASE_URL", "")
SUPABASE_KEY = secret_or_env("SUPABASE_KEY", "")
TEACHER_PIN = str(secret_or_env("TEACHER_PIN", "1234"))
APP_URL = str(secret_or_env("APP_URL", "")).strip()

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

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def state():
    return db.table("session_state").select("*").eq("id", 1).single().execute().data

def pairs():
    return db.table("pairs").select("*").order("pair_no").execute().data or []

def pair(no):
    return db.table("pairs").select("*").eq("pair_no", no).single().execute().data

def update_state(**kwargs):
    db.table("session_state").update(kwargs).eq("id", 1).execute()

def set_stage(stage):
    update_state(stage=stage, stage_started_at=now_iso())

def clear_answers():
    db.table("pairs").update({
        "think_answer": None, "think_submitted_at": None,
        "share_text": None, "share_submitted_at": None,
        "interpretation_answer": None, "interpretation_submitted_at": None,
    }).gte("pair_no", 1).lte("pair_no", MAX_PAIRS).execute()

def reset_class():
    db.table("pairs").update({
        "joined": False, "joined_at": None,
        "think_answer": None, "think_submitted_at": None,
        "share_text": None, "share_submitted_at": None,
        "interpretation_answer": None, "interpretation_submitted_at": None,
    }).gte("pair_no", 1).lte("pair_no", MAX_PAIRS).execute()
    update_state(stage="WAITING", stage_started_at=None, round_no=1)

def join_pair(no):
    result = (db.table("pairs").update({"joined": True, "joined_at": now_iso()})
              .eq("pair_no", no).eq("joined", False).execute())
    return bool(result.data)

def submit_think(no, answer):
    db.table("pairs").update({"think_answer": answer, "think_submitted_at": now_iso()}).eq("pair_no", no).execute()

def submit_share(no, text):
    db.table("pairs").update({"share_text": text.strip(), "share_submitted_at": now_iso()}).eq("pair_no", no).execute()

def submit_interpretation(no, answer):
    db.table("pairs").update({"interpretation_answer": answer, "interpretation_submitted_at": now_iso()}).eq("pair_no", no).execute()

def elapsed(s):
    if not s.get("stage_started_at"):
        return 0
    try:
        dt = datetime.fromisoformat(s["stage_started_at"].replace("Z", "+00:00"))
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    except Exception:
        return 0

def remaining(s):
    limit = THINK_SECONDS if s["stage"] == "THINK" else PAIR_SECONDS
    return max(0, limit - elapsed(s))

# ---------- styling ----------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:Inter,sans-serif}
.block-container{padding-top:1.1rem;padding-bottom:2rem;max-width:1500px}
.hero{border-radius:24px;padding:28px 34px;margin-bottom:18px;background:linear-gradient(135deg,#0b1f3a,#173e6d 55%,#245b91);color:white;box-shadow:0 10px 30px rgba(11,31,58,.18)}
.eyebrow{font-size:1rem;letter-spacing:.14em;font-weight:900;opacity:.8}.hero h1{font-size:clamp(2.2rem,4.5vw,4.8rem);line-height:1;margin:8px 0 12px;font-weight:900}.hero p{font-size:clamp(1rem,1.7vw,1.45rem);margin:0;opacity:.94}
.stage{border-radius:20px;padding:18px 24px;margin:14px 0;border:2px solid #dbe5ef;background:#f7fafc}.stage-name{font-size:clamp(1.6rem,3vw,3.2rem);font-weight:900}.timer{font-size:clamp(2.8rem,6vw,5.8rem);font-weight:900;line-height:1;text-align:center}
.status-grid{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:14px}.slot{border:2px solid #dbe5ef;border-radius:16px;padding:16px;min-height:110px;background:white}.slot .num{font-size:1rem;font-weight:900;opacity:.6}.slot .state{font-size:1.25rem;font-weight:800;margin-top:8px}.slot .sub{font-size:.95rem;opacity:.68;margin-top:3px}
.metric{border-radius:18px;padding:18px;background:white;border:2px solid #dbe5ef;text-align:center;min-height:105px}.metric .big{font-size:clamp(2rem,4vw,3.5rem);font-weight:900;line-height:1}.metric .label{font-size:1rem;font-weight:700;opacity:.68;margin-top:8px}
.data-table{width:100%;border-collapse:collapse;font-size:1.45rem;background:white;border-radius:14px;overflow:hidden}.data-table th,.data-table td{padding:14px 18px;border:1px solid #dbe5ef;text-align:center}.data-table th{font-weight:900;background:#eef4f9}.question{font-size:clamp(1.4rem,2.5vw,2.3rem);font-weight:900;margin:8px 0 16px}.choice{border:2px solid #dbe5ef;border-radius:18px;padding:18px;text-align:center;background:white;font-size:1.2rem;font-weight:800}.answer-count{font-size:clamp(2rem,4vw,4rem);font-weight:900;text-align:center}.small-note{font-size:1rem;opacity:.7}
div.stButton>button,div[data-testid="stFormSubmitButton"]>button{min-height:3.3rem;font-size:1.05rem;font-weight:800;border-radius:14px}textarea,input{font-size:1.08rem!important}
@media(max-width:800px){.block-container{padding:.8rem .8rem 1.5rem}.status-grid{grid-template-columns:repeat(2,minmax(120px,1fr));gap:10px}.hero{padding:20px;border-radius:18px}.data-table{font-size:1rem}.data-table th,.data-table td{padding:10px 8px}.question{font-size:1.4rem}}
</style>
"""

def ui(projector=False, student=False):
    extra=""
    if projector:
        extra="""
        <style>
        .block-container{max-width:1700px;padding:1.4rem 2.5rem 3rem}.hero{padding:36px 44px}.hero h1{font-size:clamp(3.2rem,6vw,6.5rem)}.hero p{font-size:clamp(1.35rem,2vw,2rem)}.eyebrow{font-size:1.3rem}.stage{padding:24px 32px}.stage-name{font-size:clamp(2.5rem,4vw,4.8rem)}.status-grid{grid-template-columns:repeat(4,1fr);gap:18px}.slot{min-height:145px;padding:20px}.slot .num{font-size:1.3rem}.slot .state{font-size:1.7rem}.slot .sub{font-size:1.15rem}.metric{min-height:135px;padding:24px}.metric .big{font-size:clamp(3rem,5vw,5.5rem)}.metric .label{font-size:1.25rem}.data-table{font-size:1.8rem}.data-table th,.data-table td{padding:18px}.question{font-size:2.1rem}div.stButton>button{min-height:4.2rem;font-size:1.3rem}
        </style>"""
    if student:
        extra="""
        <style>
        .block-container{max-width:720px;margin:auto;padding:1rem 1rem 2rem}.hero h1{font-size:clamp(2rem,8vw,3.3rem)}.hero p{font-size:clamp(1rem,4vw,1.35rem)}.stage-name{font-size:clamp(1.8rem,8vw,3rem)}.timer{font-size:clamp(3.2rem,16vw,5.5rem)}.data-table{font-size:1.1rem}.data-table th,.data-table td{padding:11px 7px}.question{font-size:1.45rem}.choice{padding:16px 10px;font-size:1.15rem}div.stButton>button,div[data-testid="stFormSubmitButton"]>button{min-height:3.8rem;font-size:1.1rem}
        </style>"""
    st.html(CSS+extra)

def hero(title, subtitle, eyebrow):
    st.html(f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>')

def dataset_table():
    rows=''.join(f'<tr><td>{m}</td><td><b>{v}</b></td></tr>' for m,v in ATTENDANCE.items())
    st.html(f'''<table class="data-table"><thead><tr><th>Month</th><th>Students</th></tr></thead><tbody>{rows}</tbody></table>''')

def qr(url):
    q=qrcode.QRCode(box_size=9,border=2);q.add_data(url);q.make(fit=True)
    im=q.make_image().convert("RGB");buf=io.BytesIO();im.save(buf,format="PNG");buf.seek(0);return buf

def wordcloud(texts):
    text=' '.join(x for x in texts if x)
    if not text.strip(): return None
    wc=WordCloud(width=1600,height=650,background_color='white',collocations=False,min_font_size=22).generate(text)
    buf=io.BytesIO();wc.to_image().save(buf,format='PNG');buf.seek(0);return Image.open(buf)

# ---------- teacher live content ----------
@st.fragment(run_every="1s")
def teacher_live():
    s=state(); ps=pairs(); stage=s["stage"]
    if stage in ("THINK","PAIR"):
        rem=remaining(s)
        if rem==0:
            set_stage("PAIR" if stage=="THINK" else "SHARE")
            st.rerun(scope="fragment");return
    else: rem=None

    joined=sum(bool(p["joined"]) for p in ps); think=sum(bool(p["think_submitted_at"]) for p in ps); share=sum(bool(p["share_submitted_at"]) for p in ps); interp=sum(bool(p["interpretation_submitted_at"]) for p in ps)
    st.html(f'<div class="stage"><div class="stage-name">CURRENT STAGE: {stage}</div>{f"<div class=\"timer\">{rem}s</div>" if rem is not None else ""}</div>')
    cols=st.columns(4)
    for col,(v,l) in zip(cols,[(joined,"PAIRS JOINED"),(think,"CHART ANSWERS"),(share,"SHARED REASONS"),(interp,"INTERPRETATIONS")]):
        with col: st.html(f'<div class="metric"><div class="big">{v}</div><div class="label">{l}</div></div>')

    st.markdown("### Dataset")
    dataset_table()
    st.html('<div class="question">Which visualization is most suitable for this data?</div>')

    st.markdown("### Pair Status")
    cards=[]
    for p in ps:
        if not p["joined"]: status,sub="AVAILABLE","Waiting"
        elif p["share_submitted_at"]: status,sub="SHARED ✓","Reason received"
        elif p["think_submitted_at"]: status,sub="CHART ✓","Choice locked"
        elif p["interpretation_submitted_at"]: status,sub="INTERPRET ✓","Response received"
        else: status,sub="JOINED","Working…"
        cards.append(f'<div class="slot"><div class="num">PAIR {p["pair_no"]:02d}</div><div class="state">{status}</div><div class="sub">{sub}</div></div>')
    st.html('<div class="status-grid">'+''.join(cards)+'</div>')

    if stage in ("SHARE","INTERPRET","REVEAL"):
        st.markdown("### Live Share Wall")
        img=wordcloud([p["share_text"] for p in ps if p["share_text"]])
        if img: st.image(img,use_container_width=True)
        else: st.html('<div class="stage" style="min-height:180px;text-align:center;padding-top:60px"><b style="font-size:1.5rem;opacity:.55">Waiting for pair reasons…</b></div>')

    if stage in ("INTERPRET","REVEAL"):
        st.markdown("### Interpretation")
        st.html('<div class="question">What do you interpret from the data?</div>')
        st.html('<div class="choice">A • Continuous increase</div><br><div class="choice">B • Increase with a dip</div><br><div class="choice">C • Continuous decrease</div>')

    if stage=="REVEAL":
        chart_correct=sum(p.get("think_answer")=="Line" for p in ps if p.get("joined"))
        interp_correct=sum(p.get("interpretation_answer")=="Increase with a dip" for p in ps if p.get("joined"))
        total=joined
        st.markdown("### Reveal")
        a,b=st.columns(2)
        with a: st.html(f'<div class="stage"><div style="font-size:1.3rem;font-weight:900">CORRECT CHART</div><div class="answer-count">{chart_correct}/{total}</div><div style="text-align:center;font-size:1.15rem;font-weight:800">Line chart</div></div>')
        with b: st.html(f'<div class="stage"><div style="font-size:1.3rem;font-weight:900">CORRECT INTERPRETATION</div><div class="answer-count">{interp_correct}/{total}</div><div style="text-align:center;font-size:1.15rem;font-weight:800">Increase with a dip</div></div>')
        st.success("✓ Line chart — it shows change over an ordered sequence.")
        st.info("✓ Interpretation: Overall increase, with a dip in September before rising again in October.")
        df=pd.DataFrame({"Students":list(ATTENDANCE.values())},index=list(ATTENDANCE.keys()))
        st.line_chart(df,height=430)

# ---------- teacher ----------
def teacher_controls():
    s=state(); stage=s["stage"]
    st.markdown("---");st.markdown("### Teacher Controls")
    c1,c2,c3,c4,c5=st.columns(5)
    with c1:
        if st.button("▶ START THINK",use_container_width=True,disabled=stage not in ("WAITING","REVEAL")):
            if stage=="REVEAL": clear_answers()
            set_stage("THINK");st.rerun()
    with c2:
        if st.button("▶ START PAIR",use_container_width=True,disabled=stage!="THINK"):
            set_stage("PAIR");st.rerun()
    with c3:
        if st.button("▶ OPEN SHARE",use_container_width=True,disabled=stage!="PAIR"):
            set_stage("SHARE");st.rerun()
    with c4:
        if st.button("▶ OPEN INTERPRETATION",use_container_width=True,disabled=stage!="SHARE"):
            set_stage("INTERPRET");st.rerun()
    with c5:
        if st.button("★ REVEAL",use_container_width=True,disabled=stage!="INTERPRET"):
            set_stage("REVEAL");st.rerun()
    r1,r2=st.columns(2)
    with r1:
        if st.button("↺ RESET CLASS — CLEAR ALL 12",use_container_width=True):
            reset_class();st.rerun()
    with r2:
        if st.button("🧹 CLEAR ANSWERS — KEEP PAIRS",use_container_width=True,disabled=stage not in ("REVEAL","WAITING")):
            clear_answers();set_stage("WAITING");st.rerun()

    st.markdown("---");left,right=st.columns([1,1.2])
    with left:
        st.markdown("### Student Join QR")
        join_url=APP_URL or st.text_input("App URL",placeholder="https://your-app.streamlit.app")
        if join_url:
            pair_url=join_url.rstrip('/')+'/?role=pair'
            st.image(qr(pair_url),width=300);st.code(pair_url,language=None)
    with right:
        st.markdown("### Projector Mode")
        st.info("Use browser full-screen (F11). The teacher view uses oversized text and spacing for last-bench visibility.")

def teacher():
    ui(projector=True);hero("THINK • PAIR • SHARE • INTERPRET","Data Detective — from dataset → chart choice → reason → interpretation.","FIP • DATA VISUALIZATION WITH MATPLOTLIB")
    teacher_live();teacher_controls()

def login():
    ui(projector=True);hero("TEACHER CONTROL ROOM","Enter the teacher PIN to start the classroom activity.","FIP • DATA VISUALIZATION WITH MATPLOTLIB")
    pin=st.text_input("Teacher PIN",type="password",max_chars=20)
    if st.button("OPEN DASHBOARD",use_container_width=True):
        if pin==TEACHER_PIN: st.session_state.teacher_ok=True;st.rerun()
        else: st.error("Incorrect PIN.")

# ---------- student ----------
@st.fragment(run_every="1s")
def student_live():
    s=state();stage=s["stage"];no=st.session_state.get("pair_no")
    if not no:return
    p=pair(no)
    if not p or not p["joined"]: st.error("This pair slot is no longer active.");return
    rem=remaining(s) if stage in ("THINK","PAIR") else None
    st.html(f'<div class="stage"><div class="stage-name">PAIR {no:02d} • {stage}</div>{f"<div class=\"timer\">{rem}s</div>" if rem is not None else ""}</div>')
    st.markdown("### Dataset");dataset_table()

    if stage=="WAITING": st.info("Waiting for the teacher to start THINK.")
    elif stage=="THINK":
        st.html('<div class="question">Which visualization is most suitable for this data?</div>')
        if p["think_submitted_at"]: st.success(f'✓ Choice locked: {p["think_answer"]}')
        else:
            choice=st.radio("Choose one",CHARTS,label_visibility="collapsed")
            if st.button("LOCK CHART CHOICE",use_container_width=True): submit_think(no,choice);st.rerun(scope="fragment")
    elif stage=="PAIR":
        st.success("PAIR — discuss with your partner: Why did you choose that chart?")
        if p["think_answer"]: st.html(f'<div class="choice">Your locked chart: {p["think_answer"]}</div>')
        st.caption("Wait for the teacher to open SHARE.")
    elif stage=="SHARE":
        st.html('<div class="question">SHARE — reveal your pair\'s chart choice and why.</div>')
        if p["share_submitted_at"]: st.success("✓ Your answer has been submitted to the teacher.");st.html(f'<div class="choice">{p["share_text"]}</div>')
        else:
            with st.form("share_form"):
                text=st.text_area("Final response",placeholder="Line chart — because the data changes month by month.",height=150,max_chars=300)
                if st.form_submit_button("SUBMIT TO TEACHER",use_container_width=True):
                    if text.strip(): submit_share(no,text);st.rerun(scope="fragment")
                    else: st.warning("Please enter your response.")
    elif stage=="INTERPRET":
        st.html('<div class="question">What do you interpret from the data?</div>')
        if p["interpretation_submitted_at"]: st.success(f'✓ Interpretation locked: {p["interpretation_answer"]}')
        else:
            ans=st.radio("Interpretation",INTERPRETATIONS,label_visibility="collapsed")
            if st.button("SUBMIT INTERPRETATION",use_container_width=True): submit_interpretation(no,ans);st.rerun(scope="fragment")
    elif stage=="REVEAL":
        st.success("REVEAL")
        st.markdown("### ✓ Correct chart: LINE CHART")
        st.markdown("### ✓ Correct interpretation: INCREASE WITH A DIP")
        st.info("Overall attendance increases, with a dip in September before increasing again in October.")
        df=pd.DataFrame({"Students":list(ATTENDANCE.values())},index=list(ATTENDANCE.keys()))
        st.line_chart(df,height=330)

def student_join():
    ui(student=True);hero("JOIN YOUR PAIR","One device per pair. Choose your assigned slot.","DATA DETECTIVE")
    ps=pairs();available=[x["pair_no"] for x in ps if not x["joined"]]
    if not available: st.error("All 12 pair slots are occupied. Please ask the teacher.");return
    st.markdown("### Choose your pair number")
    cols=st.columns(3)
    for i in range(1,MAX_PAIRS+1):
        p=next((x for x in ps if x["pair_no"]==i),None);occ=bool(p and p["joined"])
        with cols[(i-1)%3]:
            if st.button(f"PAIR {i:02d}\n"+("OCCUPIED" if occ else "JOIN"),key=f"join_{i}",use_container_width=True,disabled=occ):
                if join_pair(i): st.session_state.pair_no=i;st.rerun()
                else: st.warning("That slot was just taken. Choose another.")
    st.html('<p class="small-note">Your teacher sees your pair immediately. Other pairs\' answers remain hidden until the reveal.</p>')

def student():
    if "pair_no" not in st.session_state: student_join()
    else:
        ui(student=True);hero("YOUR PAIR • YOUR ANSWER","Choose together, discuss, reveal, then interpret.","DATA DETECTIVE");student_live()

# ---------- main ----------
def setup():
    ui();hero("SETUP NEEDED","Connect the live classroom database before using the activity.","DATA DETECTIVE")
    st.error("Add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets, then restart the app.")

def main():
    role=st.query_params.get("role","teacher")
    if isinstance(role,list):role=role[0]
    if not db: setup();return
    if role=="pair": student();return
    if st.session_state.get("teacher_ok"): teacher()
    else: login()

if __name__=="__main__": main()
