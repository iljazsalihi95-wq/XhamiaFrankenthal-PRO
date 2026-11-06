"""Shared ledger for tables, cards, and reports, with amounts in cents."""
from decimal import Decimal, InvalidOperation

EXCLUDED = {"jo", "false", "0", "nein"}


def cents(value):
    raw = str(value or "").strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return int((Decimal(raw) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, OverflowError):
        return 0


def records(db, year, kind):
    sheet = kind if year == 2026 else f"{kind} {year}"
    source = db.execute(
        """SELECT date, description, account,
                  CASE WHEN source_sheet='Daljet' AND account='Bank'
                            AND lower(notes) LIKE '%dalje reale nga banka%'
                            AND lower(notes) LIKE '%jo transfer cash-bank%'
                       THEN 'Borxh / Forderung' ELSE category END,
                  amount_cents, included, source_row FROM source_finance WHERE source_sheet=? ORDER BY source_row""",
        (sheet,),
    ).fetchall()
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='finance'").fetchone()
    if not exists:
        return source
    manual = db.execute(
        "SELECT date, description, method, category, amount, rowid FROM finance WHERE year=? AND kind=?",
        (year, kind),
    )
    return source + [(d, n, m, c, cents(a), "Po", -rowid) for d, n, m, c, a, rowid in manual]


def exclusion(record):
    _, description, _, category, _, included, _ = record
    category = str(category or "").strip().casefold()
    description = str(description or "").casefold()
    opening = ("gjendje fillestare", "saldo fillestare", "übertrag", "gjendje e bartur")
    if any(word in category or word in description for word in opening) or "bartje" in description:
        return "Gjendje fillestare"
    if category.startswith(("transfer i brendshëm", "transfer i brendshem", "transfertë e brendshme")):
        return "Transfer i brendshëm / për rakordim"
    if str(included).strip().casefold() in EXCLUDED:
        return "Përjashtuar në burim"
    return ""


def totals(rows):
    result = dict(count=0, cash=0, bank=0, other=0, excluded=0)
    for row in rows:
        if exclusion(row):
            result["excluded"] += 1
            continue
        method = str(row[2] or "").strip().casefold()
        if method in {"cash", "kesh", "kësh", "false"}:
            key = "cash"
        elif method in {"bank", "bankë", "true"}:
            key = "bank"
        else:
            key = "other"
        result[key] += row[4]
        result["count"] += 1
    return result


def summary(db, year):
    return {kind: totals(records(db, year, kind)) for kind in ("Hyrjet", "Daljet")}


def reconciliation(db, year):
    """Compare the imported source rows with the same workbook's cached summary."""
    if year != 2026 or not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_balance'"
    ).fetchone():
        return {}
    official = dict(db.execute(
        "SELECT row_num,value FROM source_balance WHERE tab='Gjendja' AND col_num=11 AND row_num IN (3,4)"
    ))
    comparison = {}
    for kind, row_number in (("Hyrjet", 3), ("Daljet", 4)):
        if row_number not in official:
            continue
        imported = totals(row for row in records(db, year, kind) if row[6] > 0)
        classified = sum(imported[key] for key in ("cash", "bank", "other"))
        comparison[kind] = (classified, cents(official[row_number]))
    return comparison
