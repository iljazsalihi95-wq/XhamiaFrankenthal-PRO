"""Import official Google Sheets snapshots bundled with the Windows installer.
Preserves source rows, does not synthesize payments or balances.
"""
import json, sys
from pathlib import Path
from datetime import datetime

def euros(value):
    s=str(value or "").replace("€","").replace("\u00a0","").replace(" ","").strip()
    if not s:return 0
    if "," in s:s=s.replace(".","").replace(",",".")
    try:return round(float(s)*100)
    except (ValueError,TypeError):return 0

def seed(db):
    base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"data"
    db.execute("CREATE TABLE IF NOT EXISTS source_members (year INTEGER,source_row INTEGER,member_id TEXT,first_name TEXT,last_name TEXT,bank TEXT,PRIMARY KEY(year,source_row))")
    db.execute("CREATE TABLE IF NOT EXISTS source_months (year INTEGER,source_row INTEGER,month INTEGER,amount_cents INTEGER,raw_value TEXT,PRIMARY KEY(year,source_row,month))")
    db.execute("CREATE TABLE IF NOT EXISTS source_finance (source_sheet TEXT,source_row INTEGER,date TEXT,description TEXT,account TEXT,category TEXT,amount_cents INTEGER,included TEXT,notes TEXT,PRIMARY KEY(source_sheet,source_row))")
    for year in (2025,2026,2027):
        path=base/f"{year}.json"
        if not path.exists():continue
        rows=json.loads(path.read_text(encoding="utf-8"))["rows"]
        for ix,row in enumerate(rows[1:],start=2):
            row=list(row)+[""]*20
            if not str(row[1]).strip() or not str(row[2]).strip():continue
            db.execute("INSERT OR IGNORE INTO source_members VALUES (?,?,?,?,?,?)",(year,ix,str(row[0]),str(row[1]),str(row[2]),str(row[3])))
            for m in range(1,13):
                raw=str(row[3+m] or "")
                db.execute("INSERT OR IGNORE INTO source_months VALUES (?,?,?,?,?)",(year,ix,m,euros(raw),raw))
    has_sync=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_sync'").fetchone()
    for sheet in ("Hyrjet","Daljet","Hyrjet 2025","Daljet 2025","Hyrjet 2027","Daljet 2027"):
        if has_sync and sheet in ("Hyrjet","Daljet"):continue
        path=base/(sheet.replace(" ","_")+".json")
        if not path.exists():continue
        rows=json.loads(path.read_text(encoding="utf-8"))["rows"]
        for ix,row in enumerate(rows,start=1):
            if len(row)<4:continue
            try:
                normalized_date=datetime.strptime(str(row[0]).replace("/", "."), "%d.%m.%Y").strftime("%d.%m.%Y")
            except ValueError:
                continue
            if sheet.endswith("2025"):
                date,desc,bank,amount=row[:4]
                account="Bank" if str(bank).upper()=="TRUE" else "Cash"
                category="Të tjera";included="Po";notes=""
            else:
                rr=list(row)+[""]*10
                date,desc,account,category,amount,included=rr[:6]
                notes=" | ".join(str(value) for value in rr[6:9] if value)
            db.execute("INSERT OR IGNORE INTO source_finance VALUES (?,?,?,?,?,?,?,?,?)",(sheet,ix,normalized_date,str(desc),str(account),str(category),euros(amount),str(included),notes))
    db.commit()
