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
