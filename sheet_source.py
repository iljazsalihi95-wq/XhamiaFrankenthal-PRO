"""Import a signed-in Google Sheets workbook export into the local finance cache."""
import datetime
from contextlib import closing
from pathlib import Path
import sqlite3

from openpyxl import load_workbook

from ledger_totals import cents

SHEET = "https://docs.google.com/spreadsheets/d/1buwJ_DodIOcQCyrzckr1uO_lPXF3vEnYNUzZeA65Wao"
TABS = {
    "Hyrjet 2026": 210442105,
    "Daljet 2026": 1918400385,
    "Gjendja 2026": 674181368,
    "Bilanci aktual · rakordimi": 572817127,
    "Bilanci ndër vite": 1249036061,
}


def backup_database(db, path):
    with closing(sqlite3.connect(path)) as copy:
        db.backup(copy)


def import_workbook(db, path, backup_folder):
    """Validate before replacing the source cache; preserve local entries."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    entries, balance_rows = {}, {}
    try:
        for tab in ("Hyrjet", "Daljet"):
            rows = list(workbook[tab].values)
            if tuple(rows[2][:4]) != ("Data", "Përshkrimi", "Cash/Bank", "Kategoria"):
                raise ValueError(f"Titujt e kolonave te {tab} nuk përputhen.")
            entries[tab] = []
            for index, row in enumerate(rows[3:], 4):
                row = tuple(row) + (None,) * 9
                date, description, account, category, amount, included = row[:6]
                if isinstance(date, (datetime.datetime, datetime.date)):
                    date = date.strftime("%d.%m.%Y")
                else:
                    try:
                        date = datetime.datetime.strptime(str(date).replace("/", "."), "%d.%m.%Y").strftime("%d.%m.%Y")
                    except ValueError:
                        if description and amount is not None:
                            raise ValueError(f"Data te {tab}, rreshti {index}, është e pavlefshme.")
                        continue
                if str(amount).startswith(("#REF!", "#VALUE!", "#N/A", "#ERROR!")):
                    raise ValueError(f"Gabim formule te {tab}, rreshti {index}.")
                notes = " | ".join(str(value) for value in row[6:9] if value is not None)
                entries[tab].append((tab, index, date, str(description or ""), str(account or ""),
                                     str(category or ""), cents(amount), str(included or ""), notes))
            if not entries[tab]:
                raise ValueError(f"Nuk u gjetën regjistrime te {tab}.")
        for tab, width in (("Gjendja", 12), ("BILANCI MASTER", 14), ("Rakordimi i saktë 2026", 12)):
            balance_rows[tab] = [
                (tab, row_number, column, str(value))
                for row_number, row in enumerate(workbook[tab].iter_rows(max_col=width, values_only=True), 1)
                for column, value in enumerate(row, 1) if value is not None
            ]
            if not balance_rows[tab]:
                raise ValueError(f"Fleta {tab} është bosh.")
    finally:
        workbook.close()

    now = datetime.datetime.now()
    backup_path = Path(backup_folder) / f"para-financave-{now:%Y%m%d-%H%M%S-%f}.sqlite3"
    backup_database(db, backup_path)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS source_sync (id INTEGER PRIMARY KEY, synced_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS source_balance (tab TEXT, row_num INTEGER, col_num INTEGER, value TEXT)")
        for tab, rows in entries.items():
            db.execute("DELETE FROM source_finance WHERE source_sheet=?", (tab,))
            db.executemany("INSERT INTO source_finance VALUES (?,?,?,?,?,?,?,?,?)", rows)
        db.execute("DELETE FROM source_balance")
        db.executemany("INSERT INTO source_balance VALUES (?,?,?,?)",
                       [row for rows in balance_rows.values() for row in rows])
        db.execute("INSERT OR REPLACE INTO source_sync VALUES (1,?)", (now.isoformat(timespec="minutes"),))
    return backup_path
