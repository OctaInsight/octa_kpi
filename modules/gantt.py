"""
Octa KPI — Gantt Chart Module
Interactive Plotly chart (Streamlit) + Matplotlib export (SVG/PDF/EPS).
A4 landscape = 11.69 × dynamic height inches. All fonts >= 7pt.
All matplotlib colors as float tuples (no rgba() CSS strings).
Deliverable/Milestone markers plotted on TASK rows, not WP rows.
"""
import io
import plotly.graph_objects as go
import streamlit as st
from config import WP_COLORS, DARK

# ── Colour helpers ─────────────────────────────────────────────────────────────
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def _hex_to_rgba(h, a):
    return _hex_to_rgb(h) + (a,)

# ═══════════════════════════════════════════════════════════════════════════════
# PLOTLY (interactive)
# ═══════════════════════════════════════════════════════════════════════════════

def build_gantt(gantt_data, proposal_id, max_month=None):
    wps   = gantt_data.get("work_packages", [])
    tasks = gantt_data.get("tasks", [])
    dels  = gantt_data.get("deliverables", [])
    mss   = gantt_data.get("milestones", [])
    if not wps and not tasks:
        return None

    all_months = (
        [int(w["start_month"]) for w in wps if w.get("start_month")] +
        [int(w["end_month"])   for w in wps if w.get("end_month")]   +
        [int(t["start_month"]) for t in tasks if t.get("start_month")] +
        [int(t["end_month"])   for t in tasks if t.get("end_month")]   +
        [int(d["delivery_month"]) for d in dels if d.get("delivery_month")] +
        [int(m["due_month"])   for m in mss if m.get("due_month")]
    )
    total_months = max_month or (max(all_months) if all_months else 36)

    fig = go.Figure()
    y_labels = []; wp_y_map = {}; task_y_map = {}

    for i, wp in enumerate(sorted(wps, key=lambda x: x.get("wp_number",""))):
        y_labels.append(f"📦 {wp['wp_number']}: {wp.get('wp_title','')[:38]}")
        wp_y_map[wp["wp_id"]] = len(y_labels) - 1
        for t in sorted([x for x in tasks if x.get("wp_id")==wp["wp_id"]],
                        key=lambda x: x.get("task_number","")):
            y_labels.append(f"   ⚙️ {t['task_number']}: {t.get('task_title','')[:33]}")
            task_y_map[t["task_id"]] = len(y_labels) - 1

    chart_height = max(300, len(y_labels) * 42 + 120)

    for i, wp in enumerate(sorted(wps, key=lambda x: x.get("wp_number",""))):
        color = WP_COLORS[i % len(WP_COLORS)]
        sm = wp.get("start_month"); em = wp.get("end_month")
        if sm is None or em is None: continue
        y_idx = wp_y_map[wp["wp_id"]]
        fig.add_trace(go.Bar(
            name=wp["wp_number"], x=[int(em)-int(sm)+1],
            y=[y_labels[y_idx]], base=[int(sm)-1], orientation="h",
            marker=dict(color=color, opacity=0.85, line=dict(width=0)),
            width=0.55,
            hovertemplate=(f"<b>{wp['wp_number']}: {wp.get('wp_title','')}</b><br>"
                           f"Month {sm}–{em}<extra></extra>"),
            showlegend=True, legendgroup=wp["wp_number"],
        ))
        for t in [x for x in tasks if x.get("wp_id")==wp["wp_id"]]:
            tsm=t.get("start_month"); tem=t.get("end_month")
            t_idx=task_y_map.get(t["task_id"])
            if tsm is None or tem is None or t_idx is None: continue
            fig.add_trace(go.Bar(
                x=[int(tem)-int(tsm)+1], y=[y_labels[t_idx]],
                base=[int(tsm)-1], orientation="h",
                marker=dict(color=color, opacity=0.5, line=dict(width=0)),
                width=0.38,
                hovertemplate=(f"<b>{t['task_number']}: {t.get('task_title','')}</b><br>"
                               f"Month {tsm}–{tem}<extra></extra>"),
                showlegend=False, legendgroup=wp["wp_number"],
            ))

    # Deliverables on task rows
    dx, dy, dt, dl = [], [], [], []
    for d in dels:
        dm=d.get("delivery_month")
        if not dm: continue
        y_idx = task_y_map.get(d.get("task_id")) if d.get("task_id") else None
        if y_idx is None: y_idx = wp_y_map.get(d.get("wp_id"))
        if y_idx is None: continue
        dx.append(int(dm)-0.5); dy.append(y_labels[y_idx])
        dt.append(f"📄 {d['deliverable_number']}: {d.get('deliverable_title','')}<br>Month {dm}")
        dl.append(d.get("deliverable_number","D"))
    if dx:
        fig.add_trace(go.Scatter(x=dx, y=dy, mode="markers+text",
            marker=dict(symbol="diamond", size=13, color=DARK["success"],
                        line=dict(color="white", width=1)),
            text=dl, textposition="top center",
            textfont=dict(size=8, color=DARK["success"]),
            hovertext=dt, hoverinfo="text", name="Deliverables", showlegend=True))

    # Milestones on task rows
    mx, my, mt, ml = [], [], [], []
    for m in mss:
        dm=m.get("due_month")
        if not dm: continue
        y_idx = task_y_map.get(m.get("task_id")) if m.get("task_id") else None
        if y_idx is None: y_idx = wp_y_map.get(m.get("wp_id"))
        if y_idx is None: continue
        mx.append(int(dm)-0.5); my.append(y_labels[y_idx])
        mt.append(f"🏁 {m['milestone_number']}: {m.get('milestone_title','')}<br>Month {dm}")
        ml.append(m.get("milestone_number","MS"))
    if mx:
        fig.add_trace(go.Scatter(x=mx, y=my, mode="markers+text",
            marker=dict(symbol="star", size=15, color=DARK["warning"],
                        line=dict(color="white", width=1)),
            text=ml, textposition="bottom center",
            textfont=dict(size=8, color=DARK["warning"]),
            hovertext=mt, hoverinfo="text", name="Milestones", showlegend=True))

    for m in range(1, total_months+1, 6):
        fig.add_vline(x=m-0.5, line_dash="dot",
                      line_color="rgba(255,255,255,0.1)", line_width=1)

    fig.update_layout(
        barmode="overlay", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=chart_height,
        margin=dict(l=0,r=20,t=30,b=40), font_color=DARK["text"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="left", x=0, font=dict(size=11),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Project Month", range=[0,total_months+0.5],
                   tickmode="linear", tick0=1,
                   dtick=1 if total_months<=24 else 3,
                   gridcolor="rgba(255,255,255,0.06)",
                   showline=True, linecolor=DARK["border"]),
        yaxis=dict(showgrid=False, tickfont=dict(size=11), autorange="reversed"),
    )
    return fig


