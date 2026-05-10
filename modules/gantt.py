"""
Octa KPI — Gantt Chart Module
Interactive Plotly chart (for Streamlit display)
Matplotlib chart (for SVG/PDF export)
"""
import io
import plotly.graph_objects as go
import streamlit as st
from config import WP_COLORS, DARK


def build_gantt(gantt_data: dict, proposal_id: str,
                max_month: int = None) -> go.Figure:
    """
    Build an interactive Plotly Gantt chart.
    Shows: WPs (thick bars), Tasks (thinner bars),
           Deliverables (diamond markers), Milestones (star markers).
    """
    wps   = gantt_data.get("work_packages", [])
    tasks = gantt_data.get("tasks", [])
    dels  = gantt_data.get("deliverables", [])
    mss   = gantt_data.get("milestones", [])

    if not wps and not tasks:
        return None

    # Determine axis range
    all_months = []
    for w in wps:
        if w.get("start_month"): all_months.append(int(w["start_month"]))
        if w.get("end_month"):   all_months.append(int(w["end_month"]))
    for t in tasks:
        if t.get("start_month"): all_months.append(int(t["start_month"]))
        if t.get("end_month"):   all_months.append(int(t["end_month"]))
    for d in dels:
        if d.get("delivery_month"): all_months.append(int(d["delivery_month"]))
    for m in mss:
        if m.get("due_month"): all_months.append(int(m["due_month"]))

    total_months = max_month or (max(all_months) if all_months else 36)

    fig = go.Figure()
    D   = DARK

    # Build y-axis labels (WPs → tasks nested under each WP)
    y_labels = []
    wp_y_map = {}   # wp_id → y index
    task_y_map = {} # task_id → y index

    for i, wp in enumerate(sorted(wps, key=lambda x: x.get("wp_number",""))):
        y_labels.append(f"📦 {wp['wp_number']}: {wp.get('wp_title','')[:35]}")
        wp_y_map[wp["wp_id"]] = len(y_labels) - 1

        wp_tasks = [t for t in tasks if t.get("wp_id") == wp["wp_id"]]
        for t in sorted(wp_tasks, key=lambda x: x.get("task_number","")):
            y_labels.append(f"   ⚙️ {t['task_number']}: {t.get('task_title','')[:30]}")
            task_y_map[t["task_id"]] = len(y_labels) - 1

    total_rows = len(y_labels)

    # ── WP bars (thick) ───────────────────────────────────────────────────────
    for i, wp in enumerate(sorted(wps, key=lambda x: x.get("wp_number",""))):
        sm = wp.get("start_month")
        em = wp.get("end_month")
        if sm is None or em is None:
            continue
        color = WP_COLORS[i % len(WP_COLORS)]
        y_idx = wp_y_map[wp["wp_id"]]

        fig.add_trace(go.Bar(
            name=f"{wp['wp_number']}",
            x=[int(em) - int(sm) + 1],
            y=[y_labels[y_idx]],
            base=[int(sm) - 1],
            orientation="h",
            marker=dict(color=color, opacity=0.85, line=dict(width=0)),
            width=0.6,
            hovertemplate=(
                f"<b>{wp['wp_number']}: {wp.get('wp_title','')}</b><br>"
                f"Month {sm} – Month {em}<extra></extra>"
            ),
            showlegend=True,
            legendgroup=wp["wp_number"],
        ))

        # ── Task bars (thinner, same color, lighter) ──────────────────────────
        wp_tasks = [t for t in tasks if t.get("wp_id") == wp["wp_id"]]
        for t in wp_tasks:
            tsm = t.get("start_month")
            tem = t.get("end_month")
            if tsm is None or tem is None:
                continue
            t_y_idx = task_y_map.get(t["task_id"])
            if t_y_idx is None:
                continue
            fig.add_trace(go.Bar(
                x=[int(tem) - int(tsm) + 1],
                y=[y_labels[t_y_idx]],
                base=[int(tsm) - 1],
                orientation="h",
                marker=dict(color=color, opacity=0.55, line=dict(width=0)),
                width=0.4,
                hovertemplate=(
                    f"<b>{t['task_number']}: {t.get('task_title','')}</b><br>"
                    f"Month {tsm} – Month {tem}<br>"
                    f"Status: {t.get('status','planned')}<extra></extra>"
                ),
                showlegend=False,
                legendgroup=wp["wp_number"],
            ))

    # ── Deliverable markers (diamonds) ────────────────────────────────────────
    del_x, del_y, del_text = [], [], []
    for d in dels:
        dm = d.get("delivery_month")
        if not dm:
            continue
        wp_id = d.get("wp_id")
        if wp_id and wp_id in wp_y_map:
            del_x.append(int(dm) - 0.5)
            del_y.append(y_labels[wp_y_map[wp_id]])
            del_text.append(
                f"📄 {d['deliverable_number']}: {d.get('deliverable_title','')}<br>"
                f"Month {dm} · {d.get('deliverable_type','report')}"
            )

    if del_x:
        fig.add_trace(go.Scatter(
            x=del_x, y=del_y,
            mode="markers+text",
            marker=dict(
                symbol="diamond", size=12,
                color=DARK["success"],
                line=dict(color="white", width=1)
            ),
            text=[d.get("deliverable_number","D") for d in dels if d.get("delivery_month")],
            textposition="top center",
            textfont=dict(size=8, color=DARK["success"]),
            hovertext=del_text,
            hoverinfo="text",
            name="Deliverables",
            showlegend=True,
        ))

    # ── Milestone markers (stars) ─────────────────────────────────────────────
    ms_x, ms_y, ms_text = [], [], []
    for m in mss:
        dm = m.get("due_month")
        if not dm:
            continue
        wp_id = m.get("wp_id")
        if wp_id and wp_id in wp_y_map:
            ms_x.append(int(dm) - 0.5)
            ms_y.append(y_labels[wp_y_map[wp_id]])
            ms_text.append(
                f"🏁 {m['milestone_number']}: {m.get('milestone_title','')}<br>"
                f"Due: Month {dm}"
            )

    if ms_x:
        fig.add_trace(go.Scatter(
            x=ms_x, y=ms_y,
            mode="markers+text",
            marker=dict(
                symbol="star", size=14,
                color=DARK["warning"],
                line=dict(color="white", width=1)
            ),
            text=[m.get("milestone_number","MS") for m in mss if m.get("due_month")],
            textposition="bottom center",
            textfont=dict(size=8, color=DARK["warning"]),
            hovertext=ms_text,
            hoverinfo="text",
            name="Milestones",
            showlegend=True,
        ))

    # ── Month grid lines ──────────────────────────────────────────────────────
    for m in range(1, total_months + 1, 6):
        fig.add_vline(x=m - 0.5, line_dash="dot",
                      line_color="rgba(255,255,255,0.1)", line_width=1)

    # ── Layout ────────────────────────────────────────────────────────────────
    row_height = max(30, 500 // max(total_rows, 1))
    chart_height = max(300, total_rows * 40 + 120)

    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=chart_height,
        margin=dict(l=0, r=20, t=30, b=40),
        font_color=DARK["text"],
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="left", x=0,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="Project Month",
            range=[0, total_months + 0.5],
            tickmode="linear",
            tick0=1, dtick=1 if total_months <= 24 else 3,
            gridcolor="rgba(255,255,255,0.06)",
            showline=True,
            linecolor=DARK["border"],
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=11),
            autorange="reversed",
        ),
    )
    return fig


