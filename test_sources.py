import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from seed_data import seed, euros
from ledger_totals import summary, totals
from sheet_source import import_workbook
from openpyxl import Workbook

class SourceTests(unittest.TestCase):
    def test_currency(self):
        self.assertEqual(euros("1.430,00 €"),143000)
        self.assertEqual(euros("20 €"),2000)
        self.assertEqual(euros(""),0)
    def test_snapshots(self):
        root=Path(__file__).parent/"data"
        for name in ("2025","2026","2027","Hyrjet","Daljet","Hyrjet_2025","Daljet_2025","Hyrjet_2027","Daljet_2027"):
            data=json.loads((root/(name+".json")).read_text(encoding="utf-8"))
            self.assertTrue(data["rows"])
    def test_manual_entries_affect_totals(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE finance(year INTEGER,kind TEXT,date TEXT,description TEXT,method TEXT,category TEXT,amount TEXT)")
            seed(db)
            before=summary(db,2026)["Hyrjet"]["cash"]
            db.execute("INSERT INTO finance VALUES (?,?,?,?,?,?,?)",(2026,"Hyrjet","05.11.2026","Test payment","Cash","Donacion","25.50"))
            after=summary(db,2026)["Hyrjet"]["cash"]
            self.assertEqual(after-before,2550)
    def test_exclusion_and_shared_totals(self):
        rows = [
            ("01.01.2026", "Saldo", "Bank", "Gjendje fillestare", 92000, "Po", 1),
            ("01.01.2026", "Depozitim", "Bank", "Transfer i brendshëm", 10000, "Po", 2),
            ("01.01.2026", "Anëtarësi LIVE", "Cash", "Anëtarësia", 2000, "Po", 3),
            ("01.01.2026", "Pagesë individuale", "Cash", "Anëtarësia", 2000, "Jo", 4),
        ]
        self.assertEqual(totals(rows), dict(count=1, cash=2000, bank=0, other=0, excluded=3))

    def test_refresh_preserves_manual_rows_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory, sqlite3.connect(":memory:") as db:
            seed(db)
            db.execute("CREATE TABLE finance(year INTEGER,kind TEXT,date TEXT,description TEXT,method TEXT,category TEXT,amount TEXT)")
            db.execute("INSERT INTO finance VALUES (2026,'Hyrjet','01.01.2026','Lokal','Cash','Donacion','3.50')")
            db.commit()
            workbook = Workbook()
            workbook.remove(workbook.active)
            for kind in ("Hyrjet", "Daljet"):
                tab = workbook.create_sheet(kind)
                tab.append([kind])
                tab.append([])
                tab.append(["Data", "Përshkrimi", "Cash/Bank", "Kategoria", "Shuma", "Përfshi?"])
                tab.append(["14/08/2026", "Nga burimi", "Cash", "Donacion", 1, "Po"])
            for tab in ("Gjendja", "BILANCI MASTER", "Rakordimi i saktë 2026"):
                workbook.create_sheet(tab).append(["Bilanci"])
            path = Path(directory) / "source.xlsx"
            workbook.save(path)
            backup = import_workbook(db, path, directory)
            seed(db)
            self.assertTrue(backup.is_file())
            self.assertEqual(summary(db, 2026)["Hyrjet"]["cash"], 450)
            self.assertEqual(summary(db, 2026)["Daljet"]["cash"], 100)

    def test_bank_withdrawal_uses_source_note_and_inclusion_flag(self):
        with sqlite3.connect(":memory:") as db:
            seed(db)
            before = summary(db, 2026)["Daljet"]["bank"]
            db.executemany("INSERT INTO source_finance VALUES (?,?,?,?,?,?,?,?,?)", [
                ("Daljet", 1001, "02.04.2026", "Tërheqje", "Bank", "Transfer i brendshëm", 51000, "Po",
                 "Dalje reale nga BANKA. JO transfer Cash-Bank."),
                ("Daljet", 1002, "04.04.2026", "Përjashtuar", "Bank", "Transfer i brendshëm", 50500, "Jo",
                 "Dalje reale nga BANKA. JO transfer Cash-Bank."),
                ("Daljet", 1003, "04.04.2026", "Transfer", "Bank", "Transfer i brendshëm", 20000, "Po", ""),
            ])
            self.assertEqual(summary(db, 2026)["Daljet"]["bank"] - before, 51000)

    def test_2025_thousands_are_repaired_in_existing_source_cache(self):
        with sqlite3.connect(":memory:") as db:
            seed(db)
            where = " WHERE source_sheet='Hyrjet 2025' AND source_row=4"
            self.assertEqual(db.execute("SELECT amount_cents FROM source_finance"+where).fetchone()[0], 150000)
            db.execute("UPDATE source_finance SET amount_cents=150"+where)
            seed(db)
            self.assertEqual(db.execute("SELECT amount_cents FROM source_finance"+where).fetchone()[0], 150000)

    def test_database(self):
        with sqlite3.connect(":memory:") as db:
            seed(db)
            self.assertGreater(db.execute("SELECT COUNT(*) FROM source_members").fetchone()[0],300)
            self.assertGreater(db.execute("SELECT COUNT(*) FROM source_finance").fetchone()[0],100)
            self.assertIn("Hyrjet",summary(db,2026))
            first=db.execute("SELECT COUNT(*) FROM source_members").fetchone()[0]
            seed(db)
            self.assertEqual(first,db.execute("SELECT COUNT(*) FROM source_members").fetchone()[0])
if __name__=="__main__":
    unittest.main()
