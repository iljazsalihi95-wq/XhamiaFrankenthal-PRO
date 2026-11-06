"""Financial review based on imported source rows; never silently treat opening balances as income."""
from decimal import Decimal
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def font_setup():
    candidates=[r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if Path(path).exists():
            try:pdfmetrics.registerFont(TTFont("MosqueUnicode",path));return "MosqueUnicode"
            except Exception:pass
    return "Helvetica"

def report(db,year,path):
    from ledger_totals import summary as combined_summary
    s=combined_summary(db,year)
    font=font_setup()
    styles=getSampleStyleSheet()
    for k in ("Normal","Title","Heading2"):styles[k].fontName=font
    doc=SimpleDocTemplate(path,pagesize=A4)
    story=[Paragraph(f"Islamischer Verein Frankenthal e.V. — Raport financiar {year}",styles["Title"]),Spacer(1,16)]
    rows=[["Rubrika","Cash","Bank","Pa klasifikim","Rreshta"]]
    for kind in ("Hyrjet","Daljet"):
        d=s[kind];rows.append([kind,*[f"{d[k]/100:,.2f} €" for k in ("cash","bank","other")],str(d["count"])])
    t=Table(rows,colWidths=[105,90,90,100,65])
    t.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),font),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#174c55")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    story.append(t)
    story.append(Spacer(1,16))
    story.append(Paragraph("Shënim: Ky raport pasqyron regjistrin e importuar dhe regjistrimet lokale. Gjendjet fillestare, transfertat e brendshme dhe rreshtat e shënuar për përjashtim nuk numërohen si hyrje/dalje të reja. Raporti nuk është rakordim bankar dhe nuk konfirmon gjendjen reale të arkës ose bankës.",styles["Normal"]))
    story.append(Paragraph(f"Rreshta të përjashtuar: Hyrjet {s['Hyrjet']['excluded']}, Daljet {s['Daljet']['excluded']}.",styles["Normal"]))
    doc.build(story)
