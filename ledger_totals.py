"""Totals for recorded cash and bank movements. Amounts are stored in cents."""
from decimal import Decimal, InvalidOperation

def cents(value):
    raw = str(value or "").strip().replace("€", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return int((Decimal(raw) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return 0

def summary(db, year):
    totals = {}
    for kind in ("Hyrjet", "Daljet"):
        sheet = kind if year == 2026 else kind + " " + str(year)
        source = db.execute(
            "SELECT description, account, category, amount_cents, included FROM source_finance WHERE source_sheet=?",
            (sheet,)
        ).fetchall()
        manual = db.execute(
            "SELECT description, method, category, amount FROM finance WHERE year=? AND kind=?",
            (year, kind)
        ).fetchall()
        records = list(source) + [(a, b, c, cents(d), "Po") for a,b,c,d in manual]
        result = {"count": 0, "cash": 0, "bank": 0, "other": 0, "excluded": 0}
        for description, method, category, amount, included in records:
            note = str(description or "").casefold()
            cat = str(category or "").casefold()
            opening = ("gjendje fillestare" in cat or "saldo fillestare" in cat or
                       any(x in note for x in ("gjendje fillestare", "saldo fillestare", "übertrag", "bartje")))
            excluded = str(included).strip().casefold() in ("jo", "false", "0", "nein")
            if opening or excluded:
                result["excluded"] += 1
                continue
            method = str(method or "").strip().casefold()
            key = "cash" if method in ("cash", "kesh", "kësh", "false") else "bank" if method in ("bank", "bankë", "true") else "other"
            result[key] += int(amount or 0)
            result["count"] += 1
        totals[kind] = result
    return totals
