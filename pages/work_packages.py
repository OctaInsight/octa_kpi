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

# Which sub-section to highlight based on sidebar click
wp_sub_tab = st.session_state.pop("wp_sub_tab", None)

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
                tid   = t["task_id"]
                tnum  = t.get("task_number","")
                ttitle= t.get("task_title","")
                with st.expander(
                    f"⚙️ {tnum}: {ttitle}  ·  M{t.get('start_month','?')}–M{t.get('end_month','?')}",
                    expanded=False
                ):
                    with st.form(f"edit_task_{tid}"):
                        et1, et2 = st.columns([1, 4])
                        with et1:
                            e_tnum = st.text_input("Task #", value=tnum)
                        with et2:
                            e_ttitle = st.text_input("Title", value=ttitle)
                        e_tdesc = st.text_area("Description",
                            value=t.get("task_description",""), height=60)
                        etm1, etm2 = st.columns(2)
                        with etm1:
                            e_tsm = st.number_input("Start Month", min_value=1,
                                max_value=120, value=int(t.get("start_month",1) or 1))
                        with etm2:
                            e_tem = st.number_input("End Month", min_value=1,
                                max_value=120, value=int(t.get("end_month",12) or 12))
                        # Lead partner
                        lead_list_e = ["— None —"] + list(partner_opts.keys())
                        cur_tlead   = t.get("task_lead_partner_id")
                        tlead_def   = next((l for l,v in partner_opts.items() if v==cur_tlead), "— None —")
                        tlead_idx   = lead_list_e.index(tlead_def) if tlead_def in lead_list_e else 0
                        e_tlead_sel = st.selectbox("Lead Partner", lead_list_e,
                            index=tlead_idx, key=f"etlead_{tid}")
                        e_tlead_id  = partner_opts.get(e_tlead_sel)
                        # Involved partners
                        cur_tp      = get_task_partners(tid)
                        cur_tp_ids  = [r.get("partner_id") for r in cur_tp if r.get("role") != "lead"]
                        e_tinv      = st.multiselect("Involved Partners",
                            list(partner_opts.keys()),
                            default=[l for l,v in partner_opts.items() if v in cur_tp_ids],
                            key=f"etinv_{tid}")
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.form_submit_button("💾 Save", type="primary",
                                                      use_container_width=True):
                                ok2, _ = upsert_task({
                                    "task_id": tid, "proposal_id": proposal_id,
                                    "wp_id": wp_id,
                                    "task_number":      e_tnum.strip(),
                                    "task_title":       e_ttitle.strip(),
                                    "task_description": e_tdesc.strip(),
                                    "start_month": e_tsm, "end_month": e_tem,
                                    "task_lead_partner_id": e_tlead_id,
                                })
                                if ok2:
                                    tp_save = []
                                    if e_tlead_id:
                                        tp_save.append({"partner_id": e_tlead_id, "role": "lead"})
                                    for lbl in e_tinv:
                                        p_id = partner_opts.get(lbl)
                                        if p_id and p_id != e_tlead_id:
                                            tp_save.append({"partner_id": p_id, "role": "contributor"})
                                    set_task_partners(tid, tp_save)
                                    st.success("✅ Task saved!"); st.rerun()
                                else:
                                    st.error("Save failed.")
                        with sc2:
                            if st.form_submit_button("🗑 Delete",
                                                      use_container_width=True):
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
                dnum  = d.get("deliverable_number","")
                with st.expander(
                    f"◆ {dnum}: {d.get('deliverable_title','')}  ·  Month {d.get('delivery_month','?')}",
                    expanded=False
                ):
                    with st.form(f"edit_del_{did}"):
                        ed1, ed2 = st.columns([1, 4])
                        with ed1:
                            e_dnum   = st.text_input("Del. #", value=dnum)
                        with ed2:
                            e_dtitle = st.text_input("Title", value=d.get("deliverable_title",""))
                        e_ddesc = st.text_area("Description",
                            value=d.get("deliverable_description",""), height=60)
                        edd1, edd2, edd3 = st.columns(3)
                        with edd1:
                            cur_dt  = d.get("deliverable_type","report")
                            e_dtype = st.selectbox("Type", DELIVERABLE_TYPES,
                                index=DELIVERABLE_TYPES.index(cur_dt)
                                      if cur_dt in DELIVERABLE_TYPES else 0)
                        with edd2:
                            cur_diss  = d.get("dissemination_level","public")
                            e_ddiss   = st.selectbox("Dissemination", DISSEMINATION_LEVELS,
                                index=DISSEMINATION_LEVELS.index(cur_diss)
                                      if cur_diss in DISSEMINATION_LEVELS else 0)
                        with edd3:
                            e_dmonth = st.number_input("Month", min_value=1, max_value=120,
                                value=int(d.get("delivery_month",12) or 12))
                        # Link to task
                        task_opts_e = {"— No task link —": None}
                        task_opts_e |= {f"{t['task_number']}: {t.get('task_title','')[:30]}": t["task_id"]
                                        for t in wp_tasks}
                        cur_dtask   = d.get("task_id")
                        cur_dtsel   = next((l for l,v in task_opts_e.items() if v == cur_dtask),
                                          "— No task link —")
                        e_dtask_sel = st.selectbox("Linked Task", list(task_opts_e.keys()),
                            index=list(task_opts_e.keys()).index(cur_dtsel),
                            key=f"edt_{did}")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.form_submit_button("💾 Save", type="primary",
                                                      use_container_width=True):
                                ok3, _ = upsert_deliverable({
                                    "deliverable_id":    did,
                                    "proposal_id":       proposal_id,
                                    "wp_id":             wp_id,
                                    "task_id":           task_opts_e[e_dtask_sel],
                                    "deliverable_number":  e_dnum.strip(),
                                    "deliverable_title":   e_dtitle.strip(),
                                    "deliverable_description": e_ddesc.strip(),
                                    "deliverable_type":    e_dtype,
                                    "dissemination_level": e_ddiss,
                                    "delivery_month":      e_dmonth,
                                })
                                if ok3:
                                    st.success("✅ Deliverable saved!"); st.rerun()
                                else:
                                    st.error("Save failed.")
                        with dc2:
                            if st.form_submit_button("🗑 Delete",
                                                      use_container_width=True):
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
                mnum = m.get("milestone_number","")
                with st.expander(
                    f"★ {mnum}: {m.get('milestone_title','')}  ·  Month {m.get('due_month','?')}",
                    expanded=False
                ):
                    with st.form(f"edit_ms_{mid}"):
                        em1, em2 = st.columns([1, 4])
                        with em1:
                            e_mnum   = st.text_input("MS #", value=mnum)
                        with em2:
                            e_mtitle = st.text_input("Title", value=m.get("milestone_title",""))
                        e_mdesc = st.text_area("Description",
                            value=m.get("milestone_description",""), height=60)
                        emm1, emm2 = st.columns(2)
                        with emm1:
                            e_mmonth = st.number_input("Due Month", min_value=1, max_value=120,
                                value=int(m.get("due_month",12) or 12))
                        with emm2:
                            e_mmov   = st.text_input("Means of Verification",
                                value=m.get("means_of_verification",""))
                        # Link to task
                        task_opts_m = {"— WP level —": None}
                        task_opts_m |= {f"{t['task_number']}: {t.get('task_title','')[:30]}": t["task_id"]
                                        for t in wp_tasks}
                        cur_mtask   = m.get("task_id")
                        cur_mtsel   = next((l for l,v in task_opts_m.items() if v == cur_mtask),
                                          "— WP level —")
                        e_mtask_sel = st.selectbox("Linked Task", list(task_opts_m.keys()),
                            index=list(task_opts_m.keys()).index(cur_mtsel),
                            key=f"emt_{mid}")
                        mc1, mc2 = st.columns(2)
                        with mc1:
                            if st.form_submit_button("💾 Save", type="primary",
                                                      use_container_width=True):
                                ok4, _ = upsert_milestone({
                                    "milestone_id":      mid,
                                    "proposal_id":       proposal_id,
                                    "wp_id":             wp_id,
                                    "task_id":           task_opts_m[e_mtask_sel],
                                    "milestone_number":  e_mnum.strip(),
                                    "milestone_title":   e_mtitle.strip(),
                                    "milestone_description": e_mdesc.strip(),
                                    "due_month":         e_mmonth,
                                    "means_of_verification": e_mmov.strip(),
                                })
                                if ok4:
                                    st.success("✅ Milestone saved!"); st.rerun()
                                else:
                                    st.error("Save failed.")
                        with mc2:
                            if st.form_submit_button("🗑 Delete",
                                                      use_container_width=True):
                                delete_milestone(mid); st.rerun()

# ── Persistent Gantt ──────────────────────────────────────────────────────────
tasks_all = get_tasks(proposal_id)
dels_all  = get_deliverables(proposal_id)
mss_all   = get_milestones(proposal_id)
render_gantt({"work_packages": wps, "tasks": tasks_all,
              "deliverables": dels_all, "milestones": mss_all},
             proposal_id, expanded=True)
