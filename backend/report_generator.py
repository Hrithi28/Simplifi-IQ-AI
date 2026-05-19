"""
report_generator.py — AI-Powered Personalized Audit Report (PDF)
Generates a premium, visually polished multi-page PDF report.
"""

import os
import json
import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.lib import colors

logger = logging.getLogger(__name__)

# ── Color Palette ────────────────────────────────────────────────────────────
DARK_BG      = HexColor("#0A0E1A")
NAVY         = HexColor("#0F1724")
ACCENT_BLUE  = HexColor("#1E6FFF")
ACCENT_CYAN  = HexColor("#00C9FF")
ACCENT_GREEN = HexColor("#00E5A0")
ACCENT_AMBER = HexColor("#FFB547")
ACCENT_RED   = HexColor("#FF4E6A")
LIGHT_GRAY   = HexColor("#8892A4")
MID_GRAY     = HexColor("#3A4255")
OFF_WHITE    = HexColor("#E8EDF5")
PANEL_BG     = HexColor("#131929")
CARD_BG      = HexColor("#1A2035")

def hx(color):
    """Convert ReportLab color to HTML hex string."""
    return "#" + color.hexval()[2:]

WHITE        = HexColor("#FFFFFF")

W, H = A4
PAGE_W = W - 40*mm
LEFT_M = 20*mm
RIGHT_M = 20*mm
TOP_M = 15*mm
BOT_M = 15*mm


# ── Custom Flowables ──────────────────────────────────────────────────────────

class ColorRect(Flowable):
    """Filled rectangle background block."""
    def __init__(self, width, height, color, radius=4):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)


