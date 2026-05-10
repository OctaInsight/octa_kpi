"""
Octa KPI — Export Module
Generates EU-formatted Word tables for deliverables, KPIs, milestones
and exports the Gantt chart as SVG (editable in CorelDraw/Canva) and PDF.
"""
import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from config import DARK


# ── Table styling helpers ─────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    """Set table cell background colour."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tcPr.append(shd)


def _style_header_row(row, bg_hex: str = "1B2A4A"):
    for cell in row.cells:
        _set_cell_bg(cell, bg_hex)
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold       = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                run.font.size  = Pt(9)


def _add_header(doc: Document, text: str):
    h = doc.add_heading(text, level=2)
    h.runs[0].font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)


def _set_col_widths(table, widths_cm: list):
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths_cm):
                cell.width = Cm(widths_cm[i])


# ── Deliverables table (EU format) ───────────────────────────────────────────

def export_deliverables_docx(deliverables: list, proposal: dict) -> bytes:
    """EU-format deliverables table as .docx bytes."""
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(9)

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"List of Deliverables — {proposal.get('acronym','') or proposal.get('proposal_id','')}")
    run.bold = True; run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    doc.add_paragraph()

    headers = ["No.", "Deliverable Title", "WP", "Type",
               "Dissemination", "Month", "Status", "Description"]
    widths  = [1.2, 4.5, 1.0, 2.0, 2.2, 1.2, 2.0, 4.5]

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
    _style_header_row(table.rows[0])

    for d in sorted(deliverables, key=lambda x: x.get("deliverable_number","")):
        row = table.add_row().cells
        row[0].text = d.get("deliverable_number","")
        row[1].text = d.get("deliverable_title","")
        row[2].text = str(d.get("wp_id",""))
        row[3].text = d.get("deliverable_type","").replace("_"," ").title()
        row[4].text = d.get("dissemination_level","").title()
        row[5].text = str(d.get("delivery_month",""))
        row[6].text = d.get("status","planned").replace("_"," ").title()
        row[7].text = d.get("deliverable_description","")
        for cell in row:
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(2)

    _set_col_widths(table, widths)
    doc.add_paragraph(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ── Milestones table (EU format) ─────────────────────────────────────────────

def export_milestones_docx(milestones: list, proposal: dict) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.left_margin  = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Arial"; style.font.size = Pt(9)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"List of Milestones — {proposal.get('acronym','') or proposal.get('proposal_id','')}")
    run.bold = True; run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    doc.add_paragraph()

    headers = ["No.", "Milestone Title", "WP", "Month",
               "Means of Verification", "Status", "Description"]
    widths  = [1.2, 4.0, 1.0, 1.2, 4.5, 2.0, 4.5]

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
    _style_header_row(table.rows[0])

    for m in sorted(milestones, key=lambda x: x.get("due_month", 0) or 0):
        row = table.add_row().cells
        row[0].text = m.get("milestone_number","")
        row[1].text = m.get("milestone_title","")
        row[2].text = str(m.get("wp_id",""))
        row[3].text = str(m.get("due_month",""))
        row[4].text = m.get("means_of_verification","")
        row[5].text = m.get("status","planned").replace("_"," ").title()
        row[6].text = m.get("milestone_description","")

    _set_col_widths(table, widths)
    doc.add_paragraph(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ── KPI table (EU format) ─────────────────────────────────────────────────────

def export_kpis_docx(kpis_short: list, kpis_long: list,
                      proposal: dict) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.left_margin  = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Arial"; style.font.size = Pt(9)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"Key Performance Indicators — {proposal.get('acronym','') or proposal.get('proposal_id','')}")
    run.bold = True; run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    doc.add_paragraph()

    def _add_kpi_table(kpis, section_title):
        _add_header(doc, section_title)
        if not kpis:
            doc.add_paragraph("No KPIs defined.")
            return

        headers = ["No.", "KPI Title", "Level", "Baseline",
                   "Target", "Unit", "Month / Year",
                   "Measurement Method", "Verification Source",
                   "Description"]
        widths = [1.0, 3.5, 2.0, 1.5, 1.5, 1.5, 2.0, 4.0, 4.0, 4.0]

        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
        _style_header_row(table.rows[0])

        for k in sorted(kpis, key=lambda x: x.get("kpi_number","")):
            row = table.add_row().cells
            row[0].text = k.get("kpi_number","")
            row[1].text = k.get("kpi_title","")
            row[2].text = k.get("kpi_level","").replace("_"," ").title()
            row[3].text = str(k.get("baseline_value",""))
            row[4].text = str(k.get("target_value",""))
            row[5].text = k.get("unit","")
            timing = (str(k.get("target_month","")) if k.get("target_month")
                      else f"Year +{k.get('post_project_year','')}")
            row[6].text = timing
            row[7].text = k.get("measurement_method","")
            row[8].text = k.get("verification_source","")
            row[9].text = k.get("kpi_description","")

        _set_col_widths(table, widths)
        doc.add_paragraph()

    _add_kpi_table(kpis_short, "Short-Term KPIs (During Project)")
    _add_kpi_table(kpis_long,  "Long-Term KPIs (Post-Project Impact)")

    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ── Combined full export ──────────────────────────────────────────────────────

def export_full_docx(structure: dict) -> bytes:
    """Export all tables (deliverables + milestones + KPIs) in one Word document."""
    proposal    = structure.get("proposal") or {}
    deliverables= structure.get("deliverables", [])
    milestones  = structure.get("milestones", [])
    kpis_short  = structure.get("kpis_short", [])
    kpis_long   = structure.get("kpis_long", [])

    doc = Document()
    for section in doc.sections:
        section.left_margin  = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Arial"; style.font.size = Pt(9)

    # Cover
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(
        f"Work Plan Tables\n"
        f"{proposal.get('acronym','') or proposal.get('proposal_id','')}"
    )
    run.bold = True; run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    doc.add_page_break()

    # ── Deliverables ──────────────────────────────────────────────────────────
    _add_header(doc, "List of Deliverables")
    if deliverables:
        headers = ["No.", "Title", "WP", "Type", "Dissemination", "Month", "Description"]
        table   = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
        _style_header_row(table.rows[0])
        for d in sorted(deliverables, key=lambda x: x.get("deliverable_number","")):
            row = table.add_row().cells
            row[0].text = d.get("deliverable_number","")
            row[1].text = d.get("deliverable_title","")
            row[2].text = str(d.get("wp_id",""))
            row[3].text = d.get("deliverable_type","").replace("_"," ").title()
            row[4].text = d.get("dissemination_level","").title()
            row[5].text = str(d.get("delivery_month",""))
            row[6].text = d.get("deliverable_description","")
        _set_col_widths(table, [1.2, 4.0, 1.0, 2.0, 2.2, 1.2, 5.0])
    doc.add_paragraph()

    # ── Milestones ────────────────────────────────────────────────────────────
    doc.add_page_break()
    _add_header(doc, "List of Milestones")
    if milestones:
        headers = ["No.", "Title", "WP", "Month", "Means of Verification", "Description"]
        table   = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
        _style_header_row(table.rows[0])
        for m in sorted(milestones, key=lambda x: x.get("due_month",0) or 0):
            row = table.add_row().cells
            row[0].text = m.get("milestone_number","")
            row[1].text = m.get("milestone_title","")
            row[2].text = str(m.get("wp_id",""))
            row[3].text = str(m.get("due_month",""))
            row[4].text = m.get("means_of_verification","")
            row[5].text = m.get("milestone_description","")
    doc.add_paragraph()

    # ── Short-term KPIs ───────────────────────────────────────────────────────
    doc.add_page_break()
    _add_header(doc, "Short-Term KPIs")
    if kpis_short:
        headers = ["No.","Title","Baseline","Target","Unit","Month","Measurement","Description"]
        table   = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
        _style_header_row(table.rows[0])
        for k in kpis_short:
            row = table.add_row().cells
            row[0].text = k.get("kpi_number","")
            row[1].text = k.get("kpi_title","")
            row[2].text = str(k.get("baseline_value",""))
            row[3].text = str(k.get("target_value",""))
            row[4].text = k.get("unit","")
            row[5].text = str(k.get("target_month",""))
            row[6].text = k.get("measurement_method","")
            row[7].text = k.get("kpi_description","")

    # ── Long-term KPIs ────────────────────────────────────────────────────────
    doc.add_page_break()
    _add_header(doc, "Long-Term KPIs (Post-Project Impact)")
    if kpis_long:
        headers = ["No.","Title","Baseline","Target","Unit","Year After","Description"]
        table   = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
        _style_header_row(table.rows[0])
        for k in kpis_long:
            row = table.add_row().cells
            row[0].text = k.get("kpi_number","")
            row[1].text = k.get("kpi_title","")
            row[2].text = str(k.get("baseline_value",""))
            row[3].text = str(k.get("target_value",""))
            row[4].text = k.get("unit","")
            row[5].text = str(k.get("post_project_year",""))
            row[6].text = k.get("kpi_description","")

    doc.add_paragraph(f"\n\nGenerated by Octa Platform · {datetime.now().strftime('%Y-%m-%d')}")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
