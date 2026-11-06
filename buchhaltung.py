"""German bookkeeping workspace using the existing finance ledger."""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QMessageBox, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ledger_totals import exclusion, records, summary
from sheet_source import SHEET

CATEGORIES = {
    "Anëtarësia": "Mitgliedsbeiträge", "Transfer i brendshëm": "Interne Umbuchung",
    "Arka e Xhamisë": "Moscheekasse", "Sadaka / Donacion": "Spenden",
    "Të tjera": "Sonstiges / Zuordnung prüfen", "Sergji - Xhuma": "Freitagssammlung",
    "Sergji": "Sammlung", "Kthim borxhi": "Rückzahlung einer Forderung",
    "Gjendje fillestare": "Anfangsbestand", "Sergji - Kurban Bajram": "Sammlung zum Opferfest",
    "AOK": "AOK / Krankenkasse", "Blerje / Furnizime": "Einkäufe und Bedarf",
    "Rroga e Hoxhës": "Imamvergütung und IT-Betreuung (Barzahlung; getrennte Leistungszuordnung)", "Nebenkosten": "Nebenkosten", "Pastrimi": "Reinigung",
    "Abrechnung / Banka": "Bankabrechnung", "Beratung / Kontabilitet": "Beratung und Buchhaltung",
    "Bajram": "Festveranstaltung", "Steuer / Finanzamt": "Steuern / Finanzamt",
    "Sparkasse": "Sparkasse",
    "Mirëmbajtja e programit": "IT-Betreuung, Softwarewartung, Serververwaltung und technische Dienstleistungen", "Borxh / Forderung": "Offene Forderung / Bankabgang",
    "Transfer i brendshëm – financim rroge": "Interne Umbuchung zur Lohnfinanzierung",
}
EXCLUSIONS = {
    "Gjendje fillestare": "Anfangsbestand",
    "Përjashtuar në burim": "In der Quelle ausgeschlossen",
    "Transfer i brendshëm / për rakordim": "Interne Umbuchung / Abstimmung",
}
DOCUMENT_TYPES = ("Kontoauszug", "Kassenbon", "Rechnung", "Quittung",
                  "Kassenbuch", "Spendenbeleg", "Lohnunterlage", "Sonstiger Beleg")
FORM_LINKS = (
    ("ELSTER · KSt 1 und Anlage Gem", "https://www.elster.de/eportal/formulare-leistungen/alleformulare/kst"),
    ("ELSTER · Amtliche Hilfe 2025", "https://www.portal.elster.de/elsterweb/helpGlobal?themaGlobal=help_kst_2025"),
    ("ELSTER · Anlage EÜR (falls erforderlich)", "https://www.elster.de/eportal/formulare-leistungen/alleformulare/euer"),
    ("ELSTER · Belegnachreichung", "https://www.elster.de/eportal/formulare-leistungen/alleformulare/belegnachreichung"),
)
HEADERS = ("Datum", "Buchungsart", "Zahlungsweg", "Kategorie", "Betrag EUR", "Status",
           "Buchungstext Deutsch", "Originaltext", "Quelle", "Belege")
MAX_DOCUMENT_BYTES = 30 * 1024 * 1024


def money(amount):
    return f"{amount // 100},{amount % 100:02d}" if amount >= 0 else "-" + money(-amount)


def booking_rows(db, year):
    texts = dict(db.execute("SELECT booking, german FROM bookkeeping_text WHERE year=?", (year,)))
    counts = dict(db.execute("SELECT booking, count(*) FROM bookkeeping_document WHERE year=? GROUP BY booking", (year,)))
    for kind, title in (("Hyrjet", "Einnahme"), ("Daljet", "Ausgabe")):
        occurrences = {}
        for row in records(db, year, kind):
            day, original, account, category, amount, _, source_row = row
            identity = json.dumps([kind, day, original, account, amount] if source_row > 0
                                  else [kind, source_row], ensure_ascii=False)
            index = occurrences.get(identity, 0)
            occurrences[identity] = index + 1
            key = hashlib.sha256(f"{identity}|{index}".encode()).hexdigest()
            reason = exclusion(row)
            source = f"{kind}, Zeile {source_row}" if source_row > 0 else f"Lokale Buchung {-source_row}"
            german = CATEGORIES.get(category, "Zuordnung prüfen")
            if category == "Të tjera":
                original_lower = str(original).casefold()
                for terms, label in (
                    (("antares", "antars", "anëtarës"), "Mitgliedsbeiträge"),
                    (("donacion", "sadaka"), "Spenden"),
                    (("sergi", "sergj"), "Sammlung"),
                    (("nebenkosten", "nebenkisten"), "Nebenkosten"),
                    (("rroga", "rrogen", "lohn"), "Imamvergütung und IT-Betreuung (Barzahlung; getrennte Leistungszuordnung)"),
                    (("aok",), "AOK / Krankenkasse"),
                    (("abrechnung",), "Abrechnung"),
                ):
                    if any(term in original_lower for term in terms):
                        german = label
                        break
            default_text = f"{title}: {german}" if "prüfen" not in german else f"{title} laut Finanzregister"
            if kind == "Daljet" and str(account).strip().lower() == "cash" and amount == 165000 and (category == "Rroga e Hoxhës" or "rroga" in str(original).casefold() or "imam" in str(original).casefold()):
                default_text = "Barzahlung aus der Moscheekasse: 1.650,00 EUR; Nettogehalt des Imams 1.398,22 EUR; Zusatzvergütung für IT-Betreuung, Softwarewartung und Serververwaltung 250,00 EUR; Differenz 1,78 EUR zur Abstimmung. Keine Bankbuchung."
            yield key, (day, title, {"cash": "Bar", "bank": "Bank"}.get(str(account).lower(), "Ungeklärt"),
                        german, money(amount),
                        EXCLUSIONS.get(reason, "Berücksichtigt"), texts.get(key, default_text),
                        original, source, counts.get(key, 0))


