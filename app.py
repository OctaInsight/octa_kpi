"""
Octa KPI & Work Plan Designer — Landing Page
Select a proposal, then design its work plan structure.
"""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url, set_token_in_url, get_token_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import get_all_proposals, get_gantt_data, get_objectives, get_kpis
from modules.gantt import render_gantt

st.set_page_config(page_title=f"Octa Work Plan Designer",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
auto_login_from_url()
require_auth()

token = st.session_state.get("sso_token","") or get_token_from_url()
if token: set_token_in_url(token)

sidebar_nav()

page_header("Objectives & Work Plan Designer",
            "Select a proposal to design its work plan structure, KPIs and budget",
            "📊")

proposals = get_all_proposals()
if not proposals:
    st.warning("No proposals found. Create proposals in the Proposal Tracking app first.")
    st.stop()

# ── Proposal selector ─────────────────────────────────────────────────────────
D = DARK
muted = D["muted"]; acc = D["accent"]

current_pid = st.session_state.get("selected_proposal_id","")

prop_opts = {}
for p in proposals:
    acr   = p.get("acronym","").strip() or p["proposal_id"]
    title = str(p.get("proposal_title",""))[:50]
    lc    = p.get("lifecycle_status","") or p.get("status","")
    prop_opts[f"{acr} — {title} [{lc}]"] = p["proposal_id"]

current_label = next((l for l,v in prop_opts.items() if v == current_pid), None)
default_idx   = list(prop_opts.keys()).index(current_label) if current_label else 0

sel_label = st.selectbox(
    "Select Proposal to Design",
    list(prop_opts.keys()),
    index=default_idx,
    key="prop_selector"
)
sel_pid = prop_opts[sel_label]

if sel_pid != current_pid:
    st.session_state["selected_proposal_id"] = sel_pid
    st.rerun()

if not sel_pid:
    st.stop()

# ── Proposal summary ──────────────────────────────────────────────────────────
prop = next((p for p in proposals if p["proposal_id"] == sel_pid), {})
dur  = int(prop.get("project_duration_months") or 36)

c1,c2,c3,c4 = st.columns(4)
for col, label, val, color in [
    (c1, "Status",    (prop.get("lifecycle_status") or prop.get("status","")).replace("_"," ").title(), D["accent"]),
    (c2, "Duration",  f"{dur} months",  D["accent2"]),
    (c3, "Deadline",  str(prop.get("deadline","—"))[:10], D["warning"]),
    (c4, "Coordinator", str(prop.get("coordinator","—"))[:20], D["muted"]),
]:
    bg2 = D["bg2"]
    col.markdown(
        f"<div style='background:{bg2};border-top:3px solid {color};"
        f"border:1px solid {color}44;border-radius:10px;"
        f"padding:0.7rem 0.9rem;text-align:center'>"
        f"<div style='font-size:1rem;font-weight:700;color:{color}'>{val}</div>"
        f"<div style='font-size:0.72rem;color:{D["muted"]}'>{label}</div></div>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Summary counts ────────────────────────────────────────────────────────────
from modules.database import get_work_packages, get_tasks, get_deliverables, get_milestones
wps   = get_work_packages(sel_pid)
tasks = get_tasks(sel_pid)
dels  = get_deliverables(sel_pid)
mss   = get_milestones(sel_pid)
objs  = get_objectives(sel_pid)
kpis  = get_kpis(sel_pid)

section_label("📐 Work Plan Summary")
sk1,sk2,sk3,sk4,sk5,sk6 = st.columns(6)
for col, label, val in [
    (sk1,"Objectives",   len(objs)),
    (sk2,"Work Packages",len(wps)),
    (sk3,"Tasks",        len(tasks)),
    (sk4,"Deliverables", len(dels)),
    (sk5,"Milestones",   len(mss)),
    (sk6,"KPIs",         len(kpis)),
]:
    bg2 = D["bg2"]; acc = D["accent"]
    col.markdown(
        f"<div style='background:{bg2};border:1px solid {D["border"]};"
        f"border-radius:10px;padding:0.7rem;text-align:center'>"
        f"<div style='font-size:1.6rem;font-weight:700;color:{acc}'>{val}</div>"
        f"<div style='font-size:0.75rem;color:{D["muted"]}'>{label}</div></div>",
        unsafe_allow_html=True
    )

# ── Quick access buttons ──────────────────────────────────────────────────────
section_label("Quick Access")
qa1,qa2,qa3,qa4,qa5 = st.columns(5)
with qa1:
    if st.button("🎯 Design Objectives",    type="primary",  use_container_width=True):
        st.switch_page("pages/objectives.py")
with qa2:
    if st.button("📦 Work Packages",        use_container_width=True):
        st.switch_page("pages/work_packages.py")
with qa3:
    if st.button("📊 KPIs",                 use_container_width=True):
        st.switch_page("pages/kpis.py")
with qa4:
    if st.button("💶 Budget",               use_container_width=True):
        st.switch_page("pages/budget.py")
with qa5:
    if st.button("📥 Export",               use_container_width=True):
        st.switch_page("pages/export_page.py")

# ── Gantt chart ───────────────────────────────────────────────────────────────
gantt_data = {"work_packages": wps, "tasks": tasks,
              "deliverables": dels, "milestones": mss}
render_gantt(gantt_data, sel_pid, duration=dur, expanded=True)
