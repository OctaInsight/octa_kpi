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

    # Display short-term KPIs
    for k in kpis_short:
        kid   = k["kpi_id"]
        acc   = D["accent"]; muted = D["muted"]; txt = D["text"]
        bg2   = D["bg2"]; border = D["border"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {acc};border-radius:10px;"
            f"padding:0.8rem 1rem;margin-bottom:0.4rem'>"
            f"<div style='display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap'>"
            f"<strong style='color:{acc}'>{k['kpi_number']}</strong>"
            f"<strong style='color:{txt}'>{k.get('kpi_title','')}</strong>"
            f"<span style='color:{muted};font-size:0.78rem'>"
            f"Baseline: {k.get('baseline_value','0')} → Target: {k.get('target_value','')} "
            f"{k.get('unit','')} · Month {k.get('target_month','?')}</span>"
            f"</div></div>",
            unsafe_allow_html=True
        )
        if st.button(f"🗑 Delete {k['kpi_number']}", key=f"dkpi_s_{kid}"):
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
        warn = D["warning"]; muted = D["muted"]; txt = D["text"]
        bg2  = D["bg2"]; border = D["border"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {warn};border-radius:10px;"
            f"padding:0.8rem 1rem;margin-bottom:0.4rem'>"
            f"<strong style='color:{warn}'>{k['kpi_number']}</strong> "
            f"<strong style='color:{txt}'>{k.get('kpi_title','')}</strong>"
            f"<span style='color:{muted};font-size:0.78rem'> · "
            f"Year +{k.get('post_project_year','?')} after project · "
            f"Target: {k.get('target_value','')} {k.get('unit','')}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button(f"🗑 Delete {k['kpi_number']}", key=f"dkpi_l_{kid}"):
            delete_kpi(kid); st.rerun()

# ── Gantt ─────────────────────────────────────────────────────────────────────
gantt_data = get_gantt_data(proposal_id)
render_gantt(gantt_data, proposal_id, expanded=False)
