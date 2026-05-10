"""Octa KPI — KPIs Page (Short-term and Long-term)."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import (
    get_kpis, upsert_kpi, delete_kpi, set_kpi_links, get_kpi_links,
    get_objectives, get_work_packages, get_tasks, get_deliverables,
    get_milestones, get_all_partners, get_gantt_data,
)
from modules.gantt import render_gantt
from config import KPI_UNITS, KPI_STATUSES, DARK as D

st.set_page_config(page_title="KPIs — Octa", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id","")
if not proposal_id:
    st.warning("No proposal selected.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("KPIs", f"Proposal: {proposal_id}", "📊")
if st.button("← Home"): st.switch_page("app.py")

# Load reference data
objectives  = get_objectives(proposal_id)
wps         = get_work_packages(proposal_id)
tasks       = get_tasks(proposal_id)
deliverables= get_deliverables(proposal_id)
milestones  = get_milestones(proposal_id)
all_partners= get_all_partners()

obj_opts  = {f"{o['objective_number']}: {o['objective_title'][:35]}":  o["objective_id"]  for o in objectives}
wp_opts   = {f"{w['wp_number']}: {w.get('wp_title','')[:35]}":          w["wp_id"]         for w in wps}
task_opts = {f"{t['task_number']}: {t.get('task_title','')[:35]}":      t["task_id"]       for t in tasks}
del_opts  = {f"{d['deliverable_number']}: {d.get('deliverable_title','')[:30]}": d["deliverable_id"] for d in deliverables}
ms_opts   = {f"{m['milestone_number']}: {m.get('milestone_title','')[:35]}":     m["milestone_id"]  for m in milestones}
part_opts = {f"{p.get('short_name','')} — {p.get('full_name','')[:35]}": p["id"] for p in all_partners}

kpis_short = get_kpis(proposal_id, "short_term")
kpis_long  = get_kpis(proposal_id, "long_term")

tab_short, tab_long = st.tabs([
    f"⏱️ Short-Term KPIs ({len(kpis_short)})",
    f"🔭 Long-Term KPIs / Impact ({len(kpis_long)})",
])

# ══════════════════════════════════════════════════════════════════════════════
# SHORT-TERM KPIs
# ══════════════════════════════════════════════════════════════════════════════
with tab_short:
    st.markdown(
        f"<p style='color:{D["muted"]};font-size:0.84rem'>"
        f"Short-term KPIs are measured <strong>during the project</strong>. "
        f"Link each KPI to the work package, task, deliverable or milestone it measures.</p>",
        unsafe_allow_html=True
    )

    with st.expander("➕ Add Short-Term KPI", expanded=not kpis_short):
        with st.form("kpi_short_form", clear_on_submit=True):
            sc1,sc2 = st.columns([1,4])
            with sc1: k_num   = st.text_input("KPI #", placeholder="KPI1")
            with sc2: k_title = st.text_input("Title *", placeholder="e.g. Number of trained participants")
            k_desc = st.text_area("Description", height=70)

            kc1,kc2,kc3 = st.columns(3)
            with kc1:
                k_level = st.selectbox("KPI Level", [
                    "project_impact","objective","work_package",
                    "task","deliverable","milestone"
                ])
            with kc2:
                k_unit  = st.selectbox("Unit", KPI_UNITS)
            with kc3:
                k_month = st.number_input("Target Month", min_value=1, max_value=120, value=12)

            kv1,kv2,kv3 = st.columns(3)
            with kv1: k_baseline = st.text_input("Baseline Value", value="0")
            with kv2: k_target   = st.text_input("Target Value",   placeholder="e.g. 100")
            with kv3:
                k_resp_sel = st.selectbox("Responsible Partner",
                                           ["— None —"]+list(part_opts.keys()),
                                           key="kpi_s_resp")
                k_resp_id  = part_opts.get(k_resp_sel)

            k_method = st.text_input("Measurement Method",
                                      placeholder="e.g. Attendance lists, surveys")
            k_verif  = st.text_input("Verification Source",
                                      placeholder="e.g. Project reports, published data")

            # Links to entities
            st.markdown("**Link this KPI to:**")
            lc1,lc2,lc3 = st.columns(3)
            with lc1:
                sel_obj_links  = st.multiselect("Objectives",   list(obj_opts.keys()),  key="kpi_s_obj")
                sel_wp_links   = st.multiselect("Work Packages",list(wp_opts.keys()),   key="kpi_s_wp")
            with lc2:
                sel_task_links = st.multiselect("Tasks",        list(task_opts.keys()), key="kpi_s_task")
                sel_del_links  = st.multiselect("Deliverables", list(del_opts.keys()),  key="kpi_s_del")
            with lc3:
                sel_ms_links   = st.multiselect("Milestones",   list(ms_opts.keys()),   key="kpi_s_ms")

            if st.form_submit_button("➕ Add Short-Term KPI", type="primary"):
                if not k_title.strip():
                    st.error("Title required.")
                else:
                    ok, kid = upsert_kpi({
                        "proposal_id":         proposal_id,
                        "kpi_number":          k_num.strip() or "KPI-?",
                        "kpi_title":           k_title.strip(),
                        "kpi_description":     k_desc.strip(),
                        "kpi_type":            "short_term",
                        "kpi_level":           k_level,
                        "baseline_value":      k_baseline.strip(),
                        "target_value":        k_target.strip(),
                        "unit":                k_unit,
                        "target_month":        k_month,
                        "measurement_method":  k_method.strip(),
                        "verification_source": k_verif.strip(),
                        "responsible_partner_id": k_resp_id,
                        "status":              "planned",
                    })
                    if ok and kid:
                        set_kpi_links(kid,"objective",   [obj_opts[l] for l in sel_obj_links])
                        set_kpi_links(kid,"work_package",[wp_opts[l]  for l in sel_wp_links])
                        set_kpi_links(kid,"task",        [task_opts[l] for l in sel_task_links])
                        set_kpi_links(kid,"deliverable", [del_opts[l] for l in sel_del_links])
                        set_kpi_links(kid,"milestone",   [ms_opts[l]  for l in sel_ms_links])
                        st.success("✅ KPI added!"); st.rerun()

    # Display short-term KPIs with edit
    for k in kpis_short:
        kid  = k["kpi_id"]
        knum = k.get("kpi_number","")
        acc  = D["accent"]; muted = D["muted"]

        with st.expander(
            f"📊 {knum}: {k.get('kpi_title','')}  ·  "
            f"Baseline {k.get('baseline_value','0')} → Target {k.get('target_value','')} {k.get('unit','')} · Month {k.get('target_month','?')}",
            expanded=False
        ):
            with st.form(f"edit_kpi_s_{kid}"):
                ek1,ek2 = st.columns([1,4])
                with ek1: e_knum   = st.text_input("KPI #", value=knum)
                with ek2: e_ktitle = st.text_input("Title", value=k.get("kpi_title",""))
                e_kdesc = st.text_area("Description", value=k.get("kpi_description",""), height=60)
                ekc1,ekc2,ekc3 = st.columns(3)
                with ekc1:
                    level_opts=["project_impact","objective","work_package","task","deliverable","milestone"]
                    cur_lev=k.get("kpi_level","project_impact")
                    e_klevel=st.selectbox("Level", level_opts,
                        index=level_opts.index(cur_lev) if cur_lev in level_opts else 0)
                with ekc2: e_kunit=st.selectbox("Unit", KPI_UNITS,
                        index=KPI_UNITS.index(k.get("unit","number")) if k.get("unit") in KPI_UNITS else 0)
                with ekc3: e_kmonth=st.number_input("Target Month", min_value=1, max_value=120,
                        value=int(k.get("target_month",12) or 12))
                ekv1,ekv2 = st.columns(2)
                with ekv1: e_kbase   = st.text_input("Baseline", value=str(k.get("baseline_value","0")))
                with ekv2: e_ktarget = st.text_input("Target",   value=str(k.get("target_value","")))
                e_kmethod = st.text_input("Measurement Method", value=k.get("measurement_method",""))
                e_kverif  = st.text_input("Verification Source", value=k.get("verification_source",""))
                sc1,sc2 = st.columns(2)
                with sc1:
                    if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                        ok5, _ = upsert_kpi({
                            "kpi_id": kid, "proposal_id": proposal_id,
                            "kpi_number": e_knum.strip(), "kpi_title": e_ktitle.strip(),
                            "kpi_description": e_kdesc.strip(), "kpi_type": "short_term",
                            "kpi_level": e_klevel, "unit": e_kunit,
                            "target_month": e_kmonth, "baseline_value": e_kbase.strip(),
                            "target_value": e_ktarget.strip(),
                            "measurement_method": e_kmethod.strip(),
                            "verification_source": e_kverif.strip(),
                        })
                        if ok5: st.success("Saved!"); st.rerun()
                with sc2:
                    if st.form_submit_button("🗑 Delete", use_container_width=True):
                        delete_kpi(kid); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# LONG-TERM KPIs
# ══════════════════════════════════════════════════════════════════════════════
with tab_long:
    st.markdown(
        f"<p style='color:{D["muted"]};font-size:0.84rem'>"
        f"Long-term KPIs measure <strong>post-project impact</strong>. "
        f"They are monitored 1, 2, 3 or 5 years after the project ends.</p>",
        unsafe_allow_html=True
    )

    with st.expander("➕ Add Long-Term KPI", expanded=not kpis_long):
        with st.form("kpi_long_form", clear_on_submit=True):
            lc1,lc2 = st.columns([1,4])
            with lc1: lk_num   = st.text_input("KPI #", placeholder="KPI-L1")
            with lc2: lk_title = st.text_input("Title *", placeholder="e.g. Policy impact")
            lk_desc = st.text_area("Description", height=70)

            ll1,ll2,ll3,ll4 = st.columns(4)
            with ll1: lk_unit     = st.selectbox("Unit", KPI_UNITS, key="lkpi_unit")
            with ll2: lk_post_yr  = st.selectbox("Post-Project Year",
                                                   [1,2,3,5,10], key="lkpi_yr")
            with ll3: lk_baseline = st.text_input("Baseline", value="0")
            with ll4: lk_target   = st.text_input("Target",   placeholder="e.g. 500")

            lk_method = st.text_input("Measurement Method",
                                       placeholder="e.g. Policy database, impact study")
            lk_verif  = st.text_input("Verification Source")
            lk_resp_sel = st.selectbox("Responsible Partner",
                                        ["— None —"]+list(part_opts.keys()),
                                        key="lkpi_resp")
            lk_resp_id  = part_opts.get(lk_resp_sel)

            if st.form_submit_button("➕ Add Long-Term KPI", type="primary"):
                if not lk_title.strip():
                    st.error("Title required.")
                else:
                    ok, _ = upsert_kpi({
                        "proposal_id":           proposal_id,
                        "kpi_number":            lk_num.strip() or "KPIL-?",
                        "kpi_title":             lk_title.strip(),
                        "kpi_description":       lk_desc.strip(),
                        "kpi_type":              "long_term",
                        "kpi_level":             "project_impact",
                        "baseline_value":        lk_baseline.strip(),
                        "target_value":          lk_target.strip(),
                        "unit":                  lk_unit,
                        "post_project_year":     lk_post_yr,
                        "measurement_method":    lk_method.strip(),
                        "verification_source":   lk_verif.strip(),
                        "responsible_partner_id":lk_resp_id,
                        "status":                "planned",
                    })
                    if ok: st.success("✅ Long-term KPI added!"); st.rerun()

    for k in kpis_long:
        kid  = k["kpi_id"]
        knum = k.get("kpi_number","")
        warn = D["warning"]

        with st.expander(
            f"🔭 {knum}: {k.get('kpi_title','')}  ·  "
            f"Year +{k.get('post_project_year','?')} · Target {k.get('target_value','')} {k.get('unit','')}",
            expanded=False
        ):
            with st.form(f"edit_kpi_l_{kid}"):
                lk1,lk2 = st.columns([1,4])
                with lk1: e_lknum   = st.text_input("KPI #", value=knum)
                with lk2: e_lktitle = st.text_input("Title", value=k.get("kpi_title",""))
                e_lkdesc = st.text_area("Description", value=k.get("kpi_description",""), height=60)
                ll1,ll2,ll3,ll4 = st.columns(4)
                with ll1: e_lkunit  = st.selectbox("Unit", KPI_UNITS,
                        index=KPI_UNITS.index(k.get("unit","number")) if k.get("unit") in KPI_UNITS else 0,
                        key=f"lku_{kid}")
                with ll2: e_lkyr    = st.selectbox("Post-Project Year", [1,2,3,5,10],
                        index=[1,2,3,5,10].index(k.get("post_project_year",1)) if k.get("post_project_year") in [1,2,3,5,10] else 0,
                        key=f"lky_{kid}")
                with ll3: e_lkbase  = st.text_input("Baseline", value=str(k.get("baseline_value","0")))
                with ll4: e_lktarget= st.text_input("Target",   value=str(k.get("target_value","")))
                e_lkmethod = st.text_input("Measurement Method", value=k.get("measurement_method",""))
                lsc1,lsc2 = st.columns(2)
                with lsc1:
                    if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                        ok6, _ = upsert_kpi({
                            "kpi_id": kid, "proposal_id": proposal_id,
                            "kpi_number": e_lknum.strip(), "kpi_title": e_lktitle.strip(),
                            "kpi_description": e_lkdesc.strip(), "kpi_type": "long_term",
                            "kpi_level": "project_impact", "unit": e_lkunit,
                            "post_project_year": e_lkyr,
                            "baseline_value": e_lkbase.strip(),
                            "target_value": e_lktarget.strip(),
                            "measurement_method": e_lkmethod.strip(),
                        })
                        if ok6: st.success("Saved!"); st.rerun()
                with lsc2:
                    if st.form_submit_button("🗑 Delete", use_container_width=True):
                        delete_kpi(kid); st.rerun()

# ── Gantt ─────────────────────────────────────────────────────────────────────
gantt_data = get_gantt_data(proposal_id)
render_gantt(gantt_data, proposal_id, expanded=False)
