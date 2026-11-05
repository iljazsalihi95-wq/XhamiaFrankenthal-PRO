import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from seed_data import seed, euros
from ledger_totals import summary

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