def render_gantt(gantt_data, proposal_id, duration=36, expanded=True):
    with st.expander("📅 Project Timeline (Gantt Chart)", expanded=expanded):
        if not gantt_data.get("work_packages") and not gantt_data.get("tasks"):
            muted = DARK["muted"]
            st.markdown(
                f"<p style='color:{muted};font-size:0.85rem'>"
                f"Add Work Packages and Tasks to see the Gantt chart.</p>",
                unsafe_allow_html=True)
            return
        suc=DARK["success"]; warn=DARK["warning"]
        st.markdown(
            f"<div style='display:flex;gap:1.5rem;flex-wrap:wrap;"
            f"margin-bottom:0.5rem;font-size:0.78rem'>"
            f"<span>📦 Work Package bars</span>"
            f"<span style='color:{suc}'>◆ Deliverable (on task row)</span>"
            f"<span style='color:{warn}'>★ Milestone (on task row)</span></div>",
            unsafe_allow_html=True)
        fig = build_gantt(gantt_data, proposal_id, max_month=duration)
        if fig:
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MATPLOTLIB SHARED BUILDER (SVG / PDF / EPS)
# All colors as float tuples — NO rgba() CSS strings.
# A4 landscape width = 11.69 in. Fonts >= 7pt.
# ═══════════════════════════════════════════════════════════════════════════════

