"""Octa KPI — Work Packages Page (Tasks, Deliverables, Milestones)."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import (
    get_work_packages, upsert_work_package, delete_work_package,
    get_wp_objectives, set_wp_objectives, get_objectives,
    get_wp_partners, set_wp_partners,
    get_tasks, upsert_task, delete_task,
    get_task_partners, set_task_partners,
    get_deliverables, upsert_deliverable, delete_deliverable,
    get_milestones, upsert_milestone, delete_milestone,
    get_all_partners, get_proposal_partners,
)
from modules.gantt import render_gantt
from config import (DELIVERABLE_TYPES, DISSEMINATION_LEVELS,
                    TASK_STATUSES, DELIVERABLE_STATUSES, MILESTONE_STATUSES, DARK as D)

st.set_page_config(page_title="Work Packages — Octa", page_icon="📦",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id","")
if not proposal_id:
    st.warning("No proposal selected.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("Work Packages", f"Proposal: {proposal_id}", "📦")
if st.button("← Home"): st.switch_page("app.py")

user_id = st.session_state.get("user_id")
# Load partners from the proposal (coordinator + partners_list)
prop_partners = get_proposal_partners(proposal_id)
all_partners  = prop_partners if prop_partners else get_all_partners()
objectives    = get_objectives(proposal_id)
wps           = get_work_packages(proposal_id)

partner_opts = {
    f"{p.get('short_name','') or p.get('full_name','')[:20]} — {p.get('full_name','')[:35]}": p["id"]
    for p in all_partners
}
obj_opts     = {f"{o['objective_number']}: {o['objective_title'][:40]}": o["objective_id"]
                for o in objectives}

# ═════════════════════════════════════════════════════════════════════════════
# ADD / EDIT WORK PACKAGE
# ═════════════════════════════════════════════════════════════════════════════
section_label("➕ Add / Edit Work Package")

edit_wid = st.session_state.get("edit_wp_id")
edit_wp  = next((w for w in wps if w["wp_id"]==edit_wid), {}) if edit_wid else {}
def _w(f,d=""): return edit_wp.get(f,d) if edit_wp else d

with st.expander("Work Package Form", expanded=not wps or bool(edit_wid)):
    fc1,fc2 = st.columns([1,4])
    with fc1:
        wp_num   = st.text_input("WP Number *", value=_w("wp_number"), placeholder="WP1")
    with fc2:
        wp_title = st.text_input("Title *",     value=_w("wp_title"), placeholder="e.g. Management")

    wp_desc = st.text_area("Description", value=_w("wp_description"), height=80)

    mc1,mc2 = st.columns(2)
    with mc1: sm = st.number_input("Start Month *", min_value=1, max_value=120, value=int(_w("start_month",1) or 1))
    with mc2: em = st.number_input("End Month *",   min_value=1, max_value=120, value=int(_w("end_month",12) or 12))

    fc3,fc4,fc5 = st.columns(3)
    with fc3: is_mgmt  = st.checkbox("Management WP",     value=bool(_w("is_management_wp")))
    with fc4: is_comm  = st.checkbox("Communication WP",  value=bool(_w("is_communication_wp")))
    with fc5: is_diss  = st.checkbox("Dissemination WP",  value=bool(_w("is_dissemination_wp")))

    # Lead partner
    lead_opts = {"— None —": None} | partner_opts
    cur_lead  = _w("wp_lead_partner_id")
    lead_def  = next((l for l,v in lead_opts.items() if v==cur_lead), "— None —")
    sel_lead  = st.selectbox("Lead Partner", list(lead_opts.keys()),
                              index=list(lead_opts.keys()).index(lead_def),
                              key="wp_lead")
    lead_id   = lead_opts[sel_lead]

    # Involved partners (multiselect)
    cur_wp_partners = get_wp_partners(edit_wid) if edit_wid else []
    cur_involved_ids= [r.get("partner_id") for r in cur_wp_partners
                       if r.get("role") != "lead"]
    sel_involved = st.multiselect(
        "Involved Partners (contributors)",
        options=list(partner_opts.keys()),
        default=[l for l,v in partner_opts.items() if v in cur_involved_ids],
        key="wp_involved",
        help="Select all partners contributing to this WP"
    )

    # Link to objectives
    cur_obj_ids = get_wp_objectives(edit_wid) if edit_wid else []
    cur_obj_sel = [l for l,oid in obj_opts.items() if oid in cur_obj_ids]
    sel_objs    = st.multiselect("Linked Objectives", list(obj_opts.keys()),
                                  default=cur_obj_sel, key="wp_objs")

    if st.button("💾 Save Work Package", type="primary", key="save_wp"):
        if not wp_num.strip() or not wp_title.strip():
            st.error("❌ Number and Title required.")
        else:
            data = {
                "proposal_id":          proposal_id,
                "wp_number":            wp_num.strip().upper(),
                "wp_title":             wp_title.strip(),
                "wp_description":       wp_desc.strip(),
                "wp_lead_partner_id":   lead_id,
                "start_month":          sm,
                "end_month":            em,
                "is_management_wp":     is_mgmt,
                "is_communication_wp":  is_comm,
                "is_dissemination_wp":  is_diss,
            }
            if edit_wid: data["wp_id"] = edit_wid
            ok, wid = upsert_work_package(data)
            if ok:
                set_wp_objectives(wid, [obj_opts[l] for l in sel_objs])
                # Save partners: lead + involved
                partners_to_save = []
                if lead_id:
                    partners_to_save.append({"partner_id": lead_id, "role": "lead"})
                for lbl in sel_involved:
                    pid = partner_opts.get(lbl)
                    if pid and pid != lead_id:
                        partners_to_save.append({"partner_id": pid, "role": "contributor"})
                set_wp_partners(wid, partners_to_save)
                st.success("✅ WP saved!")
                st.session_state.pop("edit_wp_id", None)
                st.rerun()
            else:
                st.error(f"❌ {wid}")

    if edit_wid and st.button("✖ Cancel"):
        st.session_state.pop("edit_wp_id", None)
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# WORK PACKAGES — expandable with Tasks / Deliverables / Milestones
# ═════════════════════════════════════════════════════════════════════════════
section_label(f"All Work Packages ({len(wps)})")

for wp in sorted(wps, key=lambda x: x.get("wp_number","")):
    wp_id = wp["wp_id"]
    color = D["accent"]
    bg2   = D["bg2"]

    with st.expander(
        f"📦 {wp['wp_number']}: {wp.get('wp_title','')}  "
        f"(M{wp.get('start_month','?')}–M{wp.get('end_month','?')})",
        expanded=False
    ):
        wc1,wc2,_ = st.columns([1,1,5])
        with wc1:
            if st.button("✏️ Edit WP", key=f"ewp_{wp_id}", use_container_width=True):
                st.session_state["edit_wp_id"] = wp_id
                st.rerun()
        with wc2:
            if st.button("🗑 Delete WP", key=f"dwp_{wp_id}", use_container_width=True):
                if delete_work_package(wp_id):
                    st.success("Deleted."); st.rerun()

        wp_tasks = get_tasks(proposal_id, wp_id)
        wp_dels  = get_deliverables(proposal_id, wp_id)
        wp_mss   = get_milestones(proposal_id, wp_id)

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(
            [f"⚙️ Tasks ({len(wp_tasks)})",
             f"📄 Deliverables ({len(wp_dels)})",
             f"🏁 Milestones ({len(wp_mss)})"]
        )

        # ── TASKS ─────────────────────────────────────────────────────────────
        with sub_tab1:
            with st.form(f"task_form_{wp_id}", clear_on_submit=True):
                tc1,tc2 = st.columns([1,4])
                with tc1: t_num   = st.text_input("Task #", placeholder=f"T{wp['wp_number'][2:]}.1")
                with tc2: t_title = st.text_input("Title *", placeholder="Task title")
                t_desc = st.text_area("Description", height=60)
                tm1,tm2 = st.columns(2)
                with tm1: t_sm = st.number_input("Start Month", min_value=1, max_value=120,
                                                  value=int(wp.get("start_month",1)))
                with tm2: t_em = st.number_input("End Month",   min_value=1, max_value=120,
                                                  value=int(wp.get("end_month",12)))
                t_lead_sel = st.selectbox("Lead Partner", ["— None —"]+list(partner_opts.keys()),
                                           key=f"t_lead_{wp_id}")
                t_lead_id  = partner_opts.get(t_lead_sel)
                t_involved = st.multiselect(
                    "Involved Partners",
                    options=list(partner_opts.keys()),
                    key=f"t_involved_{wp_id}",
                    help="Partners contributing to this task"
                )

                if st.form_submit_button("➕ Add Task", type="primary"):
                    if not t_title.strip():
                        st.error("Title required.")
                    else:
                        ok, tid = upsert_task({
                            "proposal_id": proposal_id, "wp_id": wp_id,
                            "task_number": t_num.strip() or f"T-{wp['wp_number']}.x",
                            "task_title":  t_title.strip(),
                            "task_description": t_desc.strip(),
                            "start_month": t_sm, "end_month": t_em,
                            "task_lead_partner_id": t_lead_id,
                        })
                        if ok and tid:
                            task_partners_to_save = []
                            if t_lead_id:
                                task_partners_to_save.append({"partner_id": t_lead_id, "role": "lead"})
                            for lbl in t_involved:
                                pid2 = partner_opts.get(lbl)
                                if pid2 and pid2 != t_lead_id:
                                    task_partners_to_save.append({"partner_id": pid2, "role": "contributor"})
                            if task_partners_to_save:
                                set_task_partners(tid, task_partners_to_save)
                            st.success("Task added!"); st.rerun()

            for t in wp_tasks:
                tid = t["task_id"]
                muted = D["muted"]; txt = D["text"]
                st.markdown(
                    f"<div style='background:{D["bg3"]};border-radius:8px;"
                    f"padding:0.5rem 0.8rem;margin-bottom:0.3rem'>"
                    f"<strong style='color:{D["accent"]}'>{t['task_number']}</strong> "
                    f"<span style='color:{txt}'>{t.get('task_title','')}</span> "
                    f"<span style='color:{muted};font-size:0.78rem'>"
                    f"M{t.get('start_month','?')}–M{t.get('end_month','?')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"🗑 Delete {t['task_number']}", key=f"dt_{tid}"):
                    delete_task(tid); st.rerun()

        # ── DELIVERABLES ──────────────────────────────────────────────────────
        with sub_tab2:
            with st.form(f"del_form_{wp_id}", clear_on_submit=True):
                dc1,dc2 = st.columns([1,4])
                with dc1: d_num   = st.text_input("Del. #", placeholder="D1.1")
                with dc2: d_title = st.text_input("Title *")
                d_desc = st.text_area("Description", height=60)
                dd1,dd2,dd3 = st.columns(3)
                with dd1:
                    d_type = st.selectbox("Type", DELIVERABLE_TYPES)
                with dd2:
                    d_diss = st.selectbox("Dissemination", DISSEMINATION_LEVELS)
                with dd3:
                    d_month= st.number_input("Delivery Month", min_value=1, max_value=120, value=int(wp.get("end_month",12)))
                d_lead_sel = st.selectbox("Lead Partner", ["— None —"]+list(partner_opts.keys()),
                                           key=f"d_lead_{wp_id}")
                d_lead_id  = partner_opts.get(d_lead_sel)

                # Link to task
                task_opts = {"— No task link —": None}
                task_opts |= {f"{t['task_number']}: {t.get('task_title','')[:30]}": t["task_id"]
                              for t in wp_tasks}
                d_task_sel = st.selectbox("Linked Task", list(task_opts.keys()),
                                           key=f"d_task_{wp_id}")
                d_task_id  = task_opts[d_task_sel]

                if st.form_submit_button("➕ Add Deliverable", type="primary"):
                    if not d_title.strip():
                        st.error("Title required.")
                    else:
                        ok, _ = upsert_deliverable({
                            "proposal_id": proposal_id, "wp_id": wp_id,
                            "task_id": d_task_id,
                            "deliverable_number": d_num.strip() or "D-?",
                            "deliverable_title":  d_title.strip(),
                            "deliverable_description": d_desc.strip(),
                            "deliverable_type":   d_type,
                            "dissemination_level": d_diss,
                            "delivery_month":      d_month,
                            "lead_partner_id":     d_lead_id,
                        })
                        if ok: st.success("Deliverable added!"); st.rerun()

            for d in wp_dels:
                did   = d["deliverable_id"]
                muted = D["muted"]; acc = D["accent"]; suc = D["success"]
                st.markdown(
                    f"<div style='background:{D["bg3"]};border-radius:8px;"
                    f"padding:0.5rem 0.8rem;margin-bottom:0.3rem'>"
                    f"<span style='color:{suc}'>◆</span> "
                    f"<strong style='color:{acc}'>{d['deliverable_number']}</strong> "
                    f"<span style='color:{D["text"]}'>{d.get('deliverable_title','')}</span> "
                    f"<span style='color:{muted};font-size:0.78rem'>"
                    f"Month {d.get('delivery_month','?')} · {d.get('deliverable_type','')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"🗑 Delete {d['deliverable_number']}", key=f"dd_{did}"):
                    delete_deliverable(did); st.rerun()

        # ── MILESTONES ────────────────────────────────────────────────────────
        with sub_tab3:
            with st.form(f"ms_form_{wp_id}", clear_on_submit=True):
                mc1,mc2 = st.columns([1,4])
                with mc1: m_num   = st.text_input("MS #", placeholder="MS1")
                with mc2: m_title = st.text_input("Title *")
                m_desc = st.text_area("Description", height=60)
                mm1,mm2 = st.columns(2)
                with mm1: m_month = st.number_input("Due Month", min_value=1,
                                                     max_value=120,
                                                     value=int(wp.get("end_month",12)))
                with mm2: m_mov   = st.text_input("Means of Verification",
                                                   placeholder="e.g. Published report")
                m_lead_sel = st.selectbox("Responsible Partner",
                                           ["— None —"]+list(partner_opts.keys()),
                                           key=f"m_lead_{wp_id}")
                m_lead_id  = partner_opts.get(m_lead_sel)
                # Link to task
                task_opts2 = {"— WP level —": None}
                task_opts2 |= {f"{t['task_number']}: {t.get('task_title','')[:30]}": t["task_id"]
                               for t in wp_tasks}
                m_task_sel = st.selectbox("Linked Task (optional)",
                                          list(task_opts2.keys()),
                                          key=f"m_task_{wp_id}")
                m_task_id  = task_opts2[m_task_sel]

                if st.form_submit_button("➕ Add Milestone", type="primary"):
                    if not m_title.strip():
                        st.error("Title required.")
                    else:
                        ok, _ = upsert_milestone({
                            "proposal_id": proposal_id, "wp_id": wp_id,
                            "task_id": m_task_id,
                            "milestone_number": m_num.strip() or "MS-?",
                            "milestone_title":  m_title.strip(),
                            "milestone_description": m_desc.strip(),
                            "due_month": m_month,
                            "means_of_verification": m_mov.strip(),
                            "responsible_partner_id": m_lead_id,
                        })
                        if ok: st.success("Milestone added!"); st.rerun()

            for m in wp_mss:
                mid  = m["milestone_id"]
                warn = D["warning"]
                st.markdown(
                    f"<div style='background:{D["bg3"]};border-radius:8px;"
                    f"padding:0.5rem 0.8rem;margin-bottom:0.3rem'>"
                    f"<span style='color:{warn}'>★</span> "
                    f"<strong style='color:{warn}'>{m['milestone_number']}</strong> "
                    f"<span style='color:{D["text"]}'>{m.get('milestone_title','')}</span> "
                    f"<span style='color:{D["muted"]};font-size:0.78rem'>"
                    f"Month {m.get('due_month','?')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"🗑 Delete {m['milestone_number']}", key=f"dm_{mid}"):
                    delete_milestone(mid); st.rerun()

# ── Persistent Gantt ──────────────────────────────────────────────────────────
tasks_all = get_tasks(proposal_id)
dels_all  = get_deliverables(proposal_id)
mss_all   = get_milestones(proposal_id)
render_gantt({"work_packages": wps, "tasks": tasks_all,
              "deliverables": dels_all, "milestones": mss_all},
             proposal_id, expanded=True)
