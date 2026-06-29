"""WCAG + CVD contrast verifier for the ProductAgents design tokens.

Converts OKLCH -> sRGB (so palette intent stays in OKLCH) and computes WCAG 2.1
relative-luminance contrast ratios for every load-bearing token pair, in both
themes AND under protanopia/deuteranopia simulation. The DESIGN.md color tables
are generated from this script's output, so the system never ships an *asserted*
ratio — only a computed one.

Coverage rule (added after the v1 audit): every signal hue is tested against
EVERY background it can sit on (surface, canvas `bg`, and `well`), not just
surface — and each is re-checked under CVD simulation so "readable" means
"readable for color-blind users too", not just trichromats.

Run:  python3 design/contrast.py   (exits non-zero if any pair misses its floor)
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------- color math


def _oklch_to_linear(L: float, C: float, H: float) -> tuple[float, float, float]:
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    cl, cm, cs = l_**3, m_**3, s_**3
    r = 4.0767416621 * cl - 3.3077115913 * cm + 0.2309699292 * cs
    g = -1.2684380046 * cl + 2.6097574011 * cm - 0.3413193965 * cs
    bb = -0.0041960863 * cl - 0.7034186147 * cm + 1.7076147010 * cs
    return r, g, bb


def _gamma(c: float) -> int:
    c = max(0.0, min(1.0, c))
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(max(0.0, min(1.0, c)) * 255)


def oklch_hex(L: float, C: float, H: float) -> str:
    r, g, b = _oklch_to_linear(L, C, H)
    return f"#{_gamma(r):02x}{_gamma(g):02x}{_gamma(b):02x}"


def _hex_linear(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(hx[i : i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return out[0], out[1], out[2]


def _lum(rgb_lin: tuple[float, float, float]) -> float:
    r, g, b = rgb_lin
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def ratio(fg: str, bg: str) -> float:
    return _ratio(_lum(_hex_linear(fg)), _lum(_hex_linear(bg)))


# Protanopia / deuteranopia simulation matrices (Viénot-Brettel-Mollon, linear RGB).
_CVD = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}


def _cvd_lum(hx: str, kind: str) -> float:
    r, g, b = _hex_linear(hx)
    m = _CVD[kind]
    sr = max(0.0, min(1.0, m[0][0] * r + m[0][1] * g + m[0][2] * b))
    sg = max(0.0, min(1.0, m[1][0] * r + m[1][1] * g + m[1][2] * b))
    sb = max(0.0, min(1.0, m[2][0] * r + m[2][1] * g + m[2][2] * b))
    return _lum((sr, sg, sb))


def cvd_ratio(fg: str, bg: str, kind: str) -> float:
    return _ratio(_cvd_lum(fg, kind), _cvd_lum(bg, kind))


# ---------------------------------------------------------------- tokens
#
# Role -> hex, mirroring design/tokens/themes/{dark,light}.css. Hexes are the
# pinned outputs of the Phase-1 OKLCH ramp generator (the palette intent lives
# in OKLCH; oklch_hex() above documents the conversion). The gate checks the
# exact on-screen pairs the theme files produce — change a theme, change here.

DARK = {
    "bg": "#14171c",  # slate-950 canvas
    "panel": "#1b1f26",  # slate-900
    "elevated": "#222831",  # slate-850
    "well": "#14171c",  # recessed (= canvas tone)
    "field": "#14171c",  # input background
    "hairline": "#333a43",  # slate-800 (decorative — not gated)
    "structural": "#686f79",  # slate-600 control outline
    "focus": "#959ff8",  # indigo-400 (= primary)
    "ink": "#e2e6ec",  # slate-100
    "muted": "#8a93a0",  # slate-450
    "on_signal": "#14171c",  # dark label on a 500 fill
    "on_primary": "#ffffff",  # white label on the primary fill
    "primary": "#6267ca",
    "primary_text": "#959ff8",  # indigo 500 / 400
    "signal": "#e0a33e",
    "signal_text": "#f5c68c",  # amber 500 / 300
    "resolved": "#3fb5a6",
    "resolved_text": "#93d0c5",  # teal  500 / 300
    "danger": "#e15f55",
    "danger_text": "#ffa59a",  # red   500 / 300
    "success": "#46a566",
    "success_text": "#96d2a6",  # green 500 / 300
    "info": "#3c94df",
    "info_text": "#90c7fd",  # blue  500 / 300
}

LIGHT = {
    "bg": "#f7f3ec",  # sand-100 warm off-white canvas
    "panel": "#fdfbf7",  # sand-50
    "elevated": "#ffffff",
    "well": "#ede9e2",  # sand-200
    "field": "#ffffff",
    "hairline": "#dedad3",  # sand-300 (decorative — not gated)
    "structural": "#686f79",  # slate-600 control outline
    "focus": "#565cae",  # indigo-600 (= primary)
    "ink": "#1b1f26",  # slate-900
    "muted": "#545b65",  # slate-700
    "on_signal": "#14171c",  # dark label on a 500 fill
    "on_primary": "#ffffff",  # white label on the primary fill
    "primary": "#565cae",
    "primary_text": "#4e5396",  # indigo 600 / 700
    "signal": "#e0a33e",
    "signal_text": "#7e5519",  # amber 500 / 700
    "resolved": "#3fb5a6",
    "resolved_text": "#2e6b61",  # teal  500 / 700
    "danger": "#e15f55",
    "danger_text": "#94423b",  # red   500 / 700
    "success": "#46a566",
    "success_text": "#336d45",  # green 500 / 700
    "info": "#3c94df",
    "info_text": "#2d6292",  # blue  500 / 700
}

# ---------------------------------------------------------------- Phase 2 layer
#
# The semantic layer (semantic.css + themes/*.css) adds surfaces, text levels,
# accent states, feedback sets, and AI-status tokens. Resolved to the same
# pinned primitives and merged into the theme dicts above so the gate checks the
# real on-screen pairs. NOTE: every feedback/AI body-TEXT hue resolves to a 300
# (dark) / 700 (light) signal step already covered by the CVD pass below — so
# these additions introduce no new CVD hue, only new WCAG grounds/states.

DARK.update(
    {
        "bg_tertiary": "#222831",  # slate-850
        "surface_default": "#1b1f26",  # slate-900
        "surface_raised": "#222831",  # slate-850
        "surface_floating": "#222831",
        "surface_sunken": "#14171c",  # slate-950
        "surface_hover": "#333a43",  # slate-800
        "surface_pressed": "#545b65",  # slate-700
        "surface_selected": "#2b2f58",  # indigo-900
        "accent_subtle": "#2b2f58",  # indigo-900
        "text_tertiary": "#7f8791",  # slate-500 (3:1 — large/UI only)
        "accent_hover": "#565cae",  # indigo-600
        "accent_pressed": "#4e5396",  # indigo-700
        "border_default": "#686f79",  # slate-600
        "border_strong": "#8a93a0",  # slate-450
        "fb_success_bg": "#132719",
        "fb_success_text": "#96d2a6",
        "fb_success_icon": "#70bc86",
        "fb_success_border": "#46a566",
        "fb_warning_bg": "#2e1f0a",
        "fb_warning_text": "#f5c68c",
        "fb_warning_icon": "#eab167",
        "fb_warning_border": "#e0a33e",
        "fb_error_bg": "#361815",
        "fb_error_text": "#ffa59a",
        "fb_error_icon": "#f38378",
        "fb_error_border": "#e15f55",
        "fb_info_bg": "#112435",
        "fb_info_text": "#90c7fd",
        "fb_info_icon": "#68aeee",
        "fb_info_border": "#3c94df",
        "ai_done_text": "#93d0c5",
        "ai_failed_text": "#ffa59a",
        "ai_awaiting_human": "#959ff8",
        "ai_log_info": "#90c7fd",
        "ai_log_warn": "#f5c68c",
        "ai_log_error": "#ffa59a",
        "ai_log_critical": "#ffc4bb",
        "ai_log_trace": "#7f8791",
        "ai_log_debug": "#8a93a0",
        "ai_conf_low": "#f38378",
        "ai_conf_med": "#eab167",
        "ai_conf_high": "#6bb9ac",
        "ai_conf_track": "#333a43",
        "analyst_customer": "#68aeee",
        "analyst_analytics": "#6bb9ac",
        "analyst_market": "#eab167",
        "analyst_business": "#b1bbff",
        "analyst_technical": "#a1a9b4",
    }
)

LIGHT.update(
    {
        "bg_tertiary": "#ede9e2",  # sand-200
        "surface_default": "#fdfbf7",  # sand-50
        "surface_raised": "#ffffff",
        "surface_floating": "#ffffff",
        "surface_sunken": "#ede9e2",  # sand-200
        "surface_hover": "#f7f3ec",  # sand-100
        "surface_pressed": "#dedad3",  # sand-300
        "surface_selected": "#dce4ff",  # indigo-100
        "accent_subtle": "#dce4ff",  # indigo-100
        "text_tertiary": "#686f79",  # slate-600 (3:1 — large/UI only)
        "accent_hover": "#4e5396",  # indigo-700
        "accent_pressed": "#3e437a",  # indigo-800
        "border_default": "#686f79",  # slate-600
        "border_strong": "#545b65",  # slate-700
        "fb_success_bg": "#e3fee9",
        "fb_success_text": "#336d45",
        "fb_success_icon": "#3d8855",
        "fb_success_border": "#3d8855",
        "fb_warning_bg": "#fff0d7",
        "fb_warning_text": "#7e5519",
        "fb_warning_icon": "#9f6a17",
        "fb_warning_border": "#9f6a17",
        "fb_error_bg": "#ffeae4",
        "fb_error_text": "#94423b",
        "fb_error_icon": "#ba5048",
        "fb_error_border": "#ba5048",
        "fb_info_bg": "#e0f9ff",
        "fb_info_text": "#2d6292",
        "fb_info_icon": "#357bb8",
        "fb_info_border": "#357bb8",
        "ai_done_text": "#2e6b61",
        "ai_failed_text": "#94423b",
        "ai_awaiting_human": "#565cae",
        "ai_log_info": "#2d6292",
        "ai_log_warn": "#7e5519",
        "ai_log_error": "#94423b",
        "ai_log_critical": "#71352f",
        "ai_log_trace": "#686f79",
        "ai_log_debug": "#545b65",
        "ai_conf_low": "#ba5048",
        "ai_conf_med": "#9f6a17",
        "ai_conf_high": "#36867a",
        "ai_conf_track": "#dedad3",
        "analyst_customer": "#357bb8",
        "analyst_analytics": "#36867a",
        "analyst_market": "#9f6a17",
        "analyst_business": "#565cae",
        "analyst_technical": "#686f79",
    }
)

SIGNAL_TEXT = [
    "signal_text",
    "resolved_text",
    "danger_text",
    "success_text",
    "info_text",
]
SIGNAL_FILL = ["signal", "resolved", "danger", "success", "info"]
TEXT_BGS = ["bg", "panel", "well"]  # the grounds text renders on

# text pairs that must clear the body floor (4.5) or the UI floor (3.0)
PAIRS = [
    ("ink", "bg", 4.5, "primary text on canvas"),
    ("ink", "panel", 4.5, "primary text on panel"),
    ("ink", "elevated", 4.5, "primary text on floating surface"),
    ("ink", "well", 4.5, "primary text in well"),
    ("ink", "field", 4.5, "primary text in input"),
    ("muted", "bg", 4.5, "secondary text on canvas"),
    ("muted", "panel", 4.5, "secondary text on panel"),
    ("muted", "well", 4.5, "metadata / line numbers in well"),
    ("muted", "field", 4.5, "placeholder text in input"),
    ("structural", "bg", 3.0, "control outline on canvas (1.4.11)"),
    ("structural", "panel", 3.0, "control outline on panel (1.4.11)"),
    ("focus", "bg", 3.0, "focus ring on canvas (offset is load-bearing)"),
    ("primary_text", "bg", 4.5, "primary link/text on canvas"),
    ("primary_text", "panel", 4.5, "primary link/text on panel"),
    ("primary_text", "well", 4.5, "primary link/text in well"),
    ("on_primary", "primary", 4.5, "white label on primary fill"),
]
# every signal TEXT step on every ground it can render on:
for s in SIGNAL_TEXT:
    for bgk in TEXT_BGS:
        PAIRS.append((s, bgk, 4.5, f"{s} on {bgk}"))

# on-signal label: a dark ink sits on each 500 fill (chips, dots, badges).
ON_FILL = [("on_signal", s, 4.5, f"on-signal label on {s} fill") for s in SIGNAL_FILL]

# ---- Phase 2 semantic-layer pairs --------------------------------------------
# Primary text on every persistent ground it can sit on (canvas/panel already
# covered above). Hover/pressed are transient and only ever carry PRIMARY text.
INK_GROUNDS = [
    "surface_default",
    "surface_raised",
    "surface_floating",
    "surface_sunken",
    "surface_selected",
    "surface_hover",
    "surface_pressed",
    "bg_tertiary",
    "accent_subtle",
]
MUTED_GROUNDS = [
    "surface_default",
    "surface_raised",
    "surface_floating",
    "surface_sunken",
    "bg_tertiary",
]
# (selected rows carry PRIMARY text + an accent marker, never muted metadata —
#  so muted is not required to clear the indigo-tinted selected ground.)
for g in INK_GROUNDS:
    PAIRS.append(("ink", g, 4.5, f"primary text on {g}"))
for g in MUTED_GROUNDS:
    PAIRS.append(("muted", g, 4.5, f"secondary text on {g}"))

# Tertiary text — large/UI floor (3:1) only; never body copy.
for g in ("bg", "panel", "surface_default", "surface_raised"):
    PAIRS.append(("text_tertiary", g, 3.0, f"tertiary text on {g} (large/UI only)"))

# Accent-as-text/link on its grounds (primary_text covers bg/panel/well above).
for g in ("surface_default", "surface_raised", "surface_selected", "accent_subtle"):
    PAIRS.append(("primary_text", g, 4.5, f"link/accent text on {g}"))

# White label on the accent fill across interaction states (the button label).
for fill in ("primary", "accent_hover", "accent_pressed"):
    PAIRS.append(("on_primary", fill, 4.5, f"label on accent {fill}"))

# Control outlines / gridlines (WCAG 1.4.11, 3:1).
for g in ("bg", "panel", "surface_default"):
    PAIRS.append(("border_default", g, 3.0, f"control outline on {g}"))
    PAIRS.append(("border_strong", g, 3.0, f"strong border on {g}"))

# Feedback: text + icon on their OWN tinted bg; border visible on the canvas.
for kind in ("success", "warning", "error", "info"):
    PAIRS.append((f"fb_{kind}_text", f"fb_{kind}_bg", 4.5, f"{kind} fb text on its bg"))
    PAIRS.append((f"fb_{kind}_icon", f"fb_{kind}_bg", 3.0, f"{kind} fb icon on its bg"))
    PAIRS.append((f"fb_{kind}_border", "bg", 3.0, f"{kind} feedback border on canvas"))

# AI status text in the log well (the text steps; also gated as signal text on
# canvas above). awaiting-human is a marker (3:1), always paired with a label.
for tok in ("ai_done_text", "ai_failed_text"):
    PAIRS.append((tok, "surface_sunken", 4.5, f"{tok} in log/timeline well"))
for g in ("bg", "panel"):
    PAIRS.append(("ai_awaiting_human", g, 3.0, f"awaiting-human marker on {g}"))

# Log levels in the log well. Body levels at 4.5; trace/debug de-emphasized (3:1).
for tok in ("ai_log_info", "ai_log_warn", "ai_log_error", "ai_log_critical"):
    PAIRS.append((tok, "surface_sunken", 4.5, f"{tok} in log well"))
for tok in ("ai_log_trace", "ai_log_debug"):
    PAIRS.append((tok, "surface_sunken", 3.0, f"{tok} in log well (de-emphasized)"))

# Confidence-gauge fills — UI elements (3:1) on track and canvas; the gauge also
# shows the numeric reading, so color is reinforcement.
for tok in ("ai_conf_low", "ai_conf_med", "ai_conf_high"):
    PAIRS.append((tok, "ai_conf_track", 3.0, f"{tok} on gauge track"))
    PAIRS.append((tok, "bg", 3.0, f"{tok} on canvas"))

# Analyst-perspective markers — UI dots (3:1). Color is the WEAKEST channel:
# glyph + label + position carry the meaning (CVD-honest, see notes below).
for tok in (
    "analyst_customer",
    "analyst_analytics",
    "analyst_market",
    "analyst_business",
    "analyst_technical",
):
    PAIRS.append((tok, "bg", 3.0, f"{tok} marker on canvas"))
    PAIRS.append((tok, "panel", 3.0, f"{tok} marker on panel"))


def show(theme, tokens, pairs, label="contrast"):
    print(f"\n=== {theme} — {label} ===")
    fails = 0
    seen = set()
    for fg, bg, need, role in pairs:
        key = (fg, bg, role)
        if key in seen:
            continue
        seen.add(key)
        r = ratio(tokens[fg], tokens[bg])
        ok = "PASS" if r >= need else "FAIL"
        fails += r < need
        print(f"  [{ok}] {r:5.2f}:1 (need {need}) {fg:>13} on {bg:<9} — {role}")
    return fails


def show_cvd(theme, tokens):
    """Signal text must stay >=4.5 on every ground under protan + deutan."""
    print(f"\n=== {theme} — CVD readability (protan + deutan) ===")
    fails = 0
    for s in SIGNAL_TEXT:
        for bgk in TEXT_BGS:
            for kind in ("protan", "deutan"):
                r = cvd_ratio(tokens[s], tokens[bgk], kind)
                fails += r < 4.5
                if r < 4.5:
                    print(f"  [FAIL] {r:5.2f}:1 {s} on {bgk} ({kind})")
    summary = "all signal text >=4.5:1 under both simulations"
    if fails:
        summary = "SOME CVD FAILURES ABOVE"
    print(f"  {summary}")
    # informational: warm/warm pairs are NOT distinguished by color — redundancy is
    # carried by glyph + position (WCAG 1.4.1). Print, do not fail.
    for a, b in [
        ("signal_text", "danger_text"),
        ("signal_text", "success_text"),
        ("resolved_text", "info_text"),
    ]:
        d = cvd_ratio(tokens[a], tokens[b], "deutan")
        print(
            f"  note: {a} vs {b} deutan-luminance {d:.2f}:1 "
            "— NOT color-distinguished; glyph+position required"
        )
    return fails


if __name__ == "__main__":
    print("RESOLVED HEX")
    for name, t in (("DARK", DARK), ("LIGHT", LIGHT)):
        print(f"  {name}: " + "  ".join(f"{k}={v}" for k, v in t.items()))

    fails = 0
    fails += show("DARK", DARK, PAIRS)
    fails += show("DARK", DARK, ON_FILL, "on-signal fills")
    fails += show_cvd("DARK", DARK)
    fails += show("LIGHT", LIGHT, PAIRS)
    fails += show("LIGHT", LIGHT, ON_FILL, "on-signal fills")
    fails += show_cvd("LIGHT", LIGHT)

    print(f"\nTOTAL FAILURES: {fails}")
    raise SystemExit(1 if fails else 0)
