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

def create_membership_receipt(path, year, member, month, amount):
    """Print a payment confirmation from an already recorded membership month."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from xml.sax.saxutils import escape
    styles=getSampleStyleSheet()
    doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=48,leftMargin=48)
    rows=[
        Paragraph("Islamischer Verein Frankenthal e.V.",styles["Title"]),
        Spacer(1,12),
        Paragraph("Dëftesë anëtarësie / Mitgliedsbeitragsbestätigung",styles["Heading2"]),
        Spacer(1,22)
    ]
    for title,value in (("Anëtari / Mitglied",member),("Viti / Jahr",year),
                        ("Muaji / Monat",month),("Shuma e regjistruar / Erfasster Betrag",amount)):
        rows.append(Paragraph(escape(title)+": <b>"+escape(str(value))+"</b>",styles["Normal"]))
        rows.append(Spacer(1,12))
    rows.append(Spacer(1,25))
    rows.append(Paragraph("Dokument i gjeneruar nga regjistri i anëtarësisë. Verifikoni pagesën me regjistrin zyrtar.",styles["Normal"]))
    rows.append(Spacer(1,25))
    rows.append(Paragraph("Nënshkrimi / Unterschrift: __________________________",styles["Normal"]))
    doc.build(rows)
