from __future__ import annotations

from pathlib import Path
import io
import math
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="QueueMatch Local", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

BASE = Path(__file__).parent
ASSET = BASE / "assets" / "queuematch_hero.svg"
DATA_DIR = BASE / "data"

PALETTE = {
    "navy": "#163A63", "teal": "#0B9B93", "violet": "#5C5DE6", "amber": "#F2A33B",
    "ink": "#12243A", "muted": "#64748B", "paper": "#F7FAFC", "line": "#DCE5EE",
    "green": "#19A974", "red": "#E25555"
}


def css():
    st.markdown(f"""
    <style>
    :root {{ --ink:{PALETTE['ink']}; --muted:{PALETTE['muted']}; --line:{PALETTE['line']}; }}
    .stApp {{ background: linear-gradient(180deg,#f8fbff 0%,#f8fafc 45%,#ffffff 100%); color: var(--ink); }}
    [data-testid='stSidebar'] {{ background:#ffffff; border-right:1px solid var(--line); }}
    .block-container {{ max-width: 1480px; padding-top: 1.3rem; padding-bottom: 3rem; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; }}
    .brand {{ font-weight:800; font-size:1.15rem; color:var(--ink); letter-spacing:-.02em; }}
    .sub {{ font-size:.85rem; color:var(--muted); margin-top:2px; }}
    .ready {{ display:inline-flex; align-items:center; gap:8px; border:1px solid #cde7df; background:#f3fbf7; color:#13795b; padding:8px 14px; border-radius:999px; font-weight:800; font-size:.75rem; }}
    .dot {{ width:9px; height:9px; background:#26a86b; border-radius:50%; display:inline-block; }}
    .hero {{ border-radius:28px; padding:1.55rem 1.7rem; background:linear-gradient(115deg,#173e73 0%,#2f5f92 46%,#168e88 100%); color:#fff; box-shadow:0 20px 60px rgba(22,58,99,.18); min-height:300px; display:flex; align-items:center; }}
    .eyebrow {{ font-size:.78rem; letter-spacing:.14em; font-weight:800; opacity:.82; }}
    .hero h1 {{ font-size:2.7rem; line-height:1.02; margin:.5rem 0 .7rem; font-weight:850; }}
    .hero p {{ font-size:1.02rem; line-height:1.65; margin:0; color:#e7f2ff; max-width:780px; }}
    .pillrow {{ display:flex; gap:.55rem; flex-wrap:wrap; margin-top:1.1rem; }}
    .pill {{ padding:8px 12px; border-radius:999px; background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.20); font-weight:700; font-size:.78rem; }}
    .panel {{ background:#fff; border:1px solid var(--line); border-radius:22px; padding:1rem 1rem 1.1rem; box-shadow:0 10px 30px rgba(17,33,52,.05); }}
    .panel-title {{ font-size:1.05rem; font-weight:800; color:var(--ink); }}
    .small {{ color:var(--muted); font-size:.85rem; }}
    .metric {{ background:#fff; border:1px solid var(--line); border-radius:18px; padding:1rem; box-shadow:0 8px 22px rgba(17,33,52,.04); }}
    .metric-label {{ color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }}
    .metric-value {{ font-size:1.75rem; font-weight:850; color:var(--ink); margin-top:.25rem; }}
    .metric-note {{ color:var(--muted); font-size:.78rem; margin-top:.1rem; }}
    .notice {{ border-radius:16px; padding:14px 16px; background:#fff7e8; border:1px solid #f3d692; color:#6a4a09; font-size:.9rem; line-height:1.5; }}
    .score-badge {{ font-weight:800; padding:6px 10px; border-radius:999px; display:inline-block; font-size:.76rem; }}
    .footer {{ color:#7b8795; font-size:.78rem; text-align:center; padding:2rem 0 0; }}
    </style>
    """, unsafe_allow_html=True)


