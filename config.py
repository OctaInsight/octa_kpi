"""Octa KPI & Work Plan Designer — Configuration."""

APP_NAME    = "Objectives & Work Plan Designer"
APP_ICON    = "📊"
APP_VERSION = "1.0.0"

DARK = {
    "bg":      "#0f1421",
    "bg2":     "#1a2235",
    "bg3":     "#232f45",
    "border":  "rgba(255,255,255,0.09)",
    "text":    "#e2e8f0",
    "muted":   "#8899b0",
    "accent":  "#00BCD4",
    "accent2": "#FF6B35",
    "sidebar": "#1B2A4A",
    "success": "#6fcf97",
    "warning": "#f6cc52",
    "danger":  "#fc8181",
}

# WP colours for Gantt chart (cycles through these)
WP_COLORS = [
    "#00BCD4", "#FF6B35", "#6fcf97", "#f6cc52",
    "#9b59b6", "#fc8181", "#3498db", "#e67e22",
    "#1abc9c", "#e74c3c", "#2ecc71", "#8e44ad",
]

BUDGET_CATEGORIES = [
    "personnel",
    "travel",
    "equipment",
    "other_goods_services",
    "subcontracting",
    "third_parties",
    "overhead",
]

BUDGET_LABELS = {
    "personnel":          "Personnel Costs (PM × Monthly Rate)",
    "travel":             "Travel Costs",
    "equipment":          "Equipment & Infrastructure",
    "other_goods_services": "Other Goods & Services",
    "subcontracting":     "Subcontracting",
    "third_parties":      "Fund for Third Parties",
    "overhead":           "Overhead / Indirect Costs (%)",
}

DELIVERABLE_TYPES = [
    "report", "database", "application", "prototype", "policy_brief",
    "training_material", "website", "dataset", "event", "guidelines", "other"
]

DISSEMINATION_LEVELS = ["public", "sensitive", "confidential", "internal"]

TASK_STATUSES        = ["planned", "ongoing", "completed", "delayed", "cancelled"]
DELIVERABLE_STATUSES = ["planned", "in_progress", "submitted", "accepted", "delayed", "cancelled"]
MILESTONE_STATUSES   = ["planned", "achieved", "partially_achieved", "delayed", "not_achieved"]
KPI_STATUSES         = ["planned", "on_track", "achieved", "partially_achieved", "delayed", "not_achieved"]

KPI_UNITS = [
    "number", "percentage", "EUR", "participants", "downloads",
    "events", "reports", "users", "publications", "hours",
    "pages", "organisations", "countries", "other"
]