def render_gantt(gantt_data: dict, proposal_id: str,
                 duration: int = 36, expanded: bool = True):
    """Render the Gantt chart in Streamlit — call from any page."""
    with st.expander("📅 Project Timeline (Gantt Chart)", expanded=expanded):
        wps   = gantt_data.get("work_packages", [])
        tasks = gantt_data.get("tasks", [])
        dels  = gantt_data.get("deliverables", [])
        mss   = gantt_data.get("milestones", [])

        if not wps and not tasks:
            muted = DARK["muted"]
            st.markdown(
                f"<p style='color:{muted};font-size:0.85rem;padding:0.5rem 0'>"
                f"Add Work Packages and Tasks to see the Gantt chart.</p>",
                unsafe_allow_html=True
            )
            return

        # Legend chips
        acc = DARK["accent"]; suc = DARK["success"]; warn = DARK["warning"]
        st.markdown(
            f"<div style='display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:0.5rem;"
            f"font-size:0.78rem'>"
            f"<span>📦 <strong>Work Package</strong> — coloured bars</span>"
            f"<span style='color:{suc}'>◆ Deliverable</span>"
            f"<span style='color:{warn}'>★ Milestone</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        fig = build_gantt(gantt_data, proposal_id, max_month=duration)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough timeline data to render Gantt chart yet.")