def load_csv(file) -> pd.DataFrame:
    """Read a CSV safely with clear user-facing errors."""
    try:
        df = pd.read_csv(file)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file, encoding="latin-1")
        except Exception as exc:
            raise ValueError(f"Could not decode CSV: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Could not read CSV: {exc}") from exc
    if df.empty:
        raise ValueError("CSV contains headers but no data rows.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def nscore(v: float, lo: float, hi: float) -> float:
    if pd.isna(v):
        return 50.0
    try:
        v = float(v)
        lo = float(lo)
        hi = float(hi)
    except (TypeError, ValueError):
        return 50.0
    if hi <= lo:
        return 50.0
    return float(np.clip((v - lo) / (hi - lo) * 100, 0, 100))


def parse_binary(value, default=0) -> int:
    """Normalize common yes/no, true/false, 1/0 representations."""
    if pd.isna(value):
        return int(default)
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return int(float(value) != 0)
    token = str(value).strip().casefold()
    if token in {"1", "true", "yes", "y", "available", "verified"}:
        return 1
    if token in {"0", "false", "no", "n", "unavailable", "not verified"}:
        return 0
    return int(default)


def parse_date(value):
    """Return a normalized pandas Timestamp or NaT; never a datetime.date."""
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    return pd.Timestamp(ts).normalize()


def safe_days_since(value, reference=None):
    """Compute elapsed whole days using Timestamp-to-Timestamp arithmetic only."""
    ts = parse_date(value)
    ref = parse_date(reference) if reference is not None else pd.Timestamp.now().normalize()
    if pd.isna(ts) or pd.isna(ref):
        return None
    return int((ref - ts).days)


def clean_text(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def urgency_fit(slot: str, cand: str) -> float:
    rank = {"Emergency":4,"High":3,"Standard":2,"Routine":1}
    s, c = rank.get(slot,2), rank.get(cand,2)
    if c >= s: return 100.0
    if c == s-1: return 70.0
    return 35.0


def score_match(slot, cand) -> tuple[float, list[str], str]:
    reasons = []
    slot_service = clean_text(slot.service_line).casefold()
    cand_service = clean_text(cand.service_line).casefold()
    if slot_service != cand_service:
        return 0.0, ["Service-line mismatch"], "No Match"

    slot_verification_required = parse_binary(slot.verification_required)
    cand_verified = parse_binary(cand.verified)
    cand_available_today = parse_binary(cand.available_today)
    cand_contactable = parse_binary(cand.contactable)

    if slot_verification_required and cand_verified != 1:
        return 0.0, ["Verification requirement not met"], "No Match"

    try:
        travel_minutes = float(cand.travel_minutes)
    except (TypeError, ValueError):
        travel_minutes = float("nan")
    try:
        max_travel = float(slot.max_travel_minutes)
    except (TypeError, ValueError):
        max_travel = float("nan")
    if pd.notna(travel_minutes) and pd.notna(max_travel) and travel_minutes > max_travel:
        return 0.0, ["Travel time exceeds slot ceiling"], "No Match"

    slot_date = parse_date(slot.slot_date)
    earliest_date = parse_date(cand.earliest_date)
    if pd.notna(slot_date) and pd.notna(earliest_date) and earliest_date > slot_date:
        return 0.0, ["Candidate not available by slot date"], "No Match"
    if pd.isna(slot_date):
        reasons.append("Slot date is missing; date feasibility was not scored")
    if pd.isna(earliest_date):
        reasons.append("Candidate availability date is missing; date feasibility was not scored")

    uf = urgency_fit(clean_text(slot.urgency_tier), clean_text(cand.urgency_tier))
    tf = 65.0 if pd.isna(travel_minutes) else 100 - nscore(travel_minutes, 0, max(max_travel, 1) if pd.notna(max_travel) else max(travel_minutes, 1))
    try:
        rf = float(np.clip(float(cand.readiness_score), 0, 100))
    except (TypeError, ValueError):
        rf = 50.0
        reasons.append("Readiness score is missing; neutral readiness applied")

    vf = 100 if cand_verified == 1 and cand_available_today == 1 else 55 if cand_verified == 1 else 0
    freshness_days = safe_days_since(cand.last_updated)
    freshness = 100 if freshness_days is not None and 0 <= freshness_days <= 1 else 90 if freshness_days is not None and 0 <= freshness_days <= 7 else 75 if freshness_days is not None else 60
    contact = 100 if cand_contactable == 1 else 25
    score = 0.30 * uf + 0.20 * 100 + 0.15 * tf + 0.15 * rf + 0.15 * vf + 0.05 * ((freshness + contact) / 2)

    if uf < 70: reasons.append("Urgency tier is lower than slot urgency")
    if pd.notna(travel_minutes) and pd.notna(max_travel) and travel_minutes > 0.8 * max_travel: reasons.append("Travel time is near the operational ceiling")
    try:
        readiness_required = float(slot.readiness_required)
    except (TypeError, ValueError):
        readiness_required = 60.0
    if rf < readiness_required: reasons.append("Readiness is below the slot target")
    if cand_available_today == 0: reasons.append("Same-day availability is limited")
    try:
        prior_declines = int(float(cand.prior_declines))
    except (TypeError, ValueError):
        prior_declines = 0
    if prior_declines >= 2: reasons.append("Prior declines suggest confirmation risk")
    if cand_contactable == 0: reasons.append("Candidate contactability needs confirmation")
    if freshness_days is None: reasons.append("Last-updated date is missing; freshness scored conservatively")
    elif freshness_days < 0: reasons.append("Last-updated date is in the future; freshness scored conservatively")
    if not reasons: reasons.append("Strong operational fit across urgency, service, travel and readiness")
    band = "Preferred" if score >= 85 else "Suitable" if score >= 70 else "Backup" if score >= 55 else "Review"
    return round(float(score), 1), reasons, band


def build_matches(slots: pd.DataFrame, waitlist: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _,s in slots.iterrows():
        for _,c in waitlist.iterrows():
            score,reasons,band=score_match(s,c)
            if score <= 0: continue
            rows.append({
                "slot_id":s.slot_id,"candidate_id":c.candidate_id,"service_line":s.service_line,
                "slot_date":s.slot_date,"slot_start":s.slot_start,"slot_urgency":s.urgency_tier,
                "candidate_urgency":c.urgency_tier,"travel_minutes":c.travel_minutes,"readiness_score":c.readiness_score,
                "verified":c.verified,"available_today":c.available_today,"score":score,"classification":band,
                "reasons":"; ".join(reasons)
            })
    out=pd.DataFrame(rows)
    if out.empty: return out
    return out.sort_values(["slot_id","score"], ascending=[True,False]).reset_index(drop=True)

css()

st.markdown("""
<div class='topbar'>
  <div><div class='brand'>🧭 QueueMatch Local</div><div class='sub'>Emergency waitlist matching intelligence</div></div>
  <div class='ready'><span class='dot'></span> LOCAL · READY</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Data workspace")
    slot_file=st.file_uploader("Upload cancelled-appointment CSV", type=["csv"], help="Authorized, minimum-necessary operational data only.")
    wait_file=st.file_uploader("Upload verified-waitlist CSV", type=["csv"])
    st.caption("200MB per file • CSV")
    st.divider()
    st.markdown("### Matching controls")
    min_score=st.slider("Minimum score",0,100,50,5)
    same_day_only=st.checkbox("Same-day availability only", value=False)
    verified_only=st.checkbox("Verified candidates only", value=True)
    st.divider()
    st.markdown("### Local-only")
    st.caption("No external APIs • transparent rules • local CSV processing")

try:
    slots = load_csv(slot_file) if slot_file is not None else load_csv(DATA_DIR/"sample_cancelled_appointments.csv")
    waitlist = load_csv(wait_file) if wait_file is not None else load_csv(DATA_DIR/"sample_verified_waitlist.csv")
except ValueError as exc:
    st.error(f"Input data error: {exc}")
    st.stop()

required_slots={"slot_id","service_line","urgency_tier","slot_date","slot_start","max_travel_minutes","readiness_required","verification_required"}
required_wait={"candidate_id","service_line","urgency_tier","travel_minutes","readiness_score","verified","available_today","earliest_date","contactable","prior_declines","last_updated"}
missing_slots=required_slots-set(slots.columns)
missing_wait=required_wait-set(waitlist.columns)
if missing_slots or missing_wait:
    st.error(f"Missing columns — slots: {sorted(missing_slots)}; waitlist: {sorted(missing_wait)}")
    st.stop()

# Normalize numeric and boolean fields defensively so CSV values like Yes/No also work.
for col in ["max_travel_minutes", "readiness_required"]:
    slots[col] = pd.to_numeric(slots[col], errors="coerce")
for col in ["verification_required"]:
    slots[col] = slots[col].map(parse_binary)
for col in ["travel_minutes", "readiness_score", "prior_declines"]:
    waitlist[col] = pd.to_numeric(waitlist[col], errors="coerce")
for col in ["verified", "available_today", "contactable"]:
    waitlist[col] = waitlist[col].map(parse_binary)

for col in ["slot_date"]:
    slots[col] = slots[col].map(parse_date)
for col in ["earliest_date", "last_updated"]:
    waitlist[col] = waitlist[col].map(parse_date)

# Fill operational numeric defaults only after coercion.
slots["max_travel_minutes"] = slots["max_travel_minutes"].fillna(60)
slots["readiness_required"] = slots["readiness_required"].fillna(60)
waitlist["travel_minutes"] = waitlist["travel_minutes"].fillna(30)
waitlist["readiness_score"] = waitlist["readiness_score"].fillna(50)
waitlist["prior_declines"] = waitlist["prior_declines"].fillna(0)

if verified_only:
    waitlist=waitlist[waitlist.verified.eq(1)].copy()
if same_day_only:
    waitlist=waitlist[waitlist.available_today.eq(1)].copy()

matches=build_matches(slots,waitlist)

hero_left, hero_right = st.columns([1.7,0.9], gap="large", vertical_alignment="top")
with hero_left:
    st.markdown("""
    <div class='hero'>
      <div>
        <div class='eyebrow'>EMERGENCY SCHEDULING • VERIFIED QUEUE • HUMAN REVIEW</div>
        <h1>Cancelled slots, matched with care and clarity.</h1>
        <p>Screen operational candidates using transparent rules for urgency, service fit, travel feasibility, readiness, verification and availability—while keeping every record local.</p>
        <div class='pillrow'><span class='pill'>⚡ Urgency</span><span class='pill'>🗺 Travel</span><span class='pill'>✅ Readiness</span><span class='pill'>🔐 Verified</span><span class='pill'>🧩 Service fit</span><span class='pill'>📊 Explainable</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with hero_right:
    if ASSET.exists(): st.image(str(ASSET), use_container_width=True)
    else: st.info("QueueMatch Local")

st.markdown("<div style='height:14px'></div>",unsafe_allow_html=True)
st.markdown("<div class='notice'><strong>Operational-safety boundary:</strong> QueueMatch is a scheduling aid. It does not diagnose, rank clinical severity, determine clinical eligibility, or auto-book anyone. Authorized staff must review and confirm every proposed match.</div>",unsafe_allow_html=True)

m1,m2,m3,m4,m5=st.columns(5,gap="medium")
metrics=[("Cancelled slots",len(slots),"input queue"),("Verified candidates",len(waitlist),"after filters"),("Potential matches",len(matches),"scored pairs"),("Preferred matches",int((matches.classification=="Preferred").sum()) if not matches.empty else 0,"score ≥ 85"),("Coverage",round(len(matches.slot_id.unique())/max(len(slots),1)*100),"slots with ≥1 match")]
for c,(lab,val,note) in zip([m1,m2,m3,m4,m5],metrics):
    with c:
        st.markdown(f"<div class='metric'><div class='metric-label'>{lab}</div><div class='metric-value'>{val}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
tab1,tab2,tab3,tab4 = st.tabs(["Match Command Center","Queue Analytics","Candidate Review","Scenario Lab"])

with tab1:
    st.markdown("<div class='panel'><div class='panel-title'>Priority slot-to-candidate recommendations</div><div class='small'>Sorted by slot, then suitability score.</div></div>",unsafe_allow_html=True)
    if matches.empty:
        st.warning("No feasible matches under the current filters.")
    else:
        view=matches[matches.score>=min_score].copy()
        st.dataframe(view[["slot_id","candidate_id","service_line","slot_urgency","candidate_urgency","travel_minutes","readiness_score","score","classification","reasons"]],use_container_width=True,hide_index=True)
        csv=view.to_csv(index=False).encode()
        st.download_button("⬇ Download scored matches",csv,"queued_match_results.csv","text/csv")

with tab2:
    if matches.empty:
        st.info("No scored matches yet.")
    else:
        c1,c2=st.columns(2)
        with c1:
            dist=matches.classification.value_counts().reset_index(); dist.columns=["classification","count"]
            fig=px.bar(dist,x="classification",y="count",text="count",title="Match classification mix")
            fig.update_layout(margin=dict(l=10,r=10,t=50,b=10),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            fig2=px.scatter(matches,x="travel_minutes",y="readiness_score",size="score",color="classification",hover_data=["slot_id","candidate_id"],title="Travel × readiness landscape")
            fig2.update_layout(margin=dict(l=10,r=10,t=50,b=10),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2,use_container_width=True)
        by_service=matches.groupby("service_line",as_index=False).agg(matches=("candidate_id","count"),avg_score=("score","mean"))
        fig3=px.bar(by_service,x="service_line",y="avg_score",color="avg_score",title="Average suitability by service line")
        fig3.update_layout(margin=dict(l=10,r=10,t=50,b=10),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3,use_container_width=True)

with tab3:
    if matches.empty:
        st.info("No candidate review data.")
    else:
        cand=st.selectbox("Select candidate",sorted(matches.candidate_id.unique()))
        detail=matches[matches.candidate_id.eq(cand)].sort_values("score",ascending=False)
        st.dataframe(detail[["slot_id","service_line","slot_urgency","candidate_urgency","travel_minutes","readiness_score","score","classification","reasons"]],use_container_width=True,hide_index=True)
        top=detail.iloc[0]
        st.markdown(f"<div class='panel'><div class='panel-title'>Top operational fit for {cand}</div><p class='small'>{top['slot_id']} • {top['service_line']} • score {top['score']}</p><p>{top['reasons']}</p></div>",unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='panel'><div class='panel-title'>Scenario Lab</div><div class='small'>Adjust operational thresholds and recompute the queue. This is not a clinical prioritization tool.</div></div>",unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a: travel_factor=st.slider("Travel ceiling multiplier",0.6,1.4,1.0,0.05)
    with b: readiness_floor=st.slider("Readiness floor",0,100,60,5)
    with c: require_verified=st.checkbox("Require verification",True)
    scen=waitlist.copy()
    if require_verified: scen=scen[scen.verified.eq(1)]
    scen=scen[scen.readiness_score>=readiness_floor]
    scen_slots=slots.copy(); scen_slots["max_travel_minutes"]=(scen_slots["max_travel_minutes"]*travel_factor).round(0)
    scen_matches=build_matches(scen_slots,scen)
    st.metric("Scenario feasible matches",len(scen_matches))
    if not scen_matches.empty:
        st.dataframe(scen_matches[["slot_id","candidate_id","service_line","score","classification","travel_minutes","readiness_score"]].head(40),use_container_width=True,hide_index=True)
        st.download_button("⬇ Export scenario matches",scen_matches.to_csv(index=False).encode(),"scenario_matches.csv","text/csv")

st.markdown("<div class='footer'>QueueMatch Local • local-first operational coordination • human-in-the-loop review</div>",unsafe_allow_html=True)