def _build_mpl_figure(gantt_data, title, max_month, dark_bg=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    wps   = sorted(gantt_data.get("work_packages",[]), key=lambda x: x.get("wp_number",""))
    tasks = gantt_data.get("tasks",[])
    dels  = gantt_data.get("deliverables",[])
    mss   = gantt_data.get("milestones",[])

    # Build rows and maps together
    rows=[]; wp_row_map={}; task_row_map={}
    for i, wp in enumerate(wps):
        color=WP_COLORS[i%len(WP_COLORS)]
        sm=int(wp.get("start_month") or 1)
        em=int(wp.get("end_month")   or max_month)
        wp_row_map[wp["wp_id"]]=len(rows)
        rows.append((f"{wp['wp_number']}: {wp.get('wp_title','')[:32]}",
                     sm,em,color,"wp"))
        for t in sorted([x for x in tasks if x.get("wp_id")==wp["wp_id"]],
                        key=lambda x: x.get("task_number","")):
            task_row_map[t["task_id"]]=len(rows)
            rows.append(
                (f"  {t['task_number']}: {t.get('task_title','')[:30]}",
                 int(t.get("start_month") or sm),
                 int(t.get("end_month")   or em),
                 color,"task"))

    n_rows=len(rows)
    if n_rows==0: return None, None

    fig_w  = 11.69                  # A4 landscape width
    fig_h  = max(8.27, n_rows*0.44+2.0)
    bg_c   = "#0f1421" if dark_bg else "white"
    area_c = "#1a2235" if dark_bg else "#f8f9fa"
    txt_c  = "white"   if dark_bg else "#1a1a2e"
    # All grid/spine colors as float tuples
    grid_c = (1,1,1,0.10) if dark_bg else (0.82,0.82,0.82,1.0)
    spine_c= _hex_to_rgba("#2d4a7a",1.0) if dark_bg else (0.72,0.72,0.85,1.0)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(bg_c)
    ax.set_facecolor(area_c)

    for idx,(label,sm,em,color,rtype) in enumerate(rows):
        y=n_rows-idx-1; w=em-sm+1
        alpha=0.88 if rtype=="wp" else 0.55
        h=0.58     if rtype=="wp" else 0.36
        rgb=_hex_to_rgb(color)
        bar=mpatches.FancyBboxPatch(
            (sm-1,y-h/2),w,h,boxstyle="round,pad=0.04",
            facecolor=rgb+(alpha,), edgecolor="none")
        ax.add_patch(bar)
        fsize  = 8 if rtype=="wp" else 7
        fweight= "bold" if rtype=="wp" else "normal"
        fc     = txt_c if dark_bg else ("white" if rtype=="wp" else "#222222")
        ax.text(sm-0.5, y, label.strip(), va="center", ha="left",
                fontsize=fsize, color=fc, fontweight=fweight, clip_on=True)
        ax.text(em+0.15, y, f"M{sm}–M{em}", va="center", ha="left",
                fontsize=7,
                color=(0.67,0.73,0.8,0.9) if dark_bg else (0.5,0.5,0.5,1),
                clip_on=True)

    # Deliverables on task rows
    del_c=_hex_to_rgba("#6fcf97",1.0)
    for d in dels:
        dm=d.get("delivery_month")
        if not dm: continue
        ridx=task_row_map.get(d.get("task_id")) if d.get("task_id") else None
        if ridx is None: ridx=wp_row_map.get(d.get("wp_id"))
        if ridx is None: continue
        y=n_rows-ridx-1
        ax.plot(int(dm)-0.5,y+0.36,marker="D",color=del_c,markersize=8,zorder=6)
        ax.text(int(dm)-0.5,y+0.56,d.get("deliverable_number","D"),
                ha="center",fontsize=7,color=del_c,fontweight="bold",clip_on=True)

    # Milestones on task rows
    ms_c=_hex_to_rgba("#f6cc52",1.0)
    for m in mss:
        dm=m.get("due_month")
        if not dm: continue
        ridx=task_row_map.get(m.get("task_id")) if m.get("task_id") else None
        if ridx is None: ridx=wp_row_map.get(m.get("wp_id"))
        if ridx is None: continue
        y=n_rows-ridx-1
        ax.plot(int(dm)-0.5,y-0.36,marker="*",color=ms_c,markersize=11,zorder=6)
        ax.text(int(dm)-0.5,y-0.6,m.get("milestone_number","MS"),
                ha="center",fontsize=7,color=ms_c,fontweight="bold",clip_on=True)

    # Axes
    ax.set_xlim(0, max_month+0.5); ax.set_ylim(-0.9, n_rows)
    ax.set_yticks([])
    step=3 if max_month>24 else 1
    ticks=list(range(0,max_month+1,step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks], color=txt_c, fontsize=7)
    ax.set_xlabel("Project Month", color=txt_c, fontsize=8)
    ax.tick_params(colors=txt_c, labelsize=7)
    for sp in ax.spines.values(): sp.set_edgecolor(spine_c)
    ax.set_title(title, color=txt_c, fontsize=10, fontweight="bold", pad=8)
    ax.grid(axis="x", color=grid_c, linestyle="--", linewidth=0.5)

    legend_elements=[
        mpatches.Patch(facecolor=del_c, label="◆ Deliverable"),
        mpatches.Patch(facecolor=ms_c,  label="★ Milestone"),
    ]
    ax.legend(handles=legend_elements, loc="upper right",
              facecolor=area_c, edgecolor=spine_c,
              labelcolor=txt_c, fontsize=7)

    plt.tight_layout(pad=0.8)
    return fig, ax


def build_gantt_svg(gantt_data, title="Project Gantt Chart", max_month=36):
    """SVG — editable in CorelDraw, Inkscape, Canva, Illustrator."""
    try:
        import matplotlib.pyplot as plt
        fig, _ = _build_mpl_figure(gantt_data, title, max_month, dark_bg=True)
        if fig is None: return None
        buf=io.BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig); buf.seek(0); return buf.read()
    except Exception as e:
        st.error(f"Gantt SVG error: {e}"); return None


