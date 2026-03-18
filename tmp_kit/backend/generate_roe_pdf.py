"""
Generate a professional PDF report of ROE & ROCE validation data
for 10 Nifty 50 stocks across different sectors.
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

OUTPUT_PATH = r"C:\Users\kedar\.gemini\antigravity\scratch\financial_portfolio_tracker\backend\ROE_ROCE_Validation_Report.pdf"

# ─── Data ─────────────────────────────────────────────────────────────────────
STOCKS = [
    # name, sector, type, roe23, roe24, roe25, roe3y, roce23, roce24, roce25, roce3y
    ("HDFC Bank",     "Private Bank",   "Bank", 17.0,  9.0,  8.8, 11.6,   None,  None,  None,   None),
    ("SBI",           "PSU Bank",       "Bank", 15.5, 16.2, 15.9, 15.9,   None,  None,  None,   None),
    ("Reliance Inds", "Oil & Gas",      "Mfg",   9.3,  8.8,  8.3,  8.8,    9.3,   9.3,   8.6,    9.1),
    ("TCS",           "IT Services",    "IT",   46.6, 50.7, 51.2, 49.5,   57.6,  62.6,  62.0,   60.7),
    ("Infosys",       "IT Services",    "IT",   32.5, 30.0, 28.2, 30.2,   39.5,  37.1,  36.2,   37.6),
    ("Maruti Suzuki", "Auto",           "Mfg",  11.1, 15.8, 15.1, 14.0,   13.8,  19.7,  19.5,   17.7),
    ("Sun Pharma",    "Pharma",         "Mfg",  15.1, 15.0, 15.1, 15.1,   15.8,  16.5,  18.9,   17.1),
    ("Titan Company", "Consumer",       "Mfg",  27.4, 37.2, 28.7, 31.1,   34.5,  34.9,  37.0,   35.4),
    ("NTPC",          "PSU Energy",     "Mfg",  11.5, 12.9, 12.7, 12.4,    9.8,  10.4,   9.8,   10.0),
    ("Asian Paints",  "Consumer Mfg",   "Mfg",  25.7, 29.1, 18.9, 24.6,   32.6,  35.3,  24.0,   30.6),
]

def pct(v):
    return f"{v:.1f}%" if v is not None else "—"

# ─── Document Setup ─────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=landscape(A4),
    rightMargin=1.5*cm, leftMargin=1.5*cm,
    topMargin=1.5*cm, bottomMargin=1.5*cm
)

styles = getSampleStyleSheet()
BRAND_DARK  = colors.HexColor("#1a2e4a")
BRAND_BLUE  = colors.HexColor("#2563eb")
BRAND_LIGHT = colors.HexColor("#eff6ff")
HEADER_BG   = colors.HexColor("#1e3a5f")
ROW_ALT     = colors.HexColor("#f0f4fa")
GREEN_GOOD  = colors.HexColor("#d1fae5")
YELLOW_WARN = colors.HexColor("#fef9c3")
BANK_BG     = colors.HexColor("#fce7f3")

title_style = ParagraphStyle("title", parent=styles["Heading1"],
    fontSize=18, textColor=BRAND_DARK, spaceAfter=4, alignment=TA_LEFT)
subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"],
    fontSize=10, textColor=colors.HexColor("#475569"), spaceAfter=2)
note_style = ParagraphStyle("note", parent=styles["Normal"],
    fontSize=8.5, textColor=colors.HexColor("#374151"), leading=13)
footer_style = ParagraphStyle("footer", parent=styles["Normal"],
    fontSize=7.5, textColor=colors.grey, alignment=TA_CENTER)

elements = []

# ─── Header ─────────────────────────────────────────────────────────────────
elements.append(Paragraph("ROE & ROCE Validation Report", title_style))
elements.append(Paragraph(
    "10 Nifty 50 Stocks  ·  FY2023–FY2025  ·  Source: Yahoo Finance (Raw Annual Statements)",
    subtitle_style))
elements.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE, spaceAfter=10))

# ─── Methodology Box ──────────────────────────────────────────────────────
method_data = [
    [Paragraph("<b>ROE</b>  =  Net Income / Stockholders Equity × 100", note_style),
     Paragraph("<b>ROCE</b>  =  EBIT / (Total Assets − Current Liabilities) × 100", note_style),
     Paragraph("<b>3Y Avg</b>  =  Arithmetic mean of FY23, FY24, FY25", note_style),
     Paragraph("<b>Banks</b>  → ROE only; ROCE not applicable (—)", note_style)],
]
method_tbl = Table(method_data, colWidths=[6.8*cm]*4)
method_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), BRAND_LIGHT),
    ("BOX",        (0,0), (-1,-1), 0.5, BRAND_BLUE),
    ("INNERGRID",  (0,0), (-1,-1), 0.3, colors.HexColor("#bfdbfe")),
    ("TOPPADDING", (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
]))
elements.append(method_tbl)
elements.append(Spacer(1, 14))

# ─── Main Table ──────────────────────────────────────────────────────────────
col_labels = [
    "Company", "Sector", "Type",
    "ROE\nFY23", "ROE\nFY24", "ROE\nFY25", "ROE\n3Y Avg",
    "ROCE\nFY23", "ROCE\nFY24", "ROCE\nFY25", "ROCE\n3Y Avg"
]

def make_cell(text, bold=False, color=None, align=TA_RIGHT):
    weight = "<b>%s</b>" % text if bold else text
    style = ParagraphStyle("c", parent=styles["Normal"],
        fontSize=9, alignment=align,
        textColor=color or colors.black)
    return Paragraph(weight, style)

header_row = []
for label in col_labels:
    p = ParagraphStyle("hdr", parent=styles["Normal"],
        fontSize=8.5, alignment=TA_CENTER,
        textColor=colors.white, fontName="Helvetica-Bold")
    header_row.append(Paragraph(label, p))

data_rows = [header_row]
for row in STOCKS:
    name, sector, stype, r23, r24, r25, ravg, c23, c24, c25, cavg = row
    is_bank = stype == "Bank"
    r = [
        make_cell(name,   bold=True, align=TA_LEFT),
        make_cell(sector, align=TA_LEFT),
        make_cell(stype,  align=TA_CENTER,
                  color=colors.HexColor("#dc2626") if is_bank else colors.HexColor("#059669")),
        make_cell(pct(r23)),  make_cell(pct(r24)),  make_cell(pct(r25)),
        make_cell(pct(ravg), bold=True,
                  color=colors.HexColor("#1d4ed8")),
        make_cell(pct(c23)),  make_cell(pct(c24)),  make_cell(pct(c25)),
        make_cell(pct(cavg), bold=True,
                  color=colors.HexColor("#059669") if cavg else colors.grey),
    ]
    data_rows.append(r)

col_widths = [4.5*cm, 3.5*cm, 1.6*cm, 2*cm, 2*cm, 2*cm, 2.2*cm, 2*cm, 2*cm, 2*cm, 2.2*cm]
main_tbl = Table(data_rows, colWidths=col_widths, repeatRows=1)

style_cmds = [
    # Header
    ("BACKGROUND",    (0,0), (-1,0), HEADER_BG),
    ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, ROW_ALT]),
    # Grid
    ("BOX",           (0,0), (-1,-1), 0.8, BRAND_DARK),
    ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#d1d5db")),
    # Separator between ROE and ROCE columns
    ("LINEAFTER",     (6,0), (6,-1), 1.2, BRAND_BLUE),
    # Padding
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ("RIGHTPADDING",  (0,0), (-1,-1), 5),
    # Align avg cols
    ("ALIGN",         (6,0), (6,-1), "CENTER"),
    ("ALIGN",         (10,0),(10,-1),"CENTER"),
    # VALIGN
    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
]

# Colour Bank rows
for i, row in enumerate(STOCKS, start=1):
    if row[2] == "Bank":
        style_cmds.append(("BACKGROUND", (7,i), (10,i), BANK_BG))

main_tbl.setStyle(TableStyle(style_cmds))
elements.append(main_tbl)
elements.append(Spacer(1, 14))

# ─── Footnotes ───────────────────────────────────────────────────────────────
notes = [
    "* All figures computed from Yahoo Finance annual income statements and balance sheets — NOT from Yahoo pre-computed ratios.",
    "* HDFC Bank FY2024 equity inflated due to HDFC Ltd. merger (equity nearly doubled mid-year). This depresses the FY24 and FY25 ROE figures.",
    "  Alternative formula using average equity [ NI / ((Eq_start + Eq_end) / 2) ] would bring 3Y avg closer to 14–15%. Pending research team confirmation.",
    "* Report generated: " + datetime.now().strftime("%d-%b-%Y %H:%M IST"),
]
elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
for note in notes:
    elements.append(Paragraph(note, footer_style))
    elements.append(Spacer(1, 2))

# ─── Build PDF ───────────────────────────────────────────────────────────────
doc.build(elements)
print(f"PDF saved to: {OUTPUT_PATH}")
