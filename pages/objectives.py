"""Octa KPI — Objectives Page."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import (get_objectives, upsert_objective, delete_objective,
                               get_work_packages, get_wp_objectives, set_wp_objectives,
                               get_gantt_data)
from modules.gantt import render_gantt

st.set_page_config(page_title="Objectives — Octa", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id","")
if not proposal_id:
    st.warning("No proposal selected. Go to Home and select a proposal.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("Objectives", f"Proposal: {proposal_id}", "🎯")
if st.button("← Home"): st.switch_page("app.py")

D       = DARK
muted_c = D["muted"]
acc_c   = D["accent"]
user_id = st.session_state.get("user_id")

objectives = get_objectives(proposal_id)
wps        = get_work_packages(proposal_id)

# ── Form: Add / Edit Objective ────────────────────────────────────────────────
section_label("➕ Add / Edit Objective")

edit_oid = st.session_state.get("edit_obj_id")
edit_obj = next((o for o in objectives if o["objective_id"]==edit_oid), {}) if edit_oid else {}

def _v(f, d=""): return edit_obj.get(f, d) if edit_obj else d

with st.form("obj_form", clear_on_submit=False):
    fc1,fc2 = st.columns([1,4])
    with fc1:
        obj_num = st.text_input("Number *", value=_v("objective_number"),
                                 placeholder="OBJ1")
    with fc2:
        obj_title = st.text_input("Title *", value=_v("objective_title"),
                                   placeholder="e.g. Improve digital literacy…")
    obj_desc = st.text_area("Description", value=_v("objective_description"),
                             height=100, placeholder="Full objective description…")

    # Sort order
    sort_order = st.number_input("Sort order", value=int(_v("sort_order", 0)),
                                  min_value=0, key="obj_sort")

    submitted = st.form_submit_button(
        "💾 Save Objective" if not edit_obj else "💾 Update Objective",
        type="primary", use_container_width=True
    )

if submitted:
    if not obj_num.strip() or not obj_title.strip():
        st.error("❌ Number and Title are required.")
    else:
        data = {
            "proposal_id":          proposal_id,
            "objective_number":     obj_num.strip().upper(),
            "objective_title":      obj_title.strip(),
            "objective_description":obj_desc.strip(),
            "sort_order":           sort_order,
            "created_by":           user_id,
        }
        if edit_obj:
            data["objective_id"] = edit_oid
        ok, result = upsert_objective(data)
        if ok:
            st.success("✅ Objective saved!")
            st.session_state.pop("edit_obj_id", None)
            st.rerun()
        else:
            st.error(f"❌ {result}")

if edit_obj and st.button("✖ Cancel Edit"):
    st.session_state.pop("edit_obj_id", None)
    st.rerun()

# ── Objectives list ───────────────────────────────────────────────────────────
section_label(f"All Objectives ({len(objectives)})")

if not objectives:
    st.info("No objectives yet. Add your first objective above.")
else:
    for obj in objectives:
        oid   = obj["objective_id"]
        num   = obj.get("objective_number","")
        title = obj.get("objective_title","")
        desc  = obj.get("objective_description","")

        # Which WPs link to this objective?
        linked_wps = [wp for wp in wps if oid in get_wp_objectives(wp["wp_id"])]
        wp_chips   = " ".join(
            f"<span style='background:{acc_c}22;color:{acc_c};"
            f"border:1px solid {acc_c}44;padding:1px 7px;"
            f"border-radius:8px;font-size:0.72rem'>{wp['wp_number']}</span>"
            for wp in linked_wps
        )

        bg2 = D["bg2"]; border = D["border"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {acc_c};border-radius:10px;"
            f"padding:0.8rem 1rem;margin-bottom:0.3rem'>"
            f"<strong style='color:{acc_c}'>{num}</strong> "
            f"<strong style='color:{D["text"]}'>{title}</strong>"
            + (f"<br><span style='color:{muted_c};font-size:0.82rem'>{desc[:120]}{'…' if len(desc)>120 else ''}</span>" if desc else "")
            + (f"<br><div style='margin-top:0.4rem'>Linked WPs: {wp_chips}</div>" if wp_chips else "")
            + "</div>",
            unsafe_allow_html=True
        )

        bc1,bc2,bc3,_ = st.columns([1,1,1,5])
        with bc1:
            if st.button("✏️ Edit", key=f"edit_obj_{oid}", use_container_width=True):
                st.session_state["edit_obj_id"] = oid
                st.rerun()
        with bc2:
            if wps:
                # Link to WPs
                pass  # handled below
        with bc3:
            if st.button("🗑 Delete", key=f"del_obj_{oid}", use_container_width=True):
                if delete_objective(oid):
                    st.success("Deleted.")
                    st.rerun()

# ── Link objectives to WPs ────────────────────────────────────────────────────
if objectives and wps:
    section_label("🔗 Link Objectives to Work Packages")
    st.caption("For each Work Package, select which objectives it contributes to.")
    for wp in wps:
        wp_id     = wp["wp_id"]
        current   = get_wp_objectives(wp_id)
        obj_opts  = {f"{o['objective_number']}: {o['objective_title'][:40]}": o["objective_id"]
                     for o in objectives}
        sel_labels= [l for l,oid in obj_opts.items() if oid in current]

        new_sel = st.multiselect(
            f"**{wp['wp_number']}** — {wp.get('wp_title','')[:50]}",
            options=list(obj_opts.keys()),
            default=sel_labels,
            key=f"wp_obj_link_{wp_id}"
        )
        new_ids = [obj_opts[l] for l in new_sel]
        if set(new_ids) != set(current):
            if st.button(f"Save links for {wp['wp_number']}",
                         key=f"save_link_{wp_id}"):
                set_wp_objectives(wp_id, new_ids)
                st.success("Links saved!")
                st.rerun()

# ── Gantt ─────────────────────────────────────────────────────────────────────
from modules.database import get_tasks, get_deliverables, get_milestones
gantt_data = {
    "work_packages": wps,
    "tasks":         get_tasks(proposal_id),
    "deliverables":  get_deliverables(proposal_id),
    "milestones":    get_milestones(proposal_id),
}
render_gantt(gantt_data, proposal_id, expanded=False)
