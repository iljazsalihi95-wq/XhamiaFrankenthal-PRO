from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from xml.sax.saxutils import escape

def create_receipt(path, year, fields):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    lines = [Paragraph("Islamischer Verein Frankenthal e.V.", styles["Title"]),
             Paragraph("Zahlungsbestätigung / Vertetim pagese", styles["Heading2"]), Spacer(1, 20)]
    for label, value in zip(("Jahr", "Datum", "Beschreibung", "Zahlungsweg", "Kategorie", "Betrag"),
                            (year, *fields)):
        lines.append(Paragraph(escape(str(label)) + ": " + escape(str(value)), styles["Normal"]))
        lines.append(Spacer(1, 12))
    lines.append(Spacer(1, 28))
    lines.append(Paragraph("Unterschrift: _________________________", styles["Normal"]))
    doc.build(lines)