def build_gantt_pdf(gantt_data, title="Project Gantt Chart", max_month=36):
    """PDF — A4 landscape, white background."""
    try:
        import matplotlib.pyplot as plt
        fig, _ = _build_mpl_figure(gantt_data, title, max_month, dark_bg=False)
        if fig is None: return None
        buf=io.BytesIO()
        fig.savefig(buf, format="pdf", bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig); buf.seek(0); return buf.read()
    except Exception as e:
        st.error(f"Gantt PDF error: {e}"); return None


def build_gantt_eps(gantt_data, title="Project Gantt Chart", max_month=36):
    """EPS — fully editable in CorelDraw and Illustrator (white background)."""
    try:
        import matplotlib.pyplot as plt
        fig, _ = _build_mpl_figure(gantt_data, title, max_month, dark_bg=False)
        if fig is None: return None
        fig.patch.set_alpha(1.0)   # EPS has no transparency
        buf=io.BytesIO()
        fig.savefig(buf, format="eps", bbox_inches="tight", facecolor="white")
        plt.close(fig); buf.seek(0); return buf.read()
    except Exception as e:
        st.error(f"Gantt EPS error: {e}"); return None


# Backward-compat alias
def build_gantt_matplotlib(gantt_data, title="Project Gantt Chart", max_month=36):
    return build_gantt_svg(gantt_data, title, max_month)