class GradientHeader(Flowable):
    """Full-width header banner with gradient-like layered rects."""
    def __init__(self, width, height, company, tagline, report_date):
        super().__init__()
        self.width = width
        self.height = height
        self.company = company
        self.tagline = tagline
        self.report_date = report_date

    def draw(self):
        c = self.canv
        # Background layers
        c.setFillColor(DARK_BG)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(HexColor("#0D1630"))
        c.rect(self.width * 0.6, 0, self.width * 0.4, self.height, fill=1, stroke=0)

        # Accent stripe
        c.setFillColor(ACCENT_BLUE)
        c.rect(0, self.height - 3, self.width, 3, fill=1, stroke=0)

        # Decorative circles
        c.setFillColor(HexColor("#1E3A8A"))
        c.setFillAlpha(0.3)
        c.circle(self.width * 0.85, self.height * 0.5, 60, fill=1, stroke=0)
        c.circle(self.width * 0.95, self.height * 0.15, 30, fill=1, stroke=0)
        c.setFillAlpha(1)

        # "BUSINESS INTELLIGENCE REPORT" label
        c.setFillColor(ACCENT_CYAN)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(0, self.height - 20, "BUSINESS INTELLIGENCE REPORT  ·  CONFIDENTIAL")

        # Company name
        c.setFillColor(WHITE)
        font_size = 28 if len(self.company) < 20 else 22
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(0, self.height - 55, self.company)

        # Tagline
        if self.tagline:
            c.setFillColor(LIGHT_GRAY)
            c.setFont("Helvetica", 10)
            # Truncate tagline
            tl = self.tagline if len(self.tagline) < 80 else self.tagline[:77] + "..."
            c.drawString(0, self.height - 72, tl)

        # Date badge
        c.setFillColor(ACCENT_BLUE)
        badge_text = f"Generated: {self.report_date}"
        c.roundRect(0, 6, 160, 20, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(8, 11, badge_text)

        # SimplifIQ branding
        c.setFillColor(ACCENT_CYAN)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(self.width, 11, "SimplifIQ™ Intelligence")


class SectionDivider(Flowable):
    """Horizontal rule with section label."""
    def __init__(self, width, label, color=ACCENT_BLUE):
        super().__init__()
        self.width = width
        self.label = label
        self.color = color
        self.height = 18

    def draw(self):
        c = self.canv
        # Accent dot
        c.setFillColor(self.color)
        c.circle(4, 9, 4, fill=1, stroke=0)
        # Label
        c.setFillColor(self.color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(14, 5, self.label.upper())
        # Line
        label_w = len(self.label) * 5.5 + 20
        c.setStrokeColor(MID_GRAY)
        c.setLineWidth(0.5)
        c.line(label_w, 9, self.width, 9)


class ScoreBar(Flowable):
    """Horizontal score/progress bar."""
    def __init__(self, width, label, value, max_val=100, color=ACCENT_GREEN):
        super().__init__()
        self.width = width
        self.label = label
        self.value = value
        self.max_val = max_val
        self.color = color
        self.height = 22

    def draw(self):
        c = self.canv
        bar_start = 130
        bar_w = self.width - bar_start - 40
        fill_w = bar_w * (self.value / self.max_val)

        c.setFillColor(OFF_WHITE)
        c.setFont("Helvetica", 9)
        c.drawString(0, 6, self.label)

        # Background track
        c.setFillColor(MID_GRAY)
        c.roundRect(bar_start, 4, bar_w, 12, 6, fill=1, stroke=0)

        # Fill
        c.setFillColor(self.color)
        c.roundRect(bar_start, 4, max(fill_w, 10), 12, 6, fill=1, stroke=0)

        # Value
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        pct = f"{int(self.value)}%"
        c.drawRightString(self.width, 6, pct)


class TagCloud(Flowable):
    """Renders a row of pill-shaped tags."""
    def __init__(self, width, tags, color=ACCENT_BLUE):
        super().__init__()
        self.width = width
        self.tags = tags[:8]
        self.color = color
        self.height = 28

    def draw(self):
        c = self.canv
        x = 0
        for tag in self.tags:
            tag_w = len(tag) * 6 + 16
            if x + tag_w > self.width:
                break
            c.setFillColor(HexColor("#1A2F5E"))
            c.roundRect(x, 4, tag_w, 18, 9, fill=1, stroke=0)
            c.setStrokeColor(self.color)
            c.setLineWidth(0.5)
            c.roundRect(x, 4, tag_w, 18, 9, fill=0, stroke=1)
            c.setFillColor(self.color)
            c.setFont("Helvetica", 8)
            c.drawString(x + 8, 9, tag)
            x += tag_w + 6


class ImpactBadge(Flowable):
    """Impact level badge (High/Medium/Low)."""
    def __init__(self, impact):
        super().__init__()
        self.impact = impact
        self.width = 55
        self.height = 16

    def draw(self):
        c = self.canv
        colors_map = {
            "High": (HexColor("#0F3320"), ACCENT_GREEN),
            "Medium": (HexColor("#332A0A"), ACCENT_AMBER),
            "Low": (HexColor("#1A2035"), LIGHT_GRAY),
        }
        bg, fg = colors_map.get(self.impact, (CARD_BG, LIGHT_GRAY))
        c.setFillColor(bg)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(self.width / 2, 4, self.impact.upper() + " IMPACT")


# ── Style Helpers ──────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    def ps(name, parent_name='Normal', **kwargs):
        parent = base.get(parent_name, base['Normal'])
        return ParagraphStyle(name=name, parent=parent, **kwargs)

    styles['body'] = ps('body', fontSize=9, textColor=OFF_WHITE, leading=14,
                         fontName='Helvetica', alignment=TA_JUSTIFY)
    styles['body_small'] = ps('body_small', fontSize=8, textColor=LIGHT_GRAY, leading=12,
                               fontName='Helvetica')
    styles['section_title'] = ps('section_title', fontSize=13, textColor=WHITE,
                                  fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=6)
    styles['card_title'] = ps('card_title', fontSize=10, textColor=ACCENT_CYAN,
                               fontName='Helvetica-Bold', spaceAfter=4)
    styles['card_body'] = ps('card_body', fontSize=8.5, textColor=OFF_WHITE,
                              fontName='Helvetica', leading=13, alignment=TA_JUSTIFY)
    styles['kv_key'] = ps('kv_key', fontSize=8, textColor=LIGHT_GRAY,
                           fontName='Helvetica-Bold')
    styles['kv_val'] = ps('kv_val', fontSize=9, textColor=OFF_WHITE,
                           fontName='Helvetica')
    styles['insight'] = ps('insight', fontSize=8.5, textColor=OFF_WHITE,
                            fontName='Helvetica', leading=13,
                            leftIndent=12, bulletIndent=0)
    styles['center_label'] = ps('center_label', fontSize=8, textColor=LIGHT_GRAY,
                                 fontName='Helvetica', alignment=TA_CENTER)
    styles['highlight'] = ps('highlight', fontSize=9, textColor=ACCENT_GREEN,
                              fontName='Helvetica-Bold')
    styles['exec_summary'] = ps('exec_summary', fontSize=9.5, textColor=OFF_WHITE,
                                 fontName='Helvetica', leading=16, alignment=TA_JUSTIFY,
                                 borderPad=8)
    return styles


def card_table(content_rows, bg=CARD_BG, border_color=MID_GRAY):
    """Wrap content in a styled card table."""
    t = Table([[content_rows]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('ROUNDEDCORNERS', [6]),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t


# ── Page Template ─────────────────────────────────────────────────────────────

def make_canvas_factory(company_name, total_pages_holder):
    """Returns an onPage callback for headers/footers."""
    def on_page(canv, doc):
        canv.saveState()
        # Footer bar
        canv.setFillColor(DARK_BG)
        canv.rect(0, 0, W, 18*mm, fill=1, stroke=0)
        canv.setStrokeColor(MID_GRAY)
        canv.setLineWidth(0.4)
        canv.line(LEFT_M, 18*mm, W - RIGHT_M, 18*mm)

        canv.setFillColor(LIGHT_GRAY)
        canv.setFont("Helvetica", 7)
        canv.drawString(LEFT_M, 10*mm, f"SimplifIQ Business Intelligence  ·  {company_name}  ·  CONFIDENTIAL")
        canv.drawRightString(W - RIGHT_M, 10*mm, f"Page {doc.page}")

        # Header bar (not on first page — first page has GradientHeader)
        if doc.page > 1:
            canv.setFillColor(DARK_BG)
            canv.rect(0, H - 14*mm, W, 14*mm, fill=1, stroke=0)
            canv.setFillColor(ACCENT_BLUE)
            canv.rect(0, H - 2.5*mm, W, 2.5*mm, fill=1, stroke=0)
            canv.setFillColor(OFF_WHITE)
            canv.setFont("Helvetica-Bold", 8)
            canv.drawString(LEFT_M, H - 10*mm, company_name.upper())
            canv.setFillColor(LIGHT_GRAY)
            canv.setFont("Helvetica", 7)
            canv.drawRightString(W - RIGHT_M, H - 10*mm, "BUSINESS INTELLIGENCE REPORT")

        canv.restoreState()
    return on_page


# ── Report Assembly ────────────────────────────────────────────────────────────

def generate_report(lead: dict, enriched: dict, output_dir: str) -> str:
    """Build and save the PDF report. Returns the file path."""

    company_safe = "".join(c for c in lead['company'] if c.isalnum() or c in " _-").strip()
    fname = f"SimplifIQ_Report_{company_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    out_path = os.path.join(output_dir, fname)

    report_date = datetime.now().strftime("%B %d, %Y")
    styles = make_styles()
    story = []

    company_name = enriched.get("company_name", lead["company"])
    tagline = enriched.get("tagline", "")

    total_holder = [0]
    on_page = make_canvas_factory(company_name, total_holder)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=LEFT_M,
        rightMargin=RIGHT_M,
        topMargin=TOP_M + 5*mm,
        bottomMargin=BOT_M + 18*mm,
        title=f"SimplifIQ Report — {company_name}",
        author="SimplifIQ Intelligence",
        subject="Business Intelligence & AI Opportunity Report",
    )

    # ─── PAGE 1: Hero Header + Overview ──────────────────────────────────────
    story.append(GradientHeader(PAGE_W, 90, company_name, tagline, report_date))
    story.append(Spacer(1, 8*mm))

    # Executive Summary Card
    story.append(SectionDivider(PAGE_W, "Executive Summary", ACCENT_CYAN))
    story.append(Spacer(1, 3*mm))
    exec_text = enriched.get("executive_summary",
        f"{company_name} is a promising business with opportunities for AI-driven growth.")
    exec_para = Paragraph(exec_text, styles['exec_summary'])
    t = Table([[exec_para]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), HexColor("#0D2040")),
        ('BOX', (0,0),(-1,-1), 1, ACCENT_BLUE),
        ('LEFTPADDING', (0,0),(-1,-1), 14),
        ('RIGHTPADDING', (0,0),(-1,-1), 14),
        ('TOPPADDING', (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(t)
    story.append(Spacer(1, 5*mm))

    # Company Profile KPIs
    story.append(SectionDivider(PAGE_W, "Company Profile", ACCENT_BLUE))
    story.append(Spacer(1, 3*mm))

    kpi_data = [
        ["🏢  Company", company_name, "📍  HQ", enriched.get("headquarters", "Unknown")],
        ["🏭  Industry", lead['industry'], "👥  Size", enriched.get("employee_count", lead.get("company_size","Unknown"))],
        ["📅  Founded", enriched.get("founding_year", "Unknown"), "💼  Model", enriched.get("business_model", "Unknown")],
        ["🌐  Website", lead['website'], "📊  Sentiment", enriched.get("sentiment", "Positive")],
    ]
    kpi_table_data = []
    for row in kpi_data:
        kpi_table_data.append([
            Paragraph(f'<font color="#8892A4" size="8"><b>{row[0]}</b></font>', styles['body_small']),
            Paragraph(f'<font color="#E8EDF5" size="9">{row[1]}</font>', styles['body']),
            Paragraph(f'<font color="#8892A4" size="8"><b>{row[2]}</b></font>', styles['body_small']),
            Paragraph(f'<font color="#E8EDF5" size="9">{row[3]}</font>', styles['body']),
        ])

    kpi_t = Table(kpi_table_data, colWidths=[PAGE_W*0.2, PAGE_W*0.3, PAGE_W*0.2, PAGE_W*0.3])
    kpi_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
        ('ROWBACKGROUNDS', (0,0),(-1,-1), [CARD_BG, PANEL_BG]),
        ('BOX', (0,0),(-1,-1), 0.5, MID_GRAY),
        ('INNERGRID', (0,0),(-1,-1), 0.3, MID_GRAY),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('LEFTPADDING', (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 8),
        ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 5*mm))

    # Value Proposition
    vp = enriched.get("value_proposition", "")
    if vp:
        story.append(SectionDivider(PAGE_W, "Value Proposition", ACCENT_GREEN))
        story.append(Spacer(1, 3*mm))
        vp_para = Paragraph(vp, styles['body'])
        t = Table([[vp_para]], colWidths=[PAGE_W])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), HexColor("#0A1F10")),
            ('BOX', (0,0),(-1,-1), 0.5, ACCENT_GREEN),
            ('LEFTPADDING', (0,0),(-1,-1), 14),
            ('RIGHTPADDING', (0,0),(-1,-1), 14),
            ('TOPPADDING', (0,0),(-1,-1), 10),
            ('BOTTOMPADDING', (0,0),(-1,-1), 10),
            ('ROUNDEDCORNERS', [4]),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))

    # ─── PAGE 2: Core Services + Market Analysis ──────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 5*mm))

    # Core Services
    story.append(SectionDivider(PAGE_W, "Core Services & Offerings", ACCENT_BLUE))
    story.append(Spacer(1, 3*mm))
    services = enriched.get("core_services", [])
    if services:
        svc_items = []
        for i, svc in enumerate(services[:6]):
            colors_cycle = [ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN, ACCENT_AMBER]
            dot_color = colors_cycle[i % len(colors_cycle)]
            svc_items.append([
                Paragraph(
                    f'<font color="{hx(dot_color)}" size="14">●</font>  '
                    f'<font color="#E8EDF5" size="9"><b>{svc}</b></font>',
                    styles['body']
                )
            ])
        svc_t = Table(svc_items, colWidths=[PAGE_W / 2] * 2 if len(services) > 1 else [PAGE_W])
        # Reformat as 2-column
        rows_2col = []
        for i in range(0, len(services), 2):
            left = Paragraph(
                f'<font color="{hx(ACCENT_BLUE)}" size="12">◆</font>  '
                f'<font color="#E8EDF5" size="9"><b>{services[i]}</b></font>',
                styles['body']
            )
            if i + 1 < len(services):
                right = Paragraph(
                    f'<font color="{hx(ACCENT_CYAN)}" size="12">◆</font>  '
                    f'<font color="#E8EDF5" size="9"><b>{services[i+1]}</b></font>',
                    styles['body']
                )
            else:
                right = Paragraph("", styles['body'])
            rows_2col.append([left, right])
        svc_grid = Table(rows_2col, colWidths=[PAGE_W*0.5, PAGE_W*0.5])
        svc_grid.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
            ('BOX', (0,0),(-1,-1), 0.5, MID_GRAY),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#252D40")),
            ('TOPPADDING', (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 14),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(svc_grid)
    story.append(Spacer(1, 5*mm))

    # Target Market + Competitive Landscape
    story.append(SectionDivider(PAGE_W, "Market Analysis", ACCENT_AMBER))
    story.append(Spacer(1, 3*mm))

    market = enriched.get("target_market", "")
    comp = enriched.get("competitive_landscape", "")
    market_rows = []
    if market:
        market_rows.append([
            Paragraph('<b><font color="#FFB547">Target Market</font></b>', styles['card_title']),
            Paragraph(market, styles['card_body']),
        ])
    if comp:
        market_rows.append([
            Paragraph('<b><font color="#FFB547">Competitive Position</font></b>', styles['card_title']),
            Paragraph(comp, styles['card_body']),
        ])
    if market_rows:
        market_t = Table(market_rows, colWidths=[PAGE_W*0.25, PAGE_W*0.75])
        market_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
            ('BOX', (0,0),(-1,-1), 0.5, ACCENT_AMBER),
            ('INNERGRID', (0,0),(-1,-1), 0.3, MID_GRAY),
            ('TOPPADDING', (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 12),
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ]))
        story.append(market_t)
    story.append(Spacer(1, 5*mm))

    # Industry Trends
    trends = enriched.get("industry_trends", [])
    if trends:
        story.append(SectionDivider(PAGE_W, "Industry Trends", ACCENT_CYAN))
        story.append(Spacer(1, 3*mm))
        trend_items = []
        for i, trend in enumerate(trends[:5]):
            num = Paragraph(f'<font color="{hx(ACCENT_CYAN)}" size="16"><b>0{i+1}</b></font>', styles['body'])
            txt = Paragraph(f'<b><font color="#E8EDF5" size="9">{trend}</font></b>', styles['body'])
            trend_items.append([num, txt])
        trend_t = Table(trend_items, colWidths=[PAGE_W*0.1, PAGE_W*0.9])
        trend_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), PANEL_BG),
            ('BOX', (0,0),(-1,-1), 0.5, MID_GRAY),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#1E2840")),
            ('TOPPADDING', (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 12),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(trend_t)
    story.append(Spacer(1, 5*mm))

    # Technology Stack
    tech = enriched.get("technology_stack_hints", [])
    if tech:
        story.append(SectionDivider(PAGE_W, "Technology Signals", ACCENT_GREEN))
        story.append(Spacer(1, 3*mm))
        story.append(TagCloud(PAGE_W, tech, ACCENT_GREEN))
    story.append(Spacer(1, 5*mm))

    # ─── PAGE 3: AI Opportunities + Insights ──────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 5*mm))

    # Digital Maturity Score
    story.append(SectionDivider(PAGE_W, "Digital Maturity Assessment", ACCENT_BLUE))
    story.append(Spacer(1, 3*mm))
    
    digital = enriched.get("digital_maturity", "Medium")
    dm_level = 65 if "High" in digital else (40 if "Medium" in digital else 20)
    dm_color = ACCENT_GREEN if dm_level > 60 else (ACCENT_AMBER if dm_level > 30 else ACCENT_RED)

    dm_rows = [
        [ScoreBar(PAGE_W*0.85, "Digital Maturity", dm_level, color=dm_color)],
        [ScoreBar(PAGE_W*0.85, "Automation Readiness", min(dm_level + 15, 95), color=ACCENT_CYAN)],
        [ScoreBar(PAGE_W*0.85, "AI Adoption Potential", min(dm_level + 25, 98), color=ACCENT_BLUE)],
        [ScoreBar(PAGE_W*0.85, "Data Infrastructure", dm_level - 10 if dm_level > 30 else 20, color=ACCENT_AMBER)],
    ]
    dm_t = Table(dm_rows, colWidths=[PAGE_W])
    dm_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
        ('BOX', (0,0),(-1,-1), 0.5, MID_GRAY),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('LEFTPADDING', (0,0),(-1,-1), 14),
        ('RIGHTPADDING', (0,0),(-1,-1), 14),
    ]))
    story.append(dm_t)
    dm_note = digital.split("—")[-1].strip() if "—" in digital else digital
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f'<i><font color="#8892A4" size="8">{dm_note}</font></i>', styles['body_small']))
    story.append(Spacer(1, 5*mm))

    # Recommended AI Solutions
    solutions = enriched.get("recommended_ai_solutions", [])
    if solutions:
        story.append(SectionDivider(PAGE_W, "Recommended AI Solutions", ACCENT_CYAN))
        story.append(Spacer(1, 3*mm))

        for sol in solutions[:4]:
            title_txt = sol.get("title", "AI Solution")
            rationale = sol.get("rationale", "")
            impact = sol.get("impact", "Medium")
            impact_color = ACCENT_GREEN if impact == "High" else (ACCENT_AMBER if impact == "Medium" else LIGHT_GRAY)
            impact_bg = HexColor("#0F3320") if impact == "High" else (HexColor("#332A0A") if impact == "Medium" else MID_GRAY)

            header_row = [
                Paragraph(f'<b><font color="{hx(ACCENT_CYAN)}" size="10">⚡  {title_txt}</font></b>', styles['card_title']),
                Paragraph(
                    f'<b><font color="{hx(impact_color)}" size="8">  {impact.upper()} IMPACT</font></b>',
                    ParagraphStyle('badge', fontSize=8, textColor=impact_color,
                                   fontName='Helvetica-Bold', alignment=TA_RIGHT)
                ),
            ]
            detail_row = [
                Paragraph(rationale, styles['card_body']),
                Paragraph("", styles['body']),
            ]
            sol_t = Table([header_row, detail_row], colWidths=[PAGE_W*0.75, PAGE_W*0.25])
            sol_t.setStyle(TableStyle([
                ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
                ('BACKGROUND', (0,0),(-1,0), PANEL_BG),
                ('BOX', (0,0),(-1,-1), 0.5, ACCENT_CYAN),
                ('TOPPADDING', (0,0),(-1,-1), 8),
                ('BOTTOMPADDING', (0,0),(-1,-1), 8),
                ('LEFTPADDING', (0,0),(-1,-1), 12),
                ('RIGHTPADDING', (0,0),(-1,-1), 12),
                ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
            ]))
            story.append(sol_t)
            story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 2*mm))

    # Simplification Opportunities
    opps = enriched.get("opportunities_for_simplification", [])
    if opps:
        story.append(SectionDivider(PAGE_W, "Simplification Opportunities", ACCENT_GREEN))
        story.append(Spacer(1, 3*mm))
        opp_rows = []
        for i, opp in enumerate(opps[:5]):
            opp_rows.append([
                Paragraph(
                    f'<font color="{hx(ACCENT_GREEN)}" size="10"><b>→</b></font>',
                    styles['body']
                ),
                Paragraph(f'<font color="#E8EDF5" size="9">{opp}</font>', styles['body']),
            ])
        opp_t = Table(opp_rows, colWidths=[PAGE_W*0.05, PAGE_W*0.95])
        opp_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), HexColor("#0A1F10")),
            ('BOX', (0,0),(-1,-1), 0.5, ACCENT_GREEN),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#1A2F15")),
            ('TOPPADDING', (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LEFTPADDING', (0,0),(-1,-1), 12),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(opp_t)

    story.append(Spacer(1, 5*mm))

    # ─── PAGE 4: Intelligence Insights + Growth Signals ───────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 5*mm))

    # Key Business Insights
    insights = enriched.get("insights", [])
    if insights:
        story.append(SectionDivider(PAGE_W, "Business Intelligence Insights", ACCENT_BLUE))
        story.append(Spacer(1, 3*mm))
        insight_rows = []
        for i, insight in enumerate(insights[:6]):
            num_color = [ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN, ACCENT_AMBER, ACCENT_RED, OFF_WHITE]
            col = num_color[i % len(num_color)]
            insight_rows.append([
                Paragraph(f'<font color="{hx(col)}" size="16"><b>✦</b></font>', styles['body']),
                Paragraph(f'<font color="#E8EDF5" size="8.5">{insight}</font>', styles['card_body']),
            ])
        ins_t = Table(insight_rows, colWidths=[PAGE_W*0.06, PAGE_W*0.94])
        ins_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), CARD_BG),
            ('ROWBACKGROUNDS', (0,0),(-1,-1), [CARD_BG, PANEL_BG]),
            ('BOX', (0,0),(-1,-1), 0.5, MID_GRAY),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#252D40")),
            ('TOPPADDING', (0,0),(-1,-1), 9),
            ('BOTTOMPADDING', (0,0),(-1,-1), 9),
            ('LEFTPADDING', (0,0),(-1,-1), 12),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(ins_t)
    story.append(Spacer(1, 5*mm))

    # Key Challenges
    challenges = enriched.get("key_challenges", [])
    if challenges:
        story.append(SectionDivider(PAGE_W, "Key Challenges Identified", ACCENT_RED))
        story.append(Spacer(1, 3*mm))
        ch_rows = [[
            Paragraph(f'<font color="{hx(ACCENT_RED)}" size="10">⚠</font>', styles['body']),
            Paragraph(f'<font color="#E8EDF5" size="9">{ch}</font>', styles['body']),
        ] for ch in challenges[:4]]
        ch_t = Table(ch_rows, colWidths=[PAGE_W*0.06, PAGE_W*0.94])
        ch_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), HexColor("#1A0D0F")),
            ('BOX', (0,0),(-1,-1), 0.5, ACCENT_RED),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#2D1519")),
            ('TOPPADDING', (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 12),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(ch_t)
    story.append(Spacer(1, 5*mm))

    # Growth Signals
    growth = enriched.get("growth_signals", [])
    if growth:
        story.append(SectionDivider(PAGE_W, "Growth Signals", ACCENT_GREEN))
        story.append(Spacer(1, 3*mm))
        gr_cols = []
        for sig in growth[:4]:
            gr_cols.append(
                Paragraph(
                    f'<font color="{hx(ACCENT_GREEN)}" size="10"><b>↑</b></font>  '
                    f'<font color="#E8EDF5" size="8.5">{sig}</font>',
                    styles['body']
                )
            )
        # 2-column layout
        rows_2 = []
        for i in range(0, len(gr_cols), 2):
            l = gr_cols[i]
            r = gr_cols[i + 1] if i + 1 < len(gr_cols) else Paragraph("", styles['body'])
            rows_2.append([l, r])
        gr_t = Table(rows_2, colWidths=[PAGE_W*0.5, PAGE_W*0.5])
        gr_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), HexColor("#0A1F10")),
            ('BOX', (0,0),(-1,-1), 0.5, ACCENT_GREEN),
            ('INNERGRID', (0,0),(-1,-1), 0.3, HexColor("#1A3020")),
            ('TOPPADDING', (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 14),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        story.append(gr_t)

    story.append(Spacer(1, 5*mm))

    # Confidence Score
    conf = enriched.get("confidence_score", 0.75)
    story.append(SectionDivider(PAGE_W, "Research Confidence", ACCENT_AMBER))
    story.append(Spacer(1, 3*mm))
    story.append(ScoreBar(PAGE_W*0.7, "Data Confidence Score", int(conf * 100), color=ACCENT_AMBER))
    story.append(Spacer(1, 8*mm))

    # ─── Final: Call to Action ────────────────────────────────────────────────
    cta_data = [[
        Paragraph(
            '<b><font color="#FFFFFF" size="13">Ready to Simplify Your Business?</font></b>',
            styles['section_title']
        ),
    ], [
        Paragraph(
            f'This report was prepared exclusively for <b>{lead["name"]}</b> at <b>{company_name}</b>. '
            f'Our team has identified significant opportunities for AI-driven automation and growth. '
            f'We would love to explore these with you in a focused discovery session.',
            styles['card_body']
        ),
    ], [
        Paragraph(
            f'<b><font color="{hx(ACCENT_CYAN)}">→ </font></b>'
            f'<font color="{hx(ACCENT_CYAN)}">Contact us at hello@simplifiq.ai to schedule your free strategy call.</font>',
            styles['body']
        ),
    ]]
    cta_t = Table(cta_data, colWidths=[PAGE_W])
    cta_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), HexColor("#0D2040")),
        ('BOX', (0,0),(-1,-1), 1.5, ACCENT_BLUE),
        ('TOPPADDING', (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('LEFTPADDING', (0,0),(-1,-1), 16),
        ('RIGHTPADDING', (0,0),(-1,-1), 16),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(cta_t)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    logger.info(f"Report saved: {out_path}")
    return out_path
