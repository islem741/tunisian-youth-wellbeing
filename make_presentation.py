"""Generate the exam presentation as a .pptx file.
Run with:  python make_presentation.py
Output:    presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


# ── Tunisian palette ────────────────────────────────────────────────
TUN_BLUE   = RGBColor(0x00, 0x47, 0x9E)   # Tunisian flag blue
TUN_RED    = RGBColor(0xE7, 0x0D, 0x1E)   # accent (flag red)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF2, 0xF4, 0xF8)
DARK_GREY  = RGBColor(0x33, 0x33, 0x44)
AMBER      = RGBColor(0xF5, 0xA6, 0x23)
GREEN      = RGBColor(0x21, 0x96, 0x53)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

blank_layout = prs.slide_layouts[6]   # completely blank


# ── helpers ─────────────────────────────────────────────────────────

def add_slide():
    return prs.slides.add_slide(blank_layout)


def rect(slide, left, top, width, height, fill_rgb=None, line_rgb=None, line_width_pt=0):
    from pptx.util import Pt as Pt2
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    shape.line.fill.background()
    if fill_rgb:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_rgb
    else:
        shape.fill.background()
    if line_rgb:
        shape.line.color.rgb = line_rgb
        shape.line.width = Pt2(line_width_pt) if line_width_pt else Pt2(1)
    else:
        shape.line.fill.background()
    return shape


def txbox(slide, text, left, top, width, height,
          font_size=18, bold=False, color=DARK_GREY,
          align=PP_ALIGN.LEFT, wrap=True, italic=False):
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    box.word_wrap = wrap
    tf = box.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return box


def header_bar(slide, title, subtitle=None):
    """Blue top bar with white title text."""
    rect(slide, 0, 0, 13.33, 1.15, fill_rgb=TUN_BLUE)
    txbox(slide, title, 0.35, 0.08, 12, 0.6,
          font_size=30, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    if subtitle:
        txbox(slide, subtitle, 0.35, 0.7, 12, 0.4,
              font_size=14, color=RGBColor(0xCC, 0xDD, 0xFF), align=PP_ALIGN.LEFT)


def footer(slide, text="SESAME University · Python Web Programming – Django · 2025-2026"):
    rect(slide, 0, 7.15, 13.33, 0.35, fill_rgb=TUN_BLUE)
    txbox(slide, text, 0.3, 7.17, 12.7, 0.3,
          font_size=10, color=WHITE, align=PP_ALIGN.CENTER)


def bullet_box(slide, items, left, top, width, height,
               font_size=16, bullet="▸", color=DARK_GREY, line_gap=None):
    """Add a text box with bulleted items (list of strings)."""
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    box.word_wrap = True
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        if line_gap:
            from pptx.util import Pt as Pt2
            p.space_before = Pt2(line_gap)
        run = p.add_run()
        run.text = f"{bullet}  {item}"
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
    return box


def pill(slide, text, left, top, width, height,
         bg=TUN_BLUE, fg=WHITE, font_size=14, bold=False):
    r = rect(slide, left, top, width, height, fill_rgb=bg)
    txbox(slide, text, left, top + 0.03, width, height,
          font_size=font_size, bold=bold, color=fg, align=PP_ALIGN.CENTER)
    return r


# ════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ════════════════════════════════════════════════════════════════════
s1 = add_slide()
rect(s1, 0, 0, 13.33, 7.5, fill_rgb=TUN_BLUE)

# Decorative side stripe
rect(s1, 12.5, 0, 0.83, 7.5, fill_rgb=TUN_RED)

# White card
rect(s1, 0.6, 1.2, 11.5, 5.1,
     fill_rgb=WHITE, line_rgb=WHITE)

txbox(s1, "Tunisian Student Early-Warning",
      0.9, 1.5, 11, 0.9,
      font_size=36, bold=True, color=TUN_BLUE, align=PP_ALIGN.CENTER)
txbox(s1, "& Well-Being Platform",
      0.9, 2.35, 11, 0.7,
      font_size=30, bold=True, color=TUN_BLUE, align=PP_ALIGN.CENTER)

# Divider
rect(s1, 3.5, 3.15, 6.3, 0.04, fill_rgb=TUN_RED)

txbox(s1, "SESAME University",
      0.9, 3.3, 11, 0.45,
      font_size=20, color=DARK_GREY, align=PP_ALIGN.CENTER)
txbox(s1, "Python Web Programming – Django",
      0.9, 3.75, 11, 0.4,
      font_size=17, color=DARK_GREY, align=PP_ALIGN.CENTER)
txbox(s1, "Academic Year 2025 – 2026",
      0.9, 4.15, 11, 0.4,
      font_size=17, color=DARK_GREY, align=PP_ALIGN.CENTER)

txbox(s1, "Individual Exam Project",
      0.9, 4.75, 11, 0.4,
      font_size=14, italic=True, color=RGBColor(0x66, 0x77, 0x99),
      align=PP_ALIGN.CENTER)

footer(s1)


# ════════════════════════════════════════════════════════════════════
# SLIDE 2 — Problem Statement
# ════════════════════════════════════════════════════════════════════
s2 = add_slide()
rect(s2, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s2, "Problem Statement")
footer(s2)

cards = [
    (TUN_BLUE,  "👥  Population",
     "Tunisian middle- & high-school students (ages 12–18) across\n"
     "4 partner schools in Tunis, Ariana, Sousse, Bizerte."),
    (TUN_RED,   "⚠️  Problem",
     "Silent disengagement — rising absences, grade drops, unreported\n"
     "distress — often precedes dropout by months.\n"
     "Current workflows rely on informal paper notes."),
    (RGBColor(0x1A, 0x75, 0x1A), "🎯  Decision Makers",
     "Operators (teachers) enter data.\n"
     "Supervisors (counselors) review and intervene.\n"
     "Admins (directors) configure, audit, export."),
    (RGBColor(0x7B, 0x35, 0x9E), "✅  Expected Value",
     "Faster detection of high-risk cases.\n"
     "Auditable intervention adherence.\n"
     "Measurable workflow completion rate."),
]

col_w, col_gap = 3.0, 0.18
start_x = 0.3
for i, (color, title, body) in enumerate(cards):
    cx = start_x + i * (col_w + col_gap)
    rect(s2, cx, 1.3, col_w, 5.65, fill_rgb=WHITE,
         line_rgb=color, line_width_pt=2)
    rect(s2, cx, 1.3, col_w, 0.55, fill_rgb=color)
    txbox(s2, title, cx + 0.1, 1.33, col_w - 0.2, 0.5,
          font_size=13, bold=True, color=WHITE)
    txbox(s2, body, cx + 0.12, 1.98, col_w - 0.24, 4.8,
          font_size=12.5, color=DARK_GREY)


# ════════════════════════════════════════════════════════════════════
# SLIDE 3 — Architecture
# ════════════════════════════════════════════════════════════════════
s3 = add_slide()
rect(s3, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s3, "Architecture", "5-Layer Pipeline · 3 Django Apps")
footer(s3)

layers = [
    (TUN_BLUE,              "① Data Intake",       "Operator form / CSV upload\ncases/views.py · cases/services.py"),
    (RGBColor(0x0B, 0x63, 0xA0), "② SERS Engine",  "Risk scoring · SERSEntry.compute_sers()\nValidation · full_clean()"),
    (RGBColor(0x10, 0x7D, 0x8D), "③ Workflow",     "State machine: INTAKE→…→CLOSED\nCaseEvent audit log (immutable)"),
    (RGBColor(0x1A, 0x7A, 0x58), "④ Dashboard",    "KPI metrics · Supervisor queue\ndashboard/views.py"),
    (RGBColor(0x6B, 0x3E, 0xA8), "⑤ Governance",   "RBAC · Correlation ID middleware\nStructured logs · Threat model"),
]

lx, lw, lh, gap = 1.05, 10.8, 0.82, 0.08
for i, (col, title, desc) in enumerate(layers):
    ty = 1.3 + i * (lh + gap)
    rect(s3, lx, ty, lw, lh, fill_rgb=col)
    txbox(s3, title, lx + 0.15, ty + 0.04, 3.2, lh - 0.08,
          font_size=15, bold=True, color=WHITE)
    txbox(s3, desc, lx + 3.5, ty + 0.04, 7.1, lh - 0.08,
          font_size=12, color=WHITE)

# Django apps row
apps = [("cases/", TUN_BLUE), ("support/", TUN_RED),
        ("dashboard/", RGBColor(0x1A, 0x7A, 0x58))]
txbox(s3, "Django apps:", 1.05, 6.6, 1.8, 0.4,
      font_size=13, bold=True, color=DARK_GREY)
for j, (name, col) in enumerate(apps):
    pill(s3, name, 2.95 + j * 2.3, 6.58, 2.0, 0.42,
         bg=col, font_size=13, bold=True)


# ════════════════════════════════════════════════════════════════════
# SLIDE 4 — SERS Risk Engine
# ════════════════════════════════════════════════════════════════════
s4 = add_slide()
rect(s4, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s4, "SERS Risk Engine", "Student Engagement Risk Score  (0 – 100)")
footer(s4)

# Formula box
rect(s4, 0.4, 1.3, 12.53, 1.55, fill_rgb=WHITE,
     line_rgb=TUN_BLUE, line_width_pt=1.5)
txbox(s4, "SERS  =  (absence_weight × unexcused_absences)"
          "  +  (grade_drop_weight × grade_drop_points)"
          "  +  (behavior_weight × disciplinary_flags)"
          "  +  (wellbeing_weight × (10 − wellbeing_score))       capped at 100",
      0.55, 1.38, 12.1, 1.35,
      font_size=13.5, color=TUN_BLUE, bold=True)

# Component cards
comps = [
    (TUN_BLUE,   "Absences",    "weight = 6\n0–30 days\nunexcused"),
    (TUN_RED,    "Grade Drop",  "weight = 5\n0–20 points\nfrom prev. avg"),
    (AMBER,      "Behaviour",   "weight = 8\n0–10 flags\ndisciplinary"),
    (GREEN,      "Well-being",  "weight = 10\n1–10 scale\n(inverted)"),
]
cw = 2.8
for i, (col, name, detail) in enumerate(comps):
    cx = 0.4 + i * (cw + 0.22)
    rect(s4, cx, 3.05, cw, 1.95, fill_rgb=WHITE,
         line_rgb=col, line_width_pt=2)
    rect(s4, cx, 3.05, cw, 0.52, fill_rgb=col)
    txbox(s4, name, cx + 0.1, 3.08, cw - 0.2, 0.48,
          font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s4, detail, cx + 0.1, 3.65, cw - 0.2, 1.25,
          font_size=12, color=DARK_GREY, align=PP_ALIGN.CENTER)

# Thresholds
thresh = [
    (GREEN,    "LOW",    "SERS < 40"),
    (AMBER,    "MEDIUM", "40 ≤ SERS < 65"),
    (TUN_RED,  "HIGH ⚡", "SERS ≥ 65  → auto-promoted to Assessment"),
]
txbox(s4, "Risk Thresholds (Admin-configurable via SERSPolicy):",
      0.4, 5.2, 12, 0.38, font_size=13, bold=True, color=DARK_GREY)
for i, (col, label, rule) in enumerate(thresh):
    rx = 0.4 + i * 4.3
    rect(s4, rx, 5.65, 4.0, 0.68, fill_rgb=col)
    txbox(s4, f"{label}  —  {rule}", rx + 0.12, 5.68, 3.8, 0.62,
          font_size=12.5, bold=True, color=WHITE)


# ════════════════════════════════════════════════════════════════════
# SLIDE 5 — Scenario 1
# ════════════════════════════════════════════════════════════════════
s5 = add_slide()
rect(s5, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s5, "Scenario 1 — Education Early Warning",
           "Operator uploads data → risk computed → flagged cases surface on Supervisor queue")
footer(s5)

steps = [
    (TUN_BLUE,  "1. Operator\nUploads Data",
     "Form or CSV at /cases/entry/\nValidated row-by-row\nAtomic rollback on bad rows"),
    (RGBColor(0x0B, 0x63, 0xA0), "2. SERS Engine\nComputes Score",
     "SERSEntry.compute_sers()\n4 weighted components\nFull breakdown stored"),
    (TUN_RED,   "3. HIGH Risk?\nAuto-promote",
     "workflow_state → ASSESSMENT\nCaseEvent(INTAKE) logged\nNo manual step needed"),
    (RGBColor(0x1A, 0x7A, 0x58), "4. Supervisor\nReviews Queue",
     "/dashboard/supervisor/\nSorted by SERS score\nExplanation visible"),
]

sw, sh, gap = 2.85, 3.8, 0.25
sy = 1.5
for i, (col, title, body) in enumerate(steps):
    sx = 0.4 + i * (sw + gap)
    rect(s5, sx, sy, sw, sh, fill_rgb=col)
    txbox(s5, title, sx + 0.15, sy + 0.15, sw - 0.3, 0.85,
          font_size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s5, body, sx + 0.15, sy + 1.1, sw - 0.3, sh - 1.2,
          font_size=12, color=WHITE)
    if i < 3:
        txbox(s5, "→", sx + sw + 0.02, sy + 1.6, 0.25, 0.5,
              font_size=22, bold=True, color=TUN_BLUE, align=PP_ALIGN.CENTER)

# Failure injection note
rect(s5, 0.4, 5.55, 12.53, 1.0, fill_rgb=RGBColor(0xFF, 0xF3, 0xCC),
     line_rgb=AMBER, line_width_pt=1.5)
txbox(s5, "⚠  Failure Injection:  Upload CSV with wellbeing_score=11 (out of range 1–10)  "
          "→  ValidationError raised in SERSEntry.clean()  →  entire batch rolled back  "
          "→  error table displayed to Operator  →  zero rows persisted",
      0.6, 5.6, 12.1, 0.9, font_size=11.5, color=RGBColor(0x7A, 0x50, 0x00))


# ════════════════════════════════════════════════════════════════════
# SLIDE 6 — Scenario 2
# ════════════════════════════════════════════════════════════════════
s6 = add_slide()
rect(s6, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s6, "Scenario 2 — Role-Based Access Control",
           "Unauthorized access blocked, logged, and surfaced on Admin dashboard")
footer(s6)

steps6 = [
    (TUN_BLUE,              "Operator A\n(School A)",
     "Submits SERS entry\nfor a student at\nSchool A"),
    (TUN_RED,               "Operator B\n(School B)",
     "Tries GET /cases/{id}/\nfor School A entry\n← wrong school"),
    (RGBColor(0xCC, 0x33, 0x33), "HTTP 403\nForbidden",
     "PermissionDenied raised\nin case_detail()\nlines 87–95"),
    (RGBColor(0x6B, 0x3E, 0xA8), "Audit Event\nLogged",
     "CaseEvent(action=\nSECURITY) written\nImmutable trail"),
    (RGBColor(0x1A, 0x7A, 0x58), "Admin KPI\nDashboard",
     "Security event count\nincremented\nVisible to Admin"),
]
sw, sh, gap = 2.3, 3.6, 0.2
sy = 1.5
for i, (col, title, body) in enumerate(steps6):
    sx = 0.35 + i * (sw + gap)
    rect(s6, sx, sy, sw, sh, fill_rgb=col)
    txbox(s6, title, sx + 0.12, sy + 0.15, sw - 0.24, 0.85,
          font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s6, body, sx + 0.12, sy + 1.1, sw - 0.24, sh - 1.2,
          font_size=11.5, color=WHITE, align=PP_ALIGN.CENTER)
    if i < 4:
        txbox(s6, "→", sx + sw + 0.01, sy + 1.6, 0.22, 0.5,
              font_size=20, bold=True, color=TUN_BLUE, align=PP_ALIGN.CENTER)

rect(s6, 0.4, 5.35, 12.53, 1.2, fill_rgb=RGBColor(0xFF, 0xF3, 0xCC),
     line_rgb=AMBER, line_width_pt=1.5)
txbox(s6,
      "⚠  Failure Injection:  Operator B  GET /cases/1/  →  "
      "scope check fails (school mismatch)  →  "
      "CaseEvent(SECURITY) written  →  HTTP 403 returned\n"
      "Test:  test_operator_cannot_access_other_school_case  &  "
      "test_security_event_logged_on_unauthorized_access\n"
      "Guard:  cases/views.py  lines 82–95",
      0.6, 5.4, 12.1, 1.1, font_size=11, color=RGBColor(0x7A, 0x50, 0x00))


# ════════════════════════════════════════════════════════════════════
# SLIDE 7 — State Machine
# ════════════════════════════════════════════════════════════════════
s7 = add_slide()
rect(s7, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s7, "Workflow State Machine",
           "Every transition enforced in SERSEntry.transition_to() · logged as CaseEvent")
footer(s7)

states = [
    ("INTAKE",        1.0,  3.2),
    ("ASSESSMENT",    3.35, 3.2),
    ("INTERVENTION",  5.7,  3.2),
    ("FOLLOW-UP",     8.05, 3.2),
    ("CLOSED",        10.4, 3.2),
]
sw_s, sh_s = 2.05, 0.75
colors_s = [TUN_BLUE, RGBColor(0x0B, 0x63, 0xA0),
            RGBColor(0x10, 0x7D, 0x8D), AMBER, GREEN]

for (label, lx, ly), col in zip(states, colors_s):
    rect(s7, lx, ly, sw_s, sh_s, fill_rgb=col)
    txbox(s7, label, lx, ly + 0.05, sw_s, sh_s - 0.1,
          font_size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Arrows between states
for i in range(4):
    ax = states[i][1] + sw_s + 0.01
    txbox(s7, "→", ax, states[i][2] + 0.12, 0.3, 0.5,
          font_size=20, bold=True, color=DARK_GREY, align=PP_ALIGN.CENTER)

# FOLLOW-UP → INTERVENTION back arrow label
txbox(s7, "↑ back", 6.85, 2.55, 1.5, 0.4,
      font_size=10, italic=True, color=DARK_GREY, align=PP_ALIGN.CENTER)

# Any → CLOSED arrow (diagonal)
txbox(s7, "Any state → CLOSED (terminal)  ·  CLOSED has no outbound transitions",
      1.0, 4.2, 11.0, 0.42, font_size=12, italic=True, color=DARK_GREY)

# Transition table
headers = ["From", "Allowed transitions"]
rows_t = [
    ("INTAKE",       "ASSESSMENT, CLOSED"),
    ("ASSESSMENT",   "INTERVENTION, CLOSED"),
    ("INTERVENTION", "FOLLOW-UP, CLOSED"),
    ("FOLLOW-UP",    "INTERVENTION, CLOSED"),
    ("CLOSED",       "— (terminal)"),
]
rect(s7, 0.8, 4.8, 11.73, 0.42, fill_rgb=TUN_BLUE)
txbox(s7, "From State", 0.9, 4.83, 2.8, 0.36,
      font_size=12, bold=True, color=WHITE)
txbox(s7, "Allowed Transitions", 3.8, 4.83, 8.5, 0.36,
      font_size=12, bold=True, color=WHITE)

for i, (fr, to) in enumerate(rows_t):
    by = 5.28 + i * 0.36
    bg = WHITE if i % 2 == 0 else RGBColor(0xE8, 0xF0, 0xFE)
    rect(s7, 0.8, by, 11.73, 0.36, fill_rgb=bg)
    txbox(s7, fr, 0.9, by + 0.04, 2.8, 0.3,
          font_size=11, bold=True, color=TUN_BLUE)
    txbox(s7, to, 3.8, by + 0.04, 8.5, 0.3, font_size=11, color=DARK_GREY)


# ════════════════════════════════════════════════════════════════════
# SLIDE 8 — Advanced Tracks
# ════════════════════════════════════════════════════════════════════
s8 = add_slide()
rect(s8, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s8, "Advanced Tracks Implemented",
           "Three tracks selected from the exam specification")
footer(s8)

tracks = [
    (TUN_BLUE, "Track A — Service Layer",
     [
         "cases/services.py separates business logic from views",
         "ingest_sers_csv(): validates, scores, logs every row",
         "Atomic rollback sentinel (_Rollback) — no partial imports",
         "create_followup_reminder() for overdue intervention plans",
         "Unit-tested independently of HTTP layer",
     ]),
    (TUN_RED, "Track B — Security & Privacy",
     [
         "Custom User model with role field + Django Groups",
         "role_required() decorator → HTTP 403 on wrong role",
         "Operators scoped to own school (_scoped_entries)",
         "Cross-school access → CaseEvent(SECURITY) logged",
         "CSRF on every form · synthetic data only",
     ]),
    (RGBColor(0x6B, 0x3E, 0xA8), "Track D — Observability & Reliability",
     [
         "X-Correlation-ID on every request (wellbeing/middleware.py)",
         "Structured log records: level + correlation_id + logger",
         "KPI dashboard: completion rate, validation pass rate,",
         "  security event count, average SERS score",
         "Atomic CSV import — single bad row rolls back entire batch",
     ]),
]

tw = 3.9
for i, (col, title, bullets) in enumerate(tracks):
    tx = 0.35 + i * (tw + 0.22)
    rect(s8, tx, 1.3, tw, 5.65, fill_rgb=WHITE,
         line_rgb=col, line_width_pt=2)
    rect(s8, tx, 1.3, tw, 0.55, fill_rgb=col)
    txbox(s8, title, tx + 0.1, 1.33, tw - 0.2, 0.5,
          font_size=13, bold=True, color=WHITE)
    for j, b in enumerate(bullets):
        txbox(s8, f"▸  {b}", tx + 0.15, 2.0 + j * 0.85, tw - 0.3, 0.75,
              font_size=11.5, color=DARK_GREY)


# ════════════════════════════════════════════════════════════════════
# SLIDE 9 — Failure Injection & Testing
# ════════════════════════════════════════════════════════════════════
s9 = add_slide()
rect(s9, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s9, "Failure Injection & Test Evidence")
footer(s9)

# Left: failure cases
rect(s9, 0.3, 1.3, 6.2, 5.65, fill_rgb=WHITE,
     line_rgb=TUN_BLUE, line_width_pt=1.5)
txbox(s9, "Failure Injection Cases", 0.4, 1.35, 5.9, 0.45,
      font_size=15, bold=True, color=TUN_BLUE)

cases_fi = [
    ("Case 1 — Bad CSV (Scenario 1)",
     "Input: wellbeing_score = 11  (max = 10)\n"
     "Guard: SERSEntry.clean()  →  ValidationError\n"
     "Result: skipped=1, transaction rolled back\n"
     "Test: test_out_of_range_rejected"),
    ("Case 2 — Wrong School (Scenario 2)",
     "Input: Operator B  GET /cases/{id}/ (School A)\n"
     "Guard: case_detail() lines 82–95\n"
     "Result: HTTP 403 + CaseEvent(SECURITY) logged\n"
     "Test: test_operator_cannot_access_other_school_case"),
]
for i, (title, body) in enumerate(cases_fi):
    cy = 1.9 + i * 2.35
    col = TUN_BLUE if i == 0 else TUN_RED
    rect(s9, 0.4, cy, 6.0, 0.4, fill_rgb=col)
    txbox(s9, title, 0.5, cy + 0.04, 5.8, 0.35,
          font_size=12, bold=True, color=WHITE)
    txbox(s9, body, 0.5, cy + 0.5, 5.8, 1.7,
          font_size=11.5, color=DARK_GREY)

# Right: pytest summary
rect(s9, 6.8, 1.3, 6.2, 5.65, fill_rgb=WHITE,
     line_rgb=GREEN, line_width_pt=1.5)
txbox(s9, "pytest — Test Suite Summary", 6.9, 1.35, 5.9, 0.45,
      font_size=15, bold=True, color=GREEN)

rect(s9, 6.9, 1.88, 5.9, 0.4, fill_rgb=TUN_BLUE)
txbox(s9, "Test File                            Tests", 7.0, 1.91, 5.7, 0.35,
      font_size=11, bold=True, color=WHITE)

test_rows = [
    ("test_sers_scoring.py",   "5 — formula, risk classification, validation, auto-promote"),
    ("test_csv_ingestion.py",  "5 — valid upload, bad column, unknown ID, non-numeric, range"),
    ("test_permissions.py",    "5 — 403 on wrong school, SECURITY event, role locks"),
    ("test_workflow.py",       "4 — transitions, illegal move raises, audit log, plan complete"),
]
for i, (fname, desc) in enumerate(test_rows):
    ry = 2.34 + i * 0.72
    bg = WHITE if i % 2 == 0 else RGBColor(0xE8, 0xF8, 0xEE)
    rect(s9, 6.9, ry, 5.9, 0.68, fill_rgb=bg)
    txbox(s9, fname, 7.0, ry + 0.05, 2.4, 0.58,
          font_size=10.5, bold=True, color=TUN_BLUE)
    txbox(s9, desc, 9.5, ry + 0.05, 3.2, 0.58,
          font_size=10, color=DARK_GREY)

rect(s9, 6.9, 5.26, 5.9, 0.6, fill_rgb=GREEN)
txbox(s9, "19 passed   0 failed   0 errors", 6.9, 5.3, 5.9, 0.55,
      font_size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

txbox(s9, "Run:  pytest cases/tests/ -v  --tb=short",
      6.9, 5.95, 5.9, 0.45,
      font_size=11, italic=True, color=DARK_GREY, align=PP_ALIGN.CENTER)


# ════════════════════════════════════════════════════════════════════
# SLIDE 10 — Ethics & Limitations
# ════════════════════════════════════════════════════════════════════
s10 = add_slide()
rect(s10, 0, 0, 13.33, 7.5, fill_rgb=LIGHT_GREY)
header_bar(s10, "Ethics & Limitations")
footer(s10)

ethics = [
    (TUN_BLUE,  "🔒  Synthetic Data Only",
     "All student records are generated by Faker.\n"
     "No real student data has been used or stored.\n"
     "Real deployment requires written consent\n"
     "and a formal data-governance agreement."),
    (AMBER,     "📊  Rule-Based, Not Black-Box",
     "The SERS formula is fully transparent.\n"
     "Every case shows a component breakdown\n"
     "with the exact points contributed by each\n"
     "factor and the configured threshold."),
    (TUN_RED,   "🛡️  Supervisor Override",
     "Every automated classification can be\n"
     "overridden by a Supervisor. The override\n"
     "is stored as an immutable CaseEvent, so\n"
     "the original flag is never silently erased."),
    (GREEN,     "🔍  Scope & Access Limits",
     "Operators are scoped to their school.\n"
     "The tool surfaces cases for human review —\n"
     "it is not a diagnostic or legal authority.\n"
     "All denied actions are audited and logged."),
]

cw_e = 2.9
for i, (col, title, body) in enumerate(ethics):
    ex = 0.4 + i * (cw_e + 0.22)
    rect(s10, ex, 1.3, cw_e, 5.5, fill_rgb=WHITE,
         line_rgb=col, line_width_pt=2)
    rect(s10, ex, 1.3, cw_e, 0.55, fill_rgb=col)
    txbox(s10, title, ex + 0.1, 1.33, cw_e - 0.2, 0.5,
          font_size=12.5, bold=True, color=WHITE)
    txbox(s10, body, ex + 0.1, 2.0, cw_e - 0.2, 4.6,
          font_size=12, color=DARK_GREY)

txbox(s10,
      "See docs/threat_model.md  ·  docs/risk_register.md  ·  docs/failure_injection_evidence.md",
      0.4, 7.0, 12.53, 0.3,
      font_size=10, italic=True, color=RGBColor(0x66, 0x66, 0x88),
      align=PP_ALIGN.CENTER)


# ── Save ────────────────────────────────────────────────────────────
prs.save("presentation.pptx")
print("✓  presentation.pptx created successfully.")
