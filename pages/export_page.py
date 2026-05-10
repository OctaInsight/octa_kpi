"""Octa KPI — Export Page."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK
from modules.database import get_full_structure, get_gantt_data, get_proposal
from modules.export import (export_deliverables_docx, export_milestones_docx,
                             export_kpis_docx, export_full_docx)
from modules.gantt import build_gantt_svg, build_gantt_pdf, build_gantt_eps, build_gantt_html

st.set_page_config(page_title="Export — Octa", page_icon="📥",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

proposal_id = st.session_state.get("selected_proposal_id","")
if not proposal_id:
    st.warning("No proposal selected.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

page_header("Export Work Plan", f"Proposal: {proposal_id}", "📥")
if st.button("← Home"): st.switch_page("app.py")

D       = DARK
acc_c   = D["accent"]
muted_c = D["muted"]

# Load data
structure  = get_full_structure(proposal_id)
proposal   = structure.get("proposal") or {}
gantt_data = get_gantt_data(proposal_id)
duration   = int(proposal.get("project_duration_months") or 36)
acronym    = proposal.get("acronym","") or proposal_id

st.markdown(
    f"<p style='color:{muted_c};font-size:0.85rem'>"
    f"Export EU-formatted tables and the Gantt chart in multiple formats. "
    f"Word documents are fully editable. "
    f"SVG files are vector-based and can be edited in CorelDraw, Inkscape, or Canva. "
    f"PDF files can be opened in Adobe Illustrator or Photoshop as smart objects.</p>",
    unsafe_allow_html=True
)

# ═════════════════════════════════════════════════════════════════════════════
# WORD EXPORTS
# ═════════════════════════════════════════════════════════════════════════════
section_label("📄 Word Documents (.docx) — EU Format")

ec1,ec2,ec3,ec4 = st.columns(4)

with ec1:
    st.markdown("**📋 All Tables Combined**")
    st.caption("Deliverables + Milestones + Short KPIs + Long KPIs in one document")
    if st.button("Generate Full Export", type="primary",
                 use_container_width=True, key="full_docx"):
        with st.spinner("Building document…"):
            data = export_full_docx(structure)
        st.download_button(
            "📥 Download Full Export.docx",
            data=data,
            file_name=f"{acronym}_Work_Plan_Tables.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_full"
        )

with ec2:
    st.markdown("**📄 Deliverables Table**")
    st.caption("EU-format deliverables list with all fields")
    if st.button("Generate Deliverables", use_container_width=True, key="del_docx"):
        with st.spinner("Building…"):
            data = export_deliverables_docx(structure.get("deliverables",[]), proposal)
        st.download_button(
            "📥 Download Deliverables.docx",
            data=data,
            file_name=f"{acronym}_Deliverables.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_del"
        )

with ec3:
    st.markdown("**🏁 Milestones Table**")
    st.caption("EU-format milestones list with means of verification")
    if st.button("Generate Milestones", use_container_width=True, key="ms_docx"):
        with st.spinner("Building…"):
            data = export_milestones_docx(structure.get("milestones",[]), proposal)
        st.download_button(
            "📥 Download Milestones.docx",
            data=data,
            file_name=f"{acronym}_Milestones.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_ms"
        )

with ec4:
    st.markdown("**📊 KPI Tables**")
    st.caption("Short-term and long-term KPIs in EU format")
    if st.button("Generate KPIs", use_container_width=True, key="kpi_docx"):
        with st.spinner("Building…"):
            data = export_kpis_docx(
                structure.get("kpis_short",[]),
                structure.get("kpis_long",[]),
                proposal
            )
        st.download_button(
            "📥 Download KPIs.docx",
            data=data,
            file_name=f"{acronym}_KPIs.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_kpi"
        )

# ═════════════════════════════════════════════════════════════════════════════
# GANTT CHART EXPORTS
# ═════════════════════════════════════════════════════════════════════════════
section_label("📅 Gantt Chart Export")

has_gantt = bool(gantt_data.get("work_packages"))
if not has_gantt:
    st.info("Add Work Packages first to generate a Gantt chart.")
else:
    gantt_title = f"{acronym} — Project Gantt Chart"
    dur_adj     = st.slider("Project duration (months)", 12, 72, duration, 6)

    gc1, gc2, gc3, gc4 = st.columns(4)

    with gc1:
        bg2 = D["bg2"]; border = D["border"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {acc_c};border-radius:10px;padding:1rem'>"
            f"<strong style='color:{D["text"]}'>🎨 SVG — Editable Vector</strong><br>"
            f"<span style='color:{muted_c};font-size:0.82rem'>"
            f"Best for CorelDraw, Inkscape, Canva, and Adobe Illustrator.<br>"
            f"Each bar and label is an independent, editable vector object.</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("Generate SVG Gantt", type="primary",
                     use_container_width=True, key="gantt_svg"):
            with st.spinner("Rendering Gantt chart as SVG…"):
                svg_bytes = build_gantt_svg(gantt_data, gantt_title, dur_adj)
            if svg_bytes:
                st.download_button(
                    "📥 Download Gantt.svg",
                    data=svg_bytes,
                    file_name=f"{acronym}_Gantt.svg",
                    mime="image/svg+xml",
                    key="dl_svg"
                )
                st.success("✅ SVG ready — open in CorelDraw, Canva, or Inkscape to edit.")
            else:
                st.error("Could not generate SVG.")

    with gc2:
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {D['accent2']};border-radius:10px;padding:1rem'>"
            f"<strong style='color:{D['text']}'>📄 PDF — Print & Photoshop</strong><br>"
            f"<span style='color:{muted_c};font-size:0.82rem'>"
            f"Best for printing and opening in Photoshop or Acrobat.<br>"
            f"High-resolution 150 DPI export with clean dark background.</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("Generate PDF Gantt", use_container_width=True, key="gantt_pdf"):
            with st.spinner("Rendering Gantt chart as PDF…"):
                pdf_bytes = build_gantt_pdf(gantt_data, gantt_title, dur_adj)
            if pdf_bytes:
                st.download_button(
                    "📥 Download Gantt.pdf",
                    data=pdf_bytes,
                    file_name=f"{acronym}_Gantt.pdf",
                    mime="application/pdf",
                    key="dl_pdf"
                )
                st.success("✅ PDF ready.")
            else:
                st.error("Could not generate PDF.")

    with gc3:
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {D['success']};border-radius:10px;padding:1rem'>"
            f"<strong style='color:{D['text']}'>🖊️ EPS — CorelDraw & Illustrator</strong><br>"
            f"<span style='color:{muted_c};font-size:0.82rem'>"
            f"Best for CorelDraw, Adobe Illustrator and professional print.<br>"
            f"Pure vector format — every object fully editable.</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("Generate EPS Gantt", use_container_width=True, key="gantt_eps"):
            with st.spinner("Rendering Gantt chart as EPS…"):
                eps_bytes = build_gantt_eps(gantt_data, gantt_title, dur_adj)
            if eps_bytes:
                st.download_button(
                    "📥 Download Gantt.eps",
                    data=eps_bytes,
                    file_name=f"{acronym}_Gantt.eps",
                    mime="application/postscript",
                    key="dl_eps"
                )
                st.success("✅ EPS ready — open in CorelDraw or Illustrator.")
            else:
                st.error("Could not generate EPS.")

    with gc4:
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:4px solid {D['accent']};border-radius:10px;padding:1rem'>"
            f"<strong style='color:{D['text']}'>🌐 HTML — Interactive</strong><br>"
            f"<span style='color:{muted_c};font-size:0.82rem'>"
            f"Fully interactive Gantt — zoom, pan, hover in any browser.<br>"
            f"Self-contained file, no internet required. Share as-is.</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("Generate HTML Gantt", use_container_width=True, key="gantt_html"):
            with st.spinner("Building interactive HTML…"):
                html_bytes = build_gantt_html(gantt_data, gantt_title, dur_adj)
            if html_bytes:
                st.download_button(
                    "📥 Download Gantt.html",
                    data=html_bytes,
                    file_name=f"{acronym}_Gantt.html",
                    mime="text/html",
                    key="dl_html"
                )
                st.success("✅ HTML ready — open in any browser.")
            else:
                st.error("Could not generate HTML.")

    # Preview
    section_label("👁 Gantt Preview")
    from modules.gantt import render_gantt
    render_gantt(gantt_data, proposal_id, duration=dur_adj, expanded=True)