# ── Matplotlib export version ─────────────────────────────────────────────────

def build_gantt_matplotlib(gantt_data: dict, title: str = "Project Gantt Chart",
                            max_month: int = 36) -> bytes | None:
    """
    Build a matplotlib Gantt chart for export as SVG or PDF.
    Returns SVG bytes.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyArrowPatch

        wps   = sorted(gantt_data.get("work_packages", []),
                       key=lambda x: x.get("wp_number",""))
        tasks = gantt_data.get("tasks", [])
        dels  = gantt_data.get("deliverables", [])
        mss   = gantt_data.get("milestones", [])

        # Build rows
        rows = []  # (label, start, end, color, type, number)
        wp_colors_used = {}
        for i, wp in enumerate(wps):
            color = WP_COLORS[i % len(WP_COLORS)]
            wp_colors_used[wp["wp_id"]] = color
            sm = int(wp.get("start_month") or 1)
            em = int(wp.get("end_month")   or max_month)
            rows.append((f"{wp['wp_number']}: {wp.get('wp_title','')[:30]}",
                         sm, em, color, "wp", wp["wp_number"]))
            for t in sorted([x for x in tasks if x.get("wp_id")==wp["wp_id"]],
                            key=lambda x: x.get("task_number","")):
                tsm = int(t.get("start_month") or sm)
                tem = int(t.get("end_month")   or em)
                rows.append(
                    (f"  {t['task_number']}: {t.get('task_title','')[:28]}",
                     tsm, tem, color, "task", t["task_number"])
                )

        n_rows = len(rows)
        fig_h  = max(6, n_rows * 0.45 + 2)
        fig, ax = plt.subplots(figsize=(max_month * 0.35, fig_h))
        fig.patch.set_facecolor("#0f1421")
        ax.set_facecolor("#1a2235")

        # Draw bars
        for i, (label, sm, em, color, rtype, num) in enumerate(rows):
            y     = n_rows - i - 1
            width = em - sm + 1
            alpha = 0.85 if rtype == "wp" else 0.55
            height= 0.55 if rtype == "wp" else 0.35
            bar   = mpatches.FancyBboxPatch(
                (sm - 1, y - height/2), width, height,
                boxstyle="round,pad=0.05",
                facecolor=color, alpha=alpha,
                edgecolor="none"
            )
            ax.add_patch(bar)
            ax.text(sm - 0.7, y, label, va="center", ha="left",
                    fontsize=7 if rtype == "task" else 8,
                    color="white", fontweight="bold" if rtype=="wp" else "normal")

        # Deliverable markers
        for d in dels:
            dm = d.get("delivery_month")
            if not dm: continue
            wp_id = d.get("wp_id")
            row_label = next((f"{w['wp_number']}: {w.get('wp_title','')[:30]}"
                              for w in wps if w["wp_id"]==wp_id), None)
            if row_label:
                row_idx = next((i for i, r in enumerate(rows) if r[0]==row_label), None)
                if row_idx is not None:
                    y = n_rows - row_idx - 1
                    ax.plot(int(dm)-0.5, y+0.35, "D",
                            color="#6fcf97", markersize=6, zorder=5)
                    ax.text(int(dm)-0.5, y+0.55,
                            d.get("deliverable_number","D"),
                            ha="center", fontsize=6, color="#6fcf97")

        # Milestone markers
        for m in mss:
            dm = m.get("due_month")
            if not dm: continue
            wp_id = m.get("wp_id")
            row_label = next((f"{w['wp_number']}: {w.get('wp_title','')[:30]}"
                              for w in wps if w["wp_id"]==wp_id), None)
            if row_label:
                row_idx = next((i for i, r in enumerate(rows) if r[0]==row_label), None)
                if row_idx is not None:
                    y = n_rows - row_idx - 1
                    ax.plot(int(dm)-0.5, y-0.35, "*",
                            color="#f6cc52", markersize=8, zorder=5)
                    ax.text(int(dm)-0.5, y-0.6,
                            m.get("milestone_number","MS"),
                            ha="center", fontsize=6, color="#f6cc52")

        # Axes
        ax.set_xlim(0, max_month)
        ax.set_ylim(-0.8, n_rows)
        ax.set_yticks([])
        ax.set_xticks(range(0, max_month+1, 3 if max_month > 24 else 1))
        ax.set_xticklabels(
            [str(m) for m in range(0, max_month+1, 3 if max_month > 24 else 1)],
            color="white", fontsize=8
        )
        ax.set_xlabel("Project Month", color="white", fontsize=9)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2d4a7a")

        ax.set_title(title, color="white", fontsize=11, fontweight="bold", pad=10)
        ax.grid(axis="x", color="rgba(255,255,255,0.1)",
                linestyle="--", linewidth=0.5)

        # Legend
        legend_elements = [
            mpatches.Patch(facecolor="#6fcf97", label="◆ Deliverable"),
            mpatches.Patch(facecolor="#f6cc52", label="★ Milestone"),
        ]
        ax.legend(handles=legend_elements, loc="upper right",
                  facecolor="#1a2235", edgecolor="#2d4a7a",
                  labelcolor="white", fontsize=7)

        plt.tight_layout()

        # Export as SVG bytes
        buf = io.BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        st.error(f"Gantt export error: {e}")
        return None


def build_gantt_pdf(gantt_data: dict, title: str = "Project Gantt Chart",
                     max_month: int = 36) -> bytes | None:
    """Export Gantt as PDF bytes using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        wps   = sorted(gantt_data.get("work_packages", []),
                       key=lambda x: x.get("wp_number",""))
        tasks = gantt_data.get("tasks", [])
        dels  = gantt_data.get("deliverables", [])
        mss   = gantt_data.get("milestones", [])

        rows = []
        for i, wp in enumerate(wps):
            color = WP_COLORS[i % len(WP_COLORS)]
            sm = int(wp.get("start_month") or 1)
            em = int(wp.get("end_month")   or max_month)
            rows.append((f"{wp['wp_number']}: {wp.get('wp_title','')[:30]}",
                         sm, em, color, "wp"))
            for t in sorted([x for x in tasks if x.get("wp_id")==wp["wp_id"]],
                            key=lambda x: x.get("task_number","")):
                rows.append(
                    (f"  {t['task_number']}: {t.get('task_title','')[:28]}",
                     int(t.get("start_month") or sm),
                     int(t.get("end_month")   or em),
                     color, "task")
                )

        n_rows = len(rows)
        fig, ax = plt.subplots(figsize=(max(14, max_month*0.4), max(8, n_rows*0.45+2)),
                               dpi=150)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#f8f9fa")

        for i, (label, sm, em, color, rtype) in enumerate(rows):
            y     = n_rows - i - 1
            width = em - sm + 1
            alpha = 0.85 if rtype=="wp" else 0.6
            height= 0.6  if rtype=="wp" else 0.35
            bar   = mpatches.FancyBboxPatch(
                (sm-1, y-height/2), width, height,
                boxstyle="round,pad=0.05",
                facecolor=color, alpha=alpha, edgecolor="white", linewidth=0.5
            )
            ax.add_patch(bar)
            ax.text(sm-0.5, y, label, va="center", ha="left",
                    fontsize=7 if rtype=="task" else 8,
                    color="white" if rtype=="wp" else "#333",
                    fontweight="bold" if rtype=="wp" else "normal")

        for d in dels:
            dm = d.get("delivery_month")
            if dm:
                ax.plot(int(dm)-0.5, 0, "D",
                        color="#28a745", markersize=8, zorder=5, clip_on=False)

        for m in mss:
            dm = m.get("due_month")
            if dm:
                ax.plot(int(dm)-0.5, 0, "*",
                        color="#f6c23e", markersize=10, zorder=5, clip_on=False)

        ax.set_xlim(0, max_month)
        ax.set_ylim(-0.8, n_rows)
        ax.set_yticks([])
        ax.set_xticks(range(0, max_month+1, 3 if max_month>24 else 1))
        ax.set_xlabel("Project Month", fontsize=9)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.grid(axis="x", color="#dee2e6", linestyle="--", linewidth=0.5)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="pdf", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        return None
