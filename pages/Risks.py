"""Octa KPI — Risk Management Page."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import (
    get_risks, upsert_risk, delete_risk,
    get_risk_wps, set_risk_wps,
    get_work_packages, get_all_partners, get_proposal_partners,
    get_gantt_data,
)
from modules.gantt import render_gantt
from config import DARK as D

st.set_page_config(page_title="Risks — Octa", page_icon="⚠️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id", "")
if not proposal_id:
    st.warning("No proposal selected.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("Risk Management",
            f"Proposal: {proposal_id} — Identify, assess and mitigate risks",
            "⚠️")
if st.button("← Home"): st.switch_page("app.py")

# ── Risk level colour map ─────────────────────────────────────────────────────
LEVEL_COLORS = {
    "critical": D["danger"],
    "high":     D["accent2"],
    "medium":   D["warning"],
    "low":      D["success"],
}
LIKELIHOOD_OPTS = ["high", "medium", "low"]
SEVERITY_OPTS   = ["high", "medium", "low"]
STATUS_OPTS     = ["open", "mitigated", "accepted", "closed"]

wps          = get_work_packages(proposal_id)
prop_partners= get_proposal_partners(proposal_id)
all_partners = prop_partners if prop_partners else get_all_partners()
risks        = get_risks(proposal_id)

wp_opts     = {f"{w['wp_number']}: {w.get('wp_title','')[:40]}": w["wp_id"] for w in wps}
partner_opts= {
    f"{p.get('short_name','') or p.get('full_name','')[:20]} — {p.get('full_name','')[:35]}": p["id"]
    for p in all_partners
}

muted = D["muted"]; acc = D["accent"]

# ── Risk matrix legend ────────────────────────────────────────────────────────
section_label("📊 Risk Level Matrix")
mc1, mc2, mc3, mc4 = st.columns(4)
for col, level, color, desc in [
    (mc1, "🔴 Critical", D["danger"],  "High likelihood + High severity"),
    (mc2, "🟠 High",     D["accent2"], "High+Medium or Medium+High"),
    (mc3, "🟡 Medium",   D["warning"], "Medium or mixed"),
    (mc4, "🟢 Low",      D["success"], "Low likelihood + Low severity"),
]:
    bg2 = D["bg2"]
    col.markdown(
        f"<div style='background:{bg2};border-top:3px solid {color};"
        f"border:1px solid {color}44;border-radius:10px;"
        f"padding:0.6rem 0.8rem;text-align:center'>"
        f"<div style='font-weight:700;color:{color}'>{level}</div>"
        f"<div style='font-size:0.72rem;color:{muted}'>{desc}</div></div>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ADD NEW RISK FORM
# ═══════════════════════════════════════════════════════════════════════════════
section_label("➕ Add New Risk")
with st.expander("New Risk Form", expanded=not risks):
    with st.form("add_risk_form", clear_on_submit=True):
        rc1, rc2 = st.columns([1, 4])
        with rc1:
            r_num   = st.text_input("Risk ID *", placeholder="R1")
        with rc2:
            r_title = st.text_input("Risk Title *",
                                     placeholder="e.g. Delay in data collection")
        r_desc = st.text_area("Risk Description", height=80,
                               placeholder="Describe the risk in detail…")

        ra1, ra2, ra3 = st.columns(3)
        with ra1:
            r_like = st.selectbox("Likelihood *", LIKELIHOOD_OPTS,
                                   index=1,
                                   format_func=lambda x: x.title())
        with ra2:
            r_sev  = st.selectbox("Severity *", SEVERITY_OPTS,
                                   index=1,
                                   format_func=lambda x: x.title())
        with ra3:
            # Preview computed risk level
            from modules.database import _compute_risk_level
            preview_level = _compute_risk_level(r_like, r_sev)
            lc = LEVEL_COLORS.get(preview_level, D["muted"])
            st.markdown(
                f"<div style='margin-top:1.5rem;background:{lc}22;"
                f"border:1px solid {lc}44;border-radius:8px;"
                f"padding:0.5rem;text-align:center'>"
                f"<div style='color:{lc};font-weight:700;font-size:0.9rem'>"
                f"⚡ {preview_level.title()}</div>"
                f"<div style='color:{muted};font-size:0.72rem'>Risk Level</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Related WPs
        r_wps = st.multiselect(
            "Related Work Package(s)",
            options=list(wp_opts.keys()),
            key="add_risk_wps",
            help="Select all WPs where this risk may occur"
        )

        r_mitigation = st.text_area("Mitigation Strategy *", height=100,
                                     placeholder="How will this risk be prevented or reduced?…")

        # Responsible partner
        resp_opts   = {"— Not assigned —": None} | partner_opts
        r_resp_sel  = st.selectbox("Responsible Partner", list(resp_opts.keys()),
                                    key="add_risk_resp")
        r_resp_id   = resp_opts[r_resp_sel]

        r_status    = st.selectbox("Risk Status", STATUS_OPTS,
                                    format_func=lambda x: x.title())

        if st.form_submit_button("⚠️ Add Risk", type="primary", use_container_width=True):
            if not r_num.strip() or not r_title.strip():
                st.error("❌ Risk ID and Title are required.")
            elif not r_mitigation.strip():
                st.error("❌ Mitigation Strategy is required.")
            else:
                ok, rid = upsert_risk({
                    "proposal_id":          proposal_id,
                    "risk_number":          r_num.strip().upper(),
                    "risk_title":           r_title.strip(),
                    "risk_description":     r_desc.strip(),
                    "likelihood":           r_like,
                    "severity":             r_sev,
                    "mitigation_strategy":  r_mitigation.strip(),
                    "responsible_partner_id": r_resp_id,
                    "status":               r_status,
                })
                if ok and rid:
                    set_risk_wps(rid, [wp_opts[l] for l in r_wps])
                    st.success("✅ Risk added!")
                    st.rerun()
                else:
                    st.error(f"❌ {rid}")

# ═══════════════════════════════════════════════════════════════════════════════
# RISK REGISTER
# ═══════════════════════════════════════════════════════════════════════════════
section_label(f"📋 Risk Register ({len(risks)} risks)")

if not risks:
    st.info("No risks defined yet. Use the form above to add the first risk.")
else:
    # Sort by risk level severity
    level_order = {"critical":0,"high":1,"medium":2,"low":3}
    risks_sorted = sorted(risks, key=lambda x: level_order.get(x.get("risk_level","medium"),2))

    for r in risks_sorted:
        rid    = r["risk_id"]
        rnum   = r.get("risk_number","")
        rtitle = r.get("risk_title","")
        level  = r.get("risk_level","medium")
        like   = r.get("likelihood","medium")
        sev    = r.get("severity","medium")
        status = r.get("status","open")
        lc     = LEVEL_COLORS.get(level, D["muted"])

        # Status color
        sc = {"open":D["danger"],"mitigated":D["success"],
              "accepted":D["warning"],"closed":D["muted"]}.get(status, D["muted"])

        linked_wps = get_risk_wps(rid)
        linked_wp_labels = [
            w.get("wp_number","") for w in wps if w["wp_id"] in linked_wps
        ]
        wp_str = " · ".join(linked_wp_labels) if linked_wp_labels else "—"

        with st.expander(
            f"⚠️ {rnum}: {rtitle}  ·  {level.title()}  ·  {status.title()}",
            expanded=False
        ):
            ec1, ec2 = st.columns([3, 2])

            with ec1:
                txt = D["text"]
                # Badges
                st.markdown(
                    f"<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem'>"
                    f"<span style='background:{lc}22;color:{lc};border:1px solid {lc}44;"
                    f"padding:2px 9px;border-radius:10px;font-size:0.75rem;font-weight:600'>"
                    f"⚡ {level.title()}</span>"
                    f"<span style='background:{D["bg3"]};color:{muted};"
                    f"padding:2px 9px;border-radius:10px;font-size:0.75rem'>"
                    f"Likelihood: {like.title()}</span>"
                    f"<span style='background:{D["bg3"]};color:{muted};"
                    f"padding:2px 9px;border-radius:10px;font-size:0.75rem'>"
                    f"Severity: {sev.title()}</span>"
                    f"<span style='background:{sc}22;color:{sc};border:1px solid {sc}44;"
                    f"padding:2px 9px;border-radius:10px;font-size:0.75rem;font-weight:600'>"
                    f"{status.title()}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                if r.get("risk_description"):
                    st.markdown(
                        f"<p style='color:{muted};font-size:0.85rem;margin:0.3rem 0'>"
                        f"{r['risk_description']}</p>",
                        unsafe_allow_html=True
                    )

                if r.get("mitigation_strategy"):
                    suc = D["success"]
                    st.markdown(
                        f"<div style='background:{suc}11;border-left:3px solid {suc};"
                        f"border-radius:8px;padding:0.5rem 0.8rem;margin-top:0.4rem'>"
                        f"<div style='font-size:0.72rem;color:{suc};font-weight:600;"
                        f"margin-bottom:0.2rem'>🛡️ MITIGATION STRATEGY</div>"
                        f"<div style='color:{txt};font-size:0.85rem'>"
                        f"{r['mitigation_strategy']}</div></div>",
                        unsafe_allow_html=True
                    )

                st.markdown(
                    f"<p style='color:{muted};font-size:0.8rem;margin-top:0.4rem'>"
                    f"📦 Related WPs: <strong style='color:{txt}'>{wp_str}</strong></p>",
                    unsafe_allow_html=True
                )

            with ec2:
                with st.form(f"edit_risk_{rid}"):
                    er1, er2 = st.columns([1, 3])
                    with er1: e_rnum   = st.text_input("ID", value=rnum)
                    with er2: e_rtitle = st.text_input("Title", value=rtitle)
                    e_rdesc  = st.text_area("Description",
                                             value=r.get("risk_description",""),
                                             height=60)
                    erl1, erl2 = st.columns(2)
                    with erl1:
                        e_like = st.selectbox("Likelihood", LIKELIHOOD_OPTS,
                            index=LIKELIHOOD_OPTS.index(like) if like in LIKELIHOOD_OPTS else 1,
                            format_func=lambda x: x.title(),
                            key=f"elike_{rid}")
                    with erl2:
                        e_sev  = st.selectbox("Severity", SEVERITY_OPTS,
                            index=SEVERITY_OPTS.index(sev) if sev in SEVERITY_OPTS else 1,
                            format_func=lambda x: x.title(),
                            key=f"esev_{rid}")

                    e_wps = st.multiselect(
                        "Related WPs",
                        options=list(wp_opts.keys()),
                        default=[l for l,v in wp_opts.items() if v in linked_wps],
                        key=f"ewps_{rid}"
                    )
                    e_mit = st.text_area("Mitigation Strategy",
                                          value=r.get("mitigation_strategy",""),
                                          height=70, key=f"emit_{rid}")

                    cur_resp = r.get("responsible_partner_id")
                    resp_opts2 = {"— Not assigned —": None} | partner_opts
                    resp_def2  = next((l for l,v in resp_opts2.items()
                                       if v == cur_resp), "— Not assigned —")
                    e_resp_sel = st.selectbox("Responsible Partner", list(resp_opts2.keys()),
                        index=list(resp_opts2.keys()).index(resp_def2),
                        key=f"eresp_{rid}")
                    e_resp_id  = resp_opts2[e_resp_sel]

                    cur_st     = r.get("status","open")
                    e_status   = st.selectbox("Status", STATUS_OPTS,
                        index=STATUS_OPTS.index(cur_st) if cur_st in STATUS_OPTS else 0,
                        format_func=lambda x: x.title(),
                        key=f"estat_{rid}")

                    sa1, sa2 = st.columns(2)
                    with sa1:
                        if st.form_submit_button("💾 Save", type="primary",
                                                  use_container_width=True):
                            ok2, _ = upsert_risk({
                                "risk_id":          rid,
                                "proposal_id":      proposal_id,
                                "risk_number":      e_rnum.strip().upper(),
                                "risk_title":       e_rtitle.strip(),
                                "risk_description": e_rdesc.strip(),
                                "likelihood":       e_like,
                                "severity":         e_sev,
                                "mitigation_strategy": e_mit.strip(),
                                "responsible_partner_id": e_resp_id,
                                "status":           e_status,
                            })
                            if ok2:
                                set_risk_wps(rid, [wp_opts[l] for l in e_wps])
                                st.success("✅ Saved!")
                                st.rerun()
                    with sa2:
                        if st.form_submit_button("🗑 Delete", use_container_width=True):
                            delete_risk(rid)
                            st.rerun()

# ── Gantt ─────────────────────────────────────────────────────────────────────
gantt_data = get_gantt_data(proposal_id)
render_gantt(gantt_data, proposal_id, expanded=False)
