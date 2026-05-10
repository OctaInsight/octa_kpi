"""Octa KPI — Budget Page (per Partner, per WP, all 7 categories)."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import (
    get_work_packages, get_all_partners, get_budget_entries,
    upsert_budget_entry, get_personnel_costs, upsert_personnel_cost,
    delete_personnel_cost, get_overhead_settings, upsert_overhead_settings,
    get_budget_summary, get_gantt_data, get_proposal_partners,
)
from modules.gantt import render_gantt
from config import BUDGET_LABELS, DARK as D
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Budget — Octa", page_icon="💶",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id","")
if not proposal_id:
    st.warning("No proposal selected.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("Budget Designer", f"Proposal: {proposal_id}", "💶")
if st.button("← Home"): st.switch_page("app.py")

wps          = get_work_packages(proposal_id)
prop_partners = get_proposal_partners(proposal_id)
all_partners  = prop_partners if prop_partners else get_all_partners()

if not wps:
    st.info("Add Work Packages first before entering budget data.")
    if st.button("→ Go to Work Packages"): st.switch_page("pages/work_packages.py")
    st.stop()

partner_opts = {p.get("short_name","") or p.get("full_name","")[:30]: p["id"]
                for p in all_partners}
wp_opts      = {f"{w['wp_number']}: {w.get('wp_title','')[:40]}": w["wp_id"]
                for w in wps}

# ── Overhead settings ─────────────────────────────────────────────────────────
section_label("⚙️ Overhead / Indirect Cost Settings")
oh_settings = get_overhead_settings(proposal_id)
with st.expander("Configure overhead calculation", expanded=False):
    oh_pct = st.number_input(
        "Overhead percentage (%)",
        min_value=0.0, max_value=100.0,
        value=float(oh_settings.get("overhead_percentage",25.0)),
        step=0.5, key="oh_pct"
    )
    st.caption("Overhead applies to: Personnel + Travel + Equipment + Other Goods & Services")
    st.caption("Overhead EXCLUDES: Subcontracting and Fund for Third Parties (standard EU rule)")
    if st.button("💾 Save Overhead Settings"):
        upsert_overhead_settings({"proposal_id": proposal_id,
                                   "overhead_percentage": oh_pct})
        st.success("Saved!"); st.rerun()

# ── Budget entry form ─────────────────────────────────────────────────────────
section_label("💶 Enter Budget by WP & Partner")

sel_wp_label  = st.selectbox("Select Work Package", list(wp_opts.keys()), key="bwp")
sel_wp_id     = wp_opts[sel_wp_label]
sel_par_label = st.selectbox("Select Partner",      list(partner_opts.keys()), key="bpar")
sel_par_id    = partner_opts[sel_par_label]

# Load existing entries for this WP × partner
existing = get_budget_entries(proposal_id, wp_id=sel_wp_id, partner_id=sel_par_id)
existing_map = {e["cost_category"]: e for e in existing}

st.markdown(
    f"<p style='color:{D["muted"]};font-size:0.84rem'>"
    f"Enter planned budget for <strong>{sel_wp_label}</strong> / "
    f"<strong>{sel_par_label}</strong>.</p>",
    unsafe_allow_html=True
)

# ─── Category tabs ────────────────────────────────────────────────────────────
CATS  = ["personnel","travel","equipment","other_goods_services",
         "subcontracting","third_parties"]
ICONS = {"personnel":"👥","travel":"✈️","equipment":"🖥️",
         "other_goods_services":"📦","subcontracting":"🤝",
         "third_parties":"🎁","overhead":"📐"}

cat_tabs = st.tabs([f"{ICONS.get(c,'💶')} {BUDGET_LABELS[c].split('(')[0].strip()}"
                    for c in CATS])

for i, cat in enumerate(CATS):
    with cat_tabs[i]:
        existing_entry = existing_map.get(cat)
        cur_amount = float(existing_entry.get("planned_amount",0) or 0) if existing_entry else 0.0
        eid        = existing_entry.get("budget_entry_id") if existing_entry else None

        st.markdown(f"**{BUDGET_LABELS[cat]}**")

        # ── Personnel: detail form with PM × rate ─────────────────────────────
        if cat == "personnel":
            st.caption("Add individual staff profiles. Total is calculated automatically.")
            if eid:
                pc_rows = get_personnel_costs(eid)
                if pc_rows:
                    total_pc = sum(float(r.get("calculated_cost",0) or 0) for r in pc_rows)
                    for row in pc_rows:
                        calc = float(row.get("calculated_cost",0) or 0)
                        pid  = row["personnel_cost_id"]
                        muted = D["muted"]; txt = D["text"]
                        st.markdown(
                            f"<div style='background:{D["bg3"]};border-radius:8px;"
                            f"padding:0.4rem 0.8rem;margin-bottom:0.2rem;font-size:0.83rem'>"
                            f"<strong style='color:{txt}'>{row.get('staff_profile','')}</strong> "
                            f"<span style='color:{muted}'>{row.get('staff_category','')}</span> · "
                            f"{row.get('person_months',0)} PM × "
                            f"€{float(row.get('monthly_rate',0) or 0):,.0f} = "
                            f"<strong style='color:{D["accent"]}'>€{calc:,.2f}</strong>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        if st.button(f"🗑 Remove", key=f"rpc_{pid}"):
                            delete_personnel_cost(pid)
                            # Recalculate entry total
                            remaining = [r for r in pc_rows if r["personnel_cost_id"] != pid]
                            new_total = sum(float(r.get("calculated_cost",0) or 0) for r in remaining)
                            upsert_budget_entry({
                                "proposal_id": proposal_id, "wp_id": sel_wp_id,
                                "partner_id": sel_par_id, "cost_category": cat,
                                "planned_amount": new_total,
                            })
                            st.rerun()
                    acc = D["accent"]
                    st.markdown(
                        f"**Total Personnel: "
                        f"<span style='color:{acc}'>€{total_pc:,.2f}</span>**",
                        unsafe_allow_html=True
                    )

            with st.form(f"pc_form_{sel_wp_id}_{sel_par_id}", clear_on_submit=True):
                pf1,pf2,pf3,pf4 = st.columns(4)
                with pf1: pc_profile  = st.text_input("Staff Profile", placeholder="Senior Researcher")
                with pf2: pc_category = st.text_input("Category",       placeholder="Category A")
                with pf3: pc_pm       = st.number_input("Person-Months", min_value=0.0, step=0.5)
                with pf4: pc_rate     = st.number_input("Monthly Rate (€)", min_value=0.0, step=100.0)
                calc_preview = pc_pm * pc_rate
                acc = D["accent"]
                st.markdown(
                    f"Calculated cost: **<span style='color:{acc}'>€{calc_preview:,.2f}</span>**",
                    unsafe_allow_html=True
                )
                if st.form_submit_button("➕ Add Staff Line", type="primary"):
                    if pc_pm <= 0:
                        st.error("Person-months must be > 0")
                    else:
                        # Ensure budget entry exists first
                        pc_rows_existing = get_personnel_costs(eid) if eid else []
                        existing_total   = sum(float(r.get("calculated_cost",0) or 0) for r in pc_rows_existing)
                        new_total        = existing_total + calc_preview
                        ok, new_eid = upsert_budget_entry({
                            "proposal_id": proposal_id, "wp_id": sel_wp_id,
                            "partner_id": sel_par_id, "cost_category": cat,
                            "planned_amount": new_total,
                        })
                        if ok and new_eid:
                            upsert_personnel_cost({
                                "budget_entry_id": new_eid,
                                "staff_profile":   pc_profile.strip(),
                                "staff_category":  pc_category.strip(),
                                "person_months":   pc_pm,
                                "monthly_rate":    pc_rate,
                            })
                            st.success("Staff line added!"); st.rerun()

        # ── Other categories: simple planned amount input ──────────────────────
        else:
            new_amount = st.number_input(
                f"Planned Amount (€)",
                min_value=0.0, step=500.0,
                value=cur_amount,
                key=f"budget_{cat}_{sel_wp_id}_{sel_par_id}"
            )
            if cat in ("travel","equipment","other_goods_services"):
                st.caption(f"This category is **included** in the overhead base (× {oh_settings.get('overhead_percentage',25)}%)")
            elif cat in ("subcontracting","third_parties"):
                st.caption("This category is **excluded** from the overhead base.")

            if st.button(f"💾 Save {cat.replace('_',' ').title()}",
                          key=f"save_budget_{cat}_{sel_wp_id}_{sel_par_id}",
                          type="primary"):
                ok, _ = upsert_budget_entry({
                    "proposal_id": proposal_id, "wp_id": sel_wp_id,
                    "partner_id": sel_par_id, "cost_category": cat,
                    "planned_amount": new_amount,
                })
                if ok: st.success("✅ Saved!"); st.rerun()

# ── Auto-calculate and save overhead ─────────────────────────────────────────
section_label("📐 Calculated Overhead")
oh_base_cats  = ["personnel","travel","equipment","other_goods_services"]
oh_base_total = sum(
    float((existing_map.get(c) or {}).get("planned_amount",0) or 0)
    for c in oh_base_cats
)
oh_pct_val    = float(oh_settings.get("overhead_percentage",25.0))
oh_calculated = oh_base_total * oh_pct_val / 100

acc = D["accent"]; muted = D["muted"]
st.markdown(
    f"<div style='background:{D["bg2"]};border:1px solid {D["border"]};"
    f"border-left:4px solid {acc};border-radius:10px;padding:1rem;'>"
    f"<div style='font-size:0.82rem;color:{muted}'>"
    f"Overhead base: €{oh_base_total:,.2f} × {oh_pct_val}%</div>"
    f"<div style='font-size:1.5rem;font-weight:700;color:{acc}'>"
    f"Overhead = €{oh_calculated:,.2f}</div></div>",
    unsafe_allow_html=True
)
if st.button("💾 Save Overhead to Budget", type="primary"):
    upsert_budget_entry({
        "proposal_id": proposal_id, "wp_id": sel_wp_id,
        "partner_id": sel_par_id, "cost_category": "overhead",
        "planned_amount": oh_calculated,
    })
    st.success("Overhead saved!"); st.rerun()

# ── Budget summary ────────────────────────────────────────────────────────────
section_label("📊 Budget Summary")
summary = get_budget_summary(proposal_id)

sk1,sk2,sk3 = st.columns(3)
for col, label, data, icon in [
    (sk1, "By Work Package",  summary["by_wp"],       "📦"),
    (sk2, "By Partner",       summary["by_partner"],   "🤝"),
    (sk3, "By Category",      summary["by_category"],  "💶"),
]:
    with col:
        st.markdown(f"**{icon} {label}**")
        if data:
            for k,v in sorted(data.items(), key=lambda x: -x[1]):
                bg2 = D["bg2"]
                st.markdown(
                    f"<div style='background:{bg2};border-radius:6px;"
                    f"padding:0.3rem 0.7rem;margin-bottom:2px;font-size:0.82rem;"
                    f"display:flex;justify-content:space-between'>"
                    f"<span style='color:{D["text"]}'>{k}</span>"
                    f"<strong style='color:{D["accent"]}'>€{v:,.0f}</strong></div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No budget data yet.")

total = summary["total"]
bg2   = D["bg2"]; acc = D["accent"]
st.markdown(
    f"<div style='background:{bg2};border:2px solid {acc};"
    f"border-radius:12px;padding:1rem 1.5rem;text-align:center;margin-top:0.5rem'>"
    f"<div style='color:{D["muted"]};font-size:0.82rem'>TOTAL PLANNED BUDGET</div>"
    f"<div style='font-size:2rem;font-weight:800;color:{acc}'>€{total:,.2f}</div>"
    f"</div>",
    unsafe_allow_html=True
)

# ── Gantt ─────────────────────────────────────────────────────────────────────
gantt_data = get_gantt_data(proposal_id)
render_gantt(gantt_data, proposal_id, expanded=False)
