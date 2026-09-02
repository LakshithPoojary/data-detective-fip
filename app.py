import streamlit as st
import time
from collections import Counter

st.set_page_config(page_title="Data Detective", page_icon="🔎", layout="wide")

DATA = [("Jan", 75), ("Feb", 80), ("Mar", 78), ("Apr", 85), ("May", 90)]
MAX_PAIRS = 12

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:Inter,Arial,sans-serif}
.stApp{background:#f5f8fb}
.block-container{max-width:1600px;padding:18px 28px 30px}
.top{display:flex;justify-content:space-between;align-items:center;background:#102a43;color:white;border-radius:22px;padding:20px 28px;margin-bottom:18px}
.brand{font-size:clamp(1.5rem,2.7vw,3rem);font-weight:900}
.round{font-size:clamp(.9rem,1.3vw,1.3rem);font-weight:800}
.stagebar{display:flex;gap:10px;justify-content:center;margin-bottom:12px}
.stagepill{padding:9px 18px;border-radius:999px;border:2px solid #d9e2ec;background:white;font-weight:900;color:#627d98}
.active{background:#1f6feb;border-color:#1f6feb;color:white}
.timer{font-size:clamp(2.8rem,6vw,6rem);font-weight:900;line-height:.9;text-align:center;color:#102a43;margin:8px 0 16px}
.panel{background:white;border:2px solid #d9e2ec;border-radius:22px;padding:24px;height:100%;box-shadow:0 5px 18px rgba(16,42,67,.05)}
.paneltitle{font-size:clamp(1rem,1.4vw,1.35rem);font-weight:900;letter-spacing:.05em;color:#627d98;text-transform:uppercase}
.question{font-size:clamp(1.7rem,3.2vw,3.8rem);font-weight:900;line-height:1.08;color:#102a43;margin:18px 0 26px}
.data-table{width:100%;border-collapse:collapse;font-size:clamp(1.1rem,1.7vw,1.7rem)}
.data-table th{background:#edf3f8;text-align:left}
.data-table th,.data-table td{padding:12px 16px;border-bottom:1px solid #d9e2ec}
.join{font-size:clamp(1.4rem,2.3vw,2.4rem);font-weight:900;text-align:center;margin-top:20px;color:#102a43}
.join small{display:block;font-size:.55em;color:#627d98;letter-spacing:.08em}
.answer-card{border:3px solid #d9e2ec;border-radius:18px;padding:16px 20px;margin:10px 0;background:white}
.answer-label{font-size:clamp(1.2rem,1.8vw,1.7rem);font-weight:900}
.answer-count{float:right;font-size:clamp(1.4rem,2vw,2rem);font-weight:900;color:#1f6feb}
.reason{font-size:clamp(1.1rem,1.6vw,1.5rem);line-height:1.4;color:#627d98}
.reveal{background:#102a43;color:white;border-radius:24px;padding:28px;text-align:center}
.reveal h1{font-size:clamp(3rem,7vw,7rem);margin:0;font-weight:900}
.reveal p{font-size:clamp(1.2rem,2vw,2rem)}
div.stButton>button{min-height:3.5rem;font-size:1.08rem;font-weight:900;border-radius:14px}
textarea{font-size:1.1rem!important}
@media(max-width:900px){.block-container{padding:10px 12px 24px}.panel{padding:18px}.stagebar{gap:5px}.stagepill{padding:8px 10px}}
</style>
""", unsafe_allow_html=True)

def ensure():
    defaults={"stage":"WAITING","started":None,"round":1,"joined":0,"answers":{},"shares":{}}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
ensure()

def elapsed():
    return 0 if st.session_state.started is None else int(time.time()-st.session_state.started)

def set_stage(stage):
    st.session_state.stage=stage
    st.session_state.started=time.time()

def reset_round():
    st.session_state.stage="WAITING"
    st.session_state.started=None
    st.session_state.joined=0
    st.session_state.answers={}
    st.session_state.shares={}
    st.session_state.round+=1

def header():
    st.markdown(f"""<div class="top"><div class="brand">🔎 DATA DETECTIVE</div>
    <div class="round">THINK • PAIR • SHARE &nbsp; | &nbsp; ROUND {st.session_state.round}</div></div>""",unsafe_allow_html=True)

def stages():
    cur=st.session_state.stage
    html='<div class="stagebar">'
    for s in ["THINK","PAIR","SHARE","REVEAL"]:
        html+=f'<div class="stagepill {"active" if cur==s else ""}">{s}</div>'
    st.markdown(html+"</div>",unsafe_allow_html=True)

def dataset():
    rows="".join(f"<tr><td>{m}</td><td><b>{v}</b></td></tr>" for m,v in DATA)
    return f"""<div class="panel">
    <div class="paneltitle">Dataset</div>
    <div style="font-size:clamp(1.5rem,2.2vw,2.4rem);font-weight:900;margin:10px 0 14px">Monthly Attendance</div>
    <table class="data-table"><tr><th>Month</th><th>Attendance</th></tr>{rows}</table>
    <div class="join">👥 {st.session_state.joined} / {MAX_PAIRS}<small>PAIRS JOINED</small></div>
    </div>"""

def projector():
    header(); stages()
    stage=st.session_state.stage
    if stage in ("THINK","PAIR"):
        left=max(0,30-elapsed())
        st.markdown(f'<div class="timer">{left:02d}</div>',unsafe_allow_html=True)
        if left==0:
            set_stage("PAIR" if stage=="THINK" else "SHARE")
            st.rerun()
    elif stage=="SHARE":
        st.markdown('<div class="timer">SHARE</div>',unsafe_allow_html=True)

    left,right=st.columns([.9,1.35],gap="large")
    with left:
        st.markdown(dataset(),unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">',unsafe_allow_html=True)
        if stage=="WAITING":
            st.markdown('<div class="paneltitle">READY</div><div class="question">Scan the QR and join your pair.</div>',unsafe_allow_html=True)
        elif stage=="THINK":
            st.markdown('<div class="paneltitle">THINK</div><div class="question">Which visualization should we use?</div>',unsafe_allow_html=True)
            c=Counter(st.session_state.answers.values())
            for x in ["Line","Bar","Pie"]:
                st.markdown(f'<div class="answer-card"><span class="answer-label">{x}</span><span class="answer-count">{c[x]}</span></div>',unsafe_allow_html=True)
        elif stage=="PAIR":
            st.markdown('<div class="paneltitle">PAIR</div><div class="question">Why did you choose that visualization?</div><div class="reason">Discuss with your partner. Prepare one clear reason to share.</div>',unsafe_allow_html=True)
        elif stage=="SHARE":
            st.markdown('<div class="paneltitle">SHARE</div><div class="question">Which chart? Why?</div>',unsafe_allow_html=True)
            texts=list(st.session_state.shares.values())
            if texts:
                words=[]
                for t in texts:
                    words += [w.strip(".,!?;:()[]").lower() for w in t.split() if len(w.strip(".,!?;:()[]"))>2]
                common=Counter(words).most_common(18)
                st.markdown(" ".join(f"**{w}** ×{n}&nbsp;&nbsp;" for w,n in common),unsafe_allow_html=True)
                st.markdown(f'<div class="reason"><b>{len(texts)}</b> pairs have shared.</div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="reason">Waiting for pair responses…</div>',unsafe_allow_html=True)
        else:
            st.markdown("""<div class="reveal"><div style="font-weight:900;letter-spacing:.12em">CORRECT VISUALIZATION</div>
            <h1>LINE</h1><p><b>Why?</b> The data changes across an ordered sequence of months.</p>
            <p><b>Interpretation:</b> Attendance trends upward overall, with a small dip in March before recovering.</p></div>""",unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

    st.markdown("---")
    a,b,c,d,e=st.columns(5)
    if a.button("▶ START THINK",use_container_width=True,disabled=stage not in ("WAITING","REVEAL")):
        if stage=="REVEAL": reset_round()
        set_stage("THINK"); st.rerun()
    if b.button("▶ START PAIR",use_container_width=True,disabled=stage!="THINK"):
        set_stage("PAIR"); st.rerun()
    if c.button("▶ OPEN SHARE",use_container_width=True,disabled=stage!="PAIR"):
        set_stage("SHARE"); st.rerun()
    if d.button("★ REVEAL",use_container_width=True,disabled=stage!="SHARE"):
        set_stage("REVEAL"); st.rerun()
    if e.button("↺ NEW ROUND",use_container_width=True,disabled=stage!="REVEAL"):
        reset_round(); st.rerun()

def student():
    header(); stages()
    if "pair_no" not in st.session_state:
        st.markdown('<div class="question">Choose your pair number</div>',unsafe_allow_html=True)
        cols=st.columns(3)
        for i in range(1,13):
            with cols[(i-1)%3]:
                if st.button(f"PAIR {i:02d}",use_container_width=True):
                    if st.session_state.joined<MAX_PAIRS:
                        st.session_state.pair_no=i
                        st.session_state.joined+=1
                        st.rerun()
        return
    p=st.session_state.pair_no
    stage=st.session_state.stage
    st.markdown(f'<div class="join">PAIR {p:02d}<small>YOUR TEAM</small></div>',unsafe_allow_html=True)
    if stage=="WAITING":
        st.info("Waiting for the teacher to start THINK.")
    elif stage=="THINK":
        rem=max(0,30-elapsed())
        st.markdown(f'<div class="timer">{rem:02d}</div>',unsafe_allow_html=True)
        st.markdown('<div class="question">Which visualization should we use?</div>',unsafe_allow_html=True)
        choice=st.radio("Choose",["Line","Bar","Pie"],label_visibility="collapsed")
        if st.button("LOCK MY ANSWER",use_container_width=True):
            st.session_state.answers[p]=choice; st.rerun()
        if p in st.session_state.answers: st.success("Answer locked.")
    elif stage=="PAIR":
        st.markdown('<div class="question">Discuss your choice.</div>',unsafe_allow_html=True)
        st.markdown('<div class="reason">Prepare one clear reason to share.</div>',unsafe_allow_html=True)
    elif stage=="SHARE":
        st.markdown('<div class="question">Which chart? Why?</div>',unsafe_allow_html=True)
        if p in st.session_state.shares: st.success("✓ Shared with teacher.")
        else:
            txt=st.text_area("Final answer",placeholder="Line chart — because attendance changes month by month.",height=140)
            if st.button("SUBMIT SHARE",use_container_width=True) and txt.strip():
                st.session_state.shares[p]=txt.strip(); st.rerun()
    else:
        st.markdown('<div class="reveal"><div>ANSWER</div><h1>LINE</h1><p>Attendance trends upward overall, with a small dip in March.</p></div>',unsafe_allow_html=True)

role=st.query_params.get("role","teacher")
if isinstance(role,list): role=role[0]
if role=="student": student()
else: projector()
