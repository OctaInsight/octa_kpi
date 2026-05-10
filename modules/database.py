"""Octa KPI & Work Plan Designer — Supabase database layer."""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


@st.cache_resource
def _client() -> Client:
    return create_client(st.secrets["supabase"]["url"],
                         st.secrets["supabase"]["key"])

def db() -> Client:
    return _client()

def _now(): return datetime.now(timezone.utc).isoformat()


# ── Proposals (read-only) ────────────────────────────────────────────────────

def get_all_proposals() -> list:
    try:
        return db().table("proposals").select(
            "proposal_id,acronym,proposal_title,status,lifecycle_status,"
            "project_start_date,project_end_date,project_duration_months,"
            "coordinator,partners_list,deadline"
        ).order("proposal_id", desc=True).execute().data or []
    except Exception:
        return []

def get_proposal(proposal_id: str) -> dict | None:
    try:
        r = db().table("proposals").select("*").eq("proposal_id", proposal_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None



def get_proposals_for_user(organisation: str = "", is_admin: bool = False) -> list:
    """
    Return proposals the user is allowed to access.
    Admins: all proposals.
    Regular users: only proposals where their organisation is the
                   coordinator OR appears in partners_list.
    """
    all_proposals = get_all_proposals()
    if is_admin or not organisation:
        return all_proposals

    import json
    org_lower = organisation.strip().lower()
    filtered  = []

    for p in all_proposals:
        # Check coordinator
        coord = (p.get("coordinator") or "").lower()
        if org_lower and (org_lower in coord or coord in org_lower):
            filtered.append(p)
            continue

        # Check partners_list (stored as JSONB array or comma list)
        plist = p.get("partners_list") or []
        if isinstance(plist, str):
            try:    plist = json.loads(plist)
            except: plist = [plist]
        for entry in plist:
            entry_lower = str(entry).lower().strip()
            if org_lower and (org_lower in entry_lower or entry_lower in org_lower):
                filtered.append(p)
                break

    return filtered

def get_proposal_partners(proposal_id: str) -> list:
    """
    Return partners involved in this proposal.
    Reads coordinator + partners_list from the proposals table,
    then looks each one up in the partners table by full_name match.
    Falls back to all partners if none found.
    """
    try:
        import json
        prop = get_proposal(proposal_id)
        if not prop:
            return get_all_partners()

        # Collect all partner names from the proposal
        names = []
        coord = (prop.get("coordinator") or "").strip()
        if coord:
            names.append(coord)
        plist = prop.get("partners_list") or []
        if isinstance(plist, str):
            try:    plist = json.loads(plist)
            except: plist = []
        names.extend([str(p).strip() for p in plist if p and str(p).strip()])

        if not names:
            return get_all_partners()

        # Fetch all partners and filter by name match
        all_p = get_all_partners()
        result, seen = [], set()
        for name in names:
            nl = name.lower()
            for p in all_p:
                pid = p["id"]
                if pid in seen:
                    continue
                fn = (p.get("full_name")  or "").lower()
                sn = (p.get("short_name") or "").lower()
                if nl in fn or fn in nl or (sn and (nl in sn or sn in nl)):
                    result.append(p)
                    seen.add(pid)
                    break

        # Always include at least the coordinator as a manual entry if not found
        if not result:
            return get_all_partners()
        return result
    except Exception:
        return get_all_partners()

def get_all_partners() -> list:
    try:
        return db().table("partners").select("id,full_name,short_name,country")\
                   .order("full_name").execute().data or []
    except Exception:
        return []


# ── Objectives ───────────────────────────────────────────────────────────────

def get_objectives(proposal_id: str) -> list:
    try:
        return db().table("objectives").select("*")\
                   .eq("proposal_id", proposal_id)\
                   .order("sort_order").order("objective_number").execute().data or []
    except Exception:
        return []

def upsert_objective(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if data.get("objective_id"):
            oid = data.pop("objective_id")
            db().table("objectives").update(data).eq("objective_id", oid).execute()
            return True, oid
        r = db().table("objectives").insert(data).execute()
        return True, r.data[0]["objective_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_objective(oid: int) -> bool:
    try:
        db().table("objectives").delete().eq("objective_id", oid).execute()
        return True
    except Exception:
        return False


# ── Work Packages ────────────────────────────────────────────────────────────

def get_work_packages(proposal_id: str) -> list:
    try:
        return db().table("work_packages").select("*")\
                   .eq("proposal_id", proposal_id)\
                   .order("sort_order").order("wp_number").execute().data or []
    except Exception:
        return []

def upsert_work_package(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if data.get("wp_id"):
            wid = data.pop("wp_id")
            db().table("work_packages").update(data).eq("wp_id", wid).execute()
            return True, wid
        r = db().table("work_packages").insert(data).execute()
        return True, r.data[0]["wp_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_work_package(wp_id: int) -> bool:
    try:
        db().table("work_packages").delete().eq("wp_id", wp_id).execute()
        return True
    except Exception:
        return False

def set_wp_objectives(wp_id: int, objective_ids: list) -> bool:
    try:
        db().table("objective_work_packages").delete().eq("wp_id", wp_id).execute()
        if objective_ids:
            db().table("objective_work_packages").insert(
                [{"wp_id": wp_id, "objective_id": o} for o in objective_ids]
            ).execute()
        return True
    except Exception:
        return False

def get_wp_objectives(wp_id: int) -> list:
    try:
        r = db().table("objective_work_packages").select("objective_id")\
                .eq("wp_id", wp_id).execute()
        return [row["objective_id"] for row in (r.data or [])]
    except Exception:
        return []

def set_wp_partners(wp_id: int, partners: list) -> bool:
    try:
        db().table("work_package_partners").delete().eq("wp_id", wp_id).execute()
        if partners:
            db().table("work_package_partners").insert(
                [{"wp_id": wp_id, **p} for p in partners]
            ).execute()
        return True
    except Exception:
        return False

def get_wp_partners(wp_id: int) -> list:
    try:
        return db().table("work_package_partners").select(
            "*, partners(id,full_name,short_name)"
        ).eq("wp_id", wp_id).execute().data or []
    except Exception:
        return []


# ── Tasks ────────────────────────────────────────────────────────────────────

def get_tasks(proposal_id: str, wp_id: int = None) -> list:
    try:
        q = db().table("tasks_project").select("*")\
                .eq("proposal_id", proposal_id)
        if wp_id:
            q = q.eq("wp_id", wp_id)
        return q.order("task_number").execute().data or []
    except Exception:
        return []

def upsert_task(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if not data.get("task_id"):
            data.setdefault("planned_start_month", data.get("start_month"))
            data.setdefault("planned_end_month",   data.get("end_month"))
        if data.get("task_id"):
            tid = data.pop("task_id")
            db().table("tasks_project").update(data).eq("task_id", tid).execute()
            return True, tid
        r = db().table("tasks_project").insert(data).execute()
        return True, r.data[0]["task_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_task(task_id: int) -> bool:
    try:
        db().table("tasks_project").delete().eq("task_id", task_id).execute()
        return True
    except Exception:
        return False

def set_task_partners(task_id: int, partners: list) -> bool:
    try:
        db().table("task_partners").delete().eq("task_id", task_id).execute()
        if partners:
            db().table("task_partners").insert(
                [{"task_id": task_id, **p} for p in partners]
            ).execute()
        return True
    except Exception:
        return False

def get_task_partners(task_id: int) -> list:
    try:
        return db().table("task_partners").select(
            "*, partners(id,full_name,short_name)"
        ).eq("task_id", task_id).execute().data or []
    except Exception:
        return []


# ── Deliverables ─────────────────────────────────────────────────────────────

def get_deliverables(proposal_id: str, wp_id: int = None, task_id: int = None) -> list:
    try:
        q = db().table("deliverables").select("*")\
                .eq("proposal_id", proposal_id)
        if wp_id:   q = q.eq("wp_id", wp_id)
        if task_id: q = q.eq("task_id", task_id)
        return q.order("delivery_month").order("deliverable_number").execute().data or []
    except Exception:
        return []

def upsert_deliverable(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if not data.get("deliverable_id"):
            data.setdefault("planned_delivery_month", data.get("delivery_month"))
        if data.get("deliverable_id"):
            did = data.pop("deliverable_id")
            db().table("deliverables").update(data).eq("deliverable_id", did).execute()
            return True, did
        r = db().table("deliverables").insert(data).execute()
        return True, r.data[0]["deliverable_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_deliverable(did: int) -> bool:
    try:
        db().table("deliverables").delete().eq("deliverable_id", did).execute()
        return True
    except Exception:
        return False


# ── Milestones ───────────────────────────────────────────────────────────────

def get_milestones(proposal_id: str, wp_id: int = None) -> list:
    try:
        q = db().table("milestones").select("*")\
                .eq("proposal_id", proposal_id)
        if wp_id: q = q.eq("wp_id", wp_id)
        return q.order("due_month").order("milestone_number").execute().data or []
    except Exception:
        return []

def upsert_milestone(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if not data.get("milestone_id"):
            data.setdefault("planned_due_month", data.get("due_month"))
        if data.get("milestone_id"):
            mid = data.pop("milestone_id")
            db().table("milestones").update(data).eq("milestone_id", mid).execute()
            return True, mid
        r = db().table("milestones").insert(data).execute()
        return True, r.data[0]["milestone_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_milestone(mid: int) -> bool:
    try:
        db().table("milestones").delete().eq("milestone_id", mid).execute()
        return True
    except Exception:
        return False


# ── KPIs ─────────────────────────────────────────────────────────────────────

def get_kpis(proposal_id: str, kpi_type: str = None) -> list:
    try:
        q = db().table("kpis").select("*").eq("proposal_id", proposal_id)
        if kpi_type: q = q.eq("kpi_type", kpi_type)
        return q.order("sort_order").order("kpi_number").execute().data or []
    except Exception:
        return []

def upsert_kpi(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if data.get("kpi_id"):
            kid = data.pop("kpi_id")
            db().table("kpis").update(data).eq("kpi_id", kid).execute()
            return True, kid
        r = db().table("kpis").insert(data).execute()
        return True, r.data[0]["kpi_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_kpi(kid: int) -> bool:
    try:
        db().table("kpis").delete().eq("kpi_id", kid).execute()
        return True
    except Exception:
        return False

def set_kpi_links(kpi_id: int, entity_type: str, entity_ids: list) -> bool:
    TABLE_MAP = {
        "objective":   ("kpi_objectives",    "objective_id"),
        "work_package":("kpi_work_packages",  "wp_id"),
        "task":        ("kpi_tasks",          "task_id"),
        "deliverable": ("kpi_deliverables",   "deliverable_id"),
        "milestone":   ("kpi_milestones",     "milestone_id"),
    }
    if entity_type not in TABLE_MAP:
        return False
    table, fk = TABLE_MAP[entity_type]
    try:
        db().table(table).delete().eq("kpi_id", kpi_id).execute()
        if entity_ids:
            db().table(table).insert(
                [{"kpi_id": kpi_id, fk: eid} for eid in entity_ids]
            ).execute()
        return True
    except Exception:
        return False

def get_kpi_links(kpi_id: int) -> dict:
    TABLE_MAP = {
        "objectives":   ("kpi_objectives",    "objective_id"),
        "work_packages":("kpi_work_packages",  "wp_id"),
        "tasks":        ("kpi_tasks",          "task_id"),
        "deliverables": ("kpi_deliverables",   "deliverable_id"),
        "milestones":   ("kpi_milestones",     "milestone_id"),
    }
    result = {}
    for key, (table, fk) in TABLE_MAP.items():
        try:
            r = db().table(table).select(fk).eq("kpi_id", kpi_id).execute()
            result[key] = [row[fk] for row in (r.data or [])]
        except Exception:
            result[key] = []
    return result


# ── Budget ───────────────────────────────────────────────────────────────────

def get_budget_entries(proposal_id: str, wp_id: int = None,
                        partner_id: int = None) -> list:
    try:
        q = db().table("budget_entries").select(
            "*, work_packages(wp_number,wp_title), partners(full_name,short_name)"
        ).eq("proposal_id", proposal_id)
        if wp_id:      q = q.eq("wp_id", wp_id)
        if partner_id: q = q.eq("partner_id", partner_id)
        return q.execute().data or []
    except Exception:
        return []

def upsert_budget_entry(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        r = db().table("budget_entries").upsert(
            data, on_conflict="proposal_id,wp_id,partner_id,cost_category"
        ).execute()
        return True, r.data[0]["budget_entry_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def get_personnel_costs(budget_entry_id: int) -> list:
    try:
        return db().table("personnel_costs").select("*")\
                   .eq("budget_entry_id", budget_entry_id).execute().data or []
    except Exception:
        return []

def upsert_personnel_cost(data: dict) -> tuple:
    try:
        if data.get("personnel_cost_id"):
            pid = data.pop("personnel_cost_id")
            db().table("personnel_costs").update(data).eq("personnel_cost_id", pid).execute()
            return True, pid
        r = db().table("personnel_costs").insert(data).execute()
        return True, r.data[0]["personnel_cost_id"] if r.data else None
    except Exception as e:
        return False, str(e)

def delete_personnel_cost(pid: int) -> bool:
    try:
        db().table("personnel_costs").delete().eq("personnel_cost_id", pid).execute()
        return True
    except Exception:
        return False

def get_overhead_settings(proposal_id: str) -> dict:
    try:
        r = db().table("overhead_settings").select("*")\
                .eq("proposal_id", proposal_id).execute()
        if r.data:
            return r.data[0]
        # Create default if missing
        default = {"proposal_id": proposal_id, "overhead_percentage": 25.0}
        db().table("overhead_settings").insert(default).execute()
        return default
    except Exception:
        return {"overhead_percentage": 25.0}

def upsert_overhead_settings(data: dict) -> bool:
    try:
        data["updated_at"] = _now()
        db().table("overhead_settings").upsert(
            data, on_conflict="proposal_id"
        ).execute()
        return True
    except Exception:
        return False

def get_budget_summary(proposal_id: str) -> dict:
    """Returns aggregated budget per WP, per partner, per category."""
    entries = get_budget_entries(proposal_id)
    if not entries:
        return {"by_wp": {}, "by_partner": {}, "by_category": {}, "total": 0.0}

    by_wp       = {}
    by_partner  = {}
    by_category = {}
    total       = 0.0

    for e in entries:
        amt    = float(e.get("planned_amount",0) or 0)
        wp_num = e.get("work_packages",{}).get("wp_number","?") if e.get("work_packages") else e.get("wp_id","?")
        pname  = e.get("partners",{}).get("full_name","?") if e.get("partners") else e.get("partner_id","?")
        cat    = e.get("cost_category","?")

        by_wp[wp_num]         = by_wp.get(wp_num, 0)       + amt
        by_partner[pname]     = by_partner.get(pname, 0)   + amt
        by_category[cat]      = by_category.get(cat, 0)    + amt
        total                += amt

    return {"by_wp": by_wp, "by_partner": by_partner,
            "by_category": by_category, "total": total}


# ── Gantt data loader ─────────────────────────────────────────────────────────

def get_gantt_data(proposal_id: str) -> dict:
    """Load all time-based data needed to render the Gantt chart."""
    return {
        "work_packages": get_work_packages(proposal_id),
        "tasks":         get_tasks(proposal_id),
        "deliverables":  get_deliverables(proposal_id),
        "milestones":    get_milestones(proposal_id),
    }

def get_full_structure(proposal_id: str) -> dict:
    """Load everything for export, including risks with WP labels resolved."""
    wps  = get_work_packages(proposal_id)
    wp_map = {w["wp_id"]: w.get("wp_number","") for w in wps}
    risks = get_risks(proposal_id)
    # Pre-resolve WP labels onto each risk for export
    for r in risks:
        linked = get_risk_wps(r["risk_id"])
        r["_wp_labels"] = ", ".join(wp_map.get(wid,"") for wid in linked if wid in wp_map)
    return {
        "proposal":      get_proposal(proposal_id),
        "objectives":    get_objectives(proposal_id),
        "work_packages": wps,
        "tasks":         get_tasks(proposal_id),
        "deliverables":  get_deliverables(proposal_id),
        "milestones":    get_milestones(proposal_id),
        "kpis_short":    get_kpis(proposal_id, "short_term"),
        "kpis_long":     get_kpis(proposal_id, "long_term"),
        "risks":         risks,
    }


# ── Risk Management ───────────────────────────────────────────────────────────

def _compute_risk_level(likelihood: str, severity: str) -> str:
    """
    Risk matrix:
              | High Sev | Med Sev | Low Sev
    High Lik  | critical |  high   | medium
    Med  Lik  |   high   | medium  |  low
    Low  Lik  |  medium  |   low   |  low
    """
    matrix = {
        ("high",   "high"):   "critical",
        ("high",   "medium"): "high",
        ("high",   "low"):    "medium",
        ("medium", "high"):   "high",
        ("medium", "medium"): "medium",
        ("medium", "low"):    "low",
        ("low",    "high"):   "medium",
        ("low",    "medium"): "low",
        ("low",    "low"):    "low",
    }
    return matrix.get((likelihood.lower(), severity.lower()), "medium")


def get_risks(proposal_id: str) -> list:
    try:
        return db().table("risks").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("sort_order").order("risk_number").execute().data or []
    except Exception:
        return []


def get_risk_wps(risk_id: int) -> list:
    """Returns list of wp_ids linked to a risk."""
    try:
        r = db().table("risk_work_packages").select("wp_id") \
                .eq("risk_id", risk_id).execute()
        return [row["wp_id"] for row in (r.data or [])]
    except Exception:
        return []


def upsert_risk(data: dict) -> tuple:
    try:
        # Auto-compute risk level
        data["risk_level"] = _compute_risk_level(
            data.get("likelihood", "medium"),
            data.get("severity",   "medium"),
        )
        data["updated_at"] = _now()
        if data.get("risk_id"):
            rid = data.pop("risk_id")
            db().table("risks").update(data).eq("risk_id", rid).execute()
            return True, rid
        r = db().table("risks").insert(data).execute()
        return True, r.data[0]["risk_id"] if r.data else None
    except Exception as e:
        return False, str(e)


def delete_risk(risk_id: int) -> bool:
    try:
        db().table("risks").delete().eq("risk_id", risk_id).execute()
        return True
    except Exception:
        return False


def set_risk_wps(risk_id: int, wp_ids: list) -> bool:
    try:
        db().table("risk_work_packages").delete().eq("risk_id", risk_id).execute()
        if wp_ids:
            db().table("risk_work_packages").insert(
                [{"risk_id": risk_id, "wp_id": wid} for wid in wp_ids]
            ).execute()
        return True
    except Exception:
        return False
