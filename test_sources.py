import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from seed_data import seed, euros
from finance_reports import summary

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