def excel_safe(value):
    return "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value


class Buchhaltung(QDialog):
    def __init__(self, parent, db, year):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Buchhaltung · Islamischer Verein Frankenthal e.V.")
        self.resize(1260, 720)
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS bookkeeping_text (
                        year INTEGER, booking TEXT, german TEXT NOT NULL, PRIMARY KEY(year,booking))""")
            db.execute("""CREATE TABLE IF NOT EXISTS bookkeeping_document (
                        id INTEGER PRIMARY KEY, year INTEGER NOT NULL, booking TEXT,
                        category TEXT NOT NULL, name TEXT NOT NULL, added TEXT NOT NULL,
                        content BLOB NOT NULL)""")
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        layout.addLayout(header)
        header.addWidget(QLabel("Buchungsjahr"))
        self.year = QComboBox()
        self.year.addItems(("2025", "2026"))
        self.year.setCurrentText(str(year) if year in (2025, 2026) else "2026")
        header.addWidget(self.year)
        self.totals = QLabel()
        header.addWidget(self.totals, 1)
        self.button(header, "Jahresmappe exportieren", self.export)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        books = QWidget()
        books_layout = QVBoxLayout(books)
        tools = QHBoxLayout()
        books_layout.addLayout(tools)
        self.button(tools, "Buchungstext Deutsch bearbeiten", self.edit_text)
        self.button(tools, "Beleg zur Buchung hinzufügen", lambda: self.add_document(True))
        tools.addStretch()
        self.book = self.table(HEADERS)
        books_layout.addWidget(self.book)
        tabs.addTab(books, "Buchungen aus dem Finanzregister")
        archive = QWidget()
        archive_layout = QVBoxLayout(archive)
        tools = QHBoxLayout()
        archive_layout.addLayout(tools)
        self.button(tools, "Dateien hinzufügen", lambda: self.add_document(False))
        self.button(tools, "Beleg öffnen", self.open_document)
        tools.addStretch()
        self.docs = self.table(("Beleg-Nr.", "Belegart", "Dateiname", "Erfasst am", "Buchungsbezug"))
        archive_layout.addWidget(self.docs)
        tabs.addTab(archive, "Kontoauszüge und Belege")
        tax = QWidget()
        tax_layout = QVBoxLayout(tax)
        info = QLabel("Steuerunterlagen vorbereiten\n"
                      "Das Buchungsjahr hier und das Veranlagungsjahr in ELSTER anhand des Finanzamtsschreibens wählen.\n"
                      "Die Jahresmappe dient der Prüfung und Vorbereitung. Die Zuordnung zu amtlichen Formularfeldern erfolgt in ELSTER.")
        info.setWordWrap(True)
        tax_layout.addWidget(info)
        for label, url in FORM_LINKS:
            self.button(tax_layout, label, lambda checked=False, url=url: QDesktopServices.openUrl(QUrl(url)))
        self.button(tax_layout, "Finanzregister 2026 öffnen", lambda: QDesktopServices.openUrl(QUrl(SHEET)))
        tax_layout.addStretch()
        tabs.addTab(tax, "Amtliche Formulare")
        self.year.currentTextChanged.connect(self.reload)
        self.reload()

    @staticmethod
    def button(layout, text, handler):
        button = QPushButton(text)
        button.clicked.connect(handler)
        layout.addWidget(button)

    @staticmethod
    def table(headers):
        grid = QTableWidget(0, len(headers))
        grid.setHorizontalHeaderLabels(headers)
        grid.setEditTriggers(QTableWidget.NoEditTriggers)
        grid.setSelectionBehavior(QTableWidget.SelectRows)
        grid.setSelectionMode(QTableWidget.SingleSelection)
        grid.setAlternatingRowColors(True)
        return grid

    @staticmethod
    def fill(grid, rows):
        grid.setRowCount(len(rows))
        for i, (key, values) in enumerate(rows):
            for j, value in enumerate(values):
                cell = QTableWidgetItem(str(value or ""))
                cell.setToolTip(str(value or ""))
                cell.setData(Qt.UserRole, key)
                grid.setItem(i, j, cell)
        grid.resizeColumnsToContents()
        for column in range(grid.columnCount()):
            grid.setColumnWidth(column, min(grid.columnWidth(column), 280))

    @property
    def selected_year(self):
        return int(self.year.currentText())

    def reload(self):
        year = self.selected_year
        rows = list(booking_rows(self.db, year))
        self.fill(self.book, rows)
        sources = {key: row[8] for key, row in rows}
        self.fill(self.docs, [(r[0], (*r[:4], sources.get(r[4], "Zuordnung prüfen") if r[4] else "Jahresbeleg"))
                              for r in self.db.execute("""SELECT id,category,name,added,booking
                                  FROM bookkeeping_document WHERE year=? ORDER BY id""", (year,))])
        totals = summary(self.db, year)
        self.totals.setText(" · ".join(f"{title}: {money(sum(totals[kind][k] for k in ('cash','bank','other')))} €"
                                      for kind, title in (("Hyrjet", "Einnahmen"), ("Daljet", "Ausgaben")))
                            + " · Stand laut Finanzregister")

    def edit_text(self):
        row = self.book.currentRow()
        if row < 0:
            QMessageBox.information(self, "Buchung", "Bitte zuerst eine Buchung auswählen.")
            return
        key = self.book.item(row, 0).data(Qt.UserRole)
        original = self.book.item(row, 7).text()
        current = self.book.item(row, 6).text()
        value, ok = QInputDialog.getMultiLineText(self, "Buchungstext Deutsch", f"Original: {original}", current)
        if ok:
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO bookkeeping_text VALUES (?,?,?)",
                                (self.selected_year, key, value.strip()))
            self.reload()
            self.book.selectRow(row)

    def add_document(self, attach):
        row = self.book.currentRow()
        if attach and row < 0:
            QMessageBox.information(self, "Buchung", "Bitte zuerst eine Buchung auswählen.")
            return
        booking = self.book.item(row, 0).data(Qt.UserRole) if attach else None
        category, ok = QInputDialog.getItem(self, "Beleg erfassen", "Belegart", DOCUMENT_TYPES, editable=False)
        if not ok:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Belege auswählen", "", "Belege (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.csv *.xlsx)")
        try:
            with self.db:
                for filename in paths:
                    path = Path(filename)
                    with path.open("rb") as stream:
                        content = stream.read(MAX_DOCUMENT_BYTES + 1)
                    if not content or len(content) > MAX_DOCUMENT_BYTES:
                        raise ValueError(f"{path.name}: Die Datei muss zwischen 1 Byte und 30 MB groß sein.")
                    self.db.execute("""INSERT INTO bookkeeping_document(year,booking,category,name,added,content)
                                       VALUES (?,?,?,?,?,?)""",
                                    (self.selected_year, booking, category, path.name, date.today().isoformat(), content))
            self.reload()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Belege", str(exc))

    def open_document(self):
        row = self.docs.currentRow()
        if row < 0:
            return
        key = self.docs.item(row, 0).data(Qt.UserRole)
        name, content = self.db.execute("SELECT name,content FROM bookkeeping_document WHERE id=?", (key,)).fetchone()
        path, _ = QFileDialog.getSaveFileName(self, "Belegkopie speichern und öffnen", name)
        if path:
            try:
                Path(path).write_bytes(content)
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            except OSError as exc:
                QMessageBox.warning(self, "Beleg", str(exc))

    def export(self):
        year = self.selected_year
        path, _ = QFileDialog.getSaveFileName(self, "Jahresmappe exportieren", f"Buchhaltung_{year}.zip", "ZIP (*.zip)")
        if not path:
            return
        from io import StringIO
        try:
            rows = list(booking_rows(self.db, year))
            index = {key: row[8] for key, row in rows}
            journal, documents = StringIO(), StringIO()
            writer = csv.writer(journal, delimiter=";")
            writer.writerow(HEADERS)
            for _, row in rows:
                writer.writerow([v if i == 4 else excel_safe(v) for i, v in enumerate(row)])
            writer = csv.writer(documents, delimiter=";")
            writer.writerow(("Beleg-Nr.", "Belegart", "Datei", "Erfasst am", "Buchungsbezug"))
            with ZipFile(path, "w", ZIP_DEFLATED) as archive:
                for num, key, category, name, day, content in self.db.execute(
                        "SELECT id,booking,category,name,added,content FROM bookkeeping_document WHERE year=? ORDER BY id", (year,)):
                    entry = f"Belege/{num}-{Path(name).name}"
                    archive.writestr(entry, content)
                    writer.writerow((num, category, entry, day, index.get(key, "Zuordnung prüfen") if key else "Jahresbeleg"))
                archive.writestr("Buchungsjournal.csv", journal.getvalue().encode("utf-8-sig"))
                archive.writestr("Belegverzeichnis.csv", documents.getvalue().encode("utf-8-sig"))
                archive.writestr("Jahresuebersicht.txt", self.totals.text())
            QMessageBox.information(self, "Jahresmappe", "Jahresmappe wurde gespeichert.")
        except OSError as exc:
            QMessageBox.warning(self, "Export", str(exc))
