"""Static layout/theme tables for the TUI, split out of app.py."""

from textual.theme import Theme

TITLES = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "market": "Market Analyst",
    "business": "Business Analyst",
    "technical": "Technical Analyst",
    "recall": "Lessons from Past Decisions",
    "strategist": "Product Strategist",
    "judgment": "Quality Judge",
    "evidence-provenance": "Evidence Sources",
    "debate-scroll": "Advocate vs Skeptic Debate",
    "risk-scroll": "Risk Team",
    "governance": "Portfolio Manager (Governance)",
    "status-log": "Status / Errors",
}

# Runner node names whose live widget differs from the node id.
WIDGET_FOR_NODE = {
    "debate": "debate-scroll",
    "risk": "risk-scroll",
}

# Analyst node ids that have a dedicated panel widget (used to gate updates).
PANELS = {
    "customer_research",
    "product_analytics",
    "market",
    "business",
    "technical",
    "recall",
    "strategist",
}

STATE_ICON = {
    "idle": "·",
    "waiting": "◌",
    "running": "●",
    "done": "✓",
    "failed": "✗",
    "warning": "⚠",
}

# Spinner frames for the "running" state (a rotating filled circle).
SPINNER_FRAMES = "◐◓◑◒"

# Downstream panels that depend on upstream output; they show "waiting" at the
# start of a run until their first event flips them to running.
WAITING_AT_START = {
    "debate-scroll",
    "strategist",
    "judgment",
    "risk-scroll",
    "governance",
}

ANALYST_IDS = {
    "customer_research",
    "product_analytics",
    "market",
    "business",
    "technical",
}

THEME = Theme(
    name="productagents",
    primary="#38bdf8",
    secondary="#a78bfa",
    accent="#fbbf24",
    success="#34d399",
    warning="#fb923c",
    error="#f43f5e",
    surface="#13212e",
    panel="#0c1722",
    background="#08111a",
    dark=True,
    variables={
        "background": "#08111a",
        "ink": "#e6f0f2",
        "muted": "#9fb4c0",
        "idle-border": "#2a3a47",
        # Readable placeholders/labels (overrides Textual's dim default).
        "text-muted": "#9fb4c0",
        # Stage spectrum — each maps to one pipeline stage.
        "stage-evidence": "#5eead4",
        "stage-analysis": "#38bdf8",
        "stage-recall": "#818cf8",
        "stage-debate": "#fbbf24",
        "stage-strategy": "#34d399",
        "stage-judge": "#a78bfa",
        "stage-risk": "#fb7185",
        "stage-governance": "#c084fc",
    },
)
