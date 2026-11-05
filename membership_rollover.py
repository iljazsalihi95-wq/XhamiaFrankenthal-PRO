"""Membership carry-forward rules for future years.

Never copy monthly payments into a new year.
Never delete the historical source rows.
"""
from seed_data import euros

MONTH_COLUMNS = ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")

def paid_members(db, year):
    source = db.execute(
        """SELECT m.member_id,m.first_name,m.last_name,m.bank,
        COALESCE(SUM(CASE WHEN s.amount_cents>0 THEN s.amount_cents ELSE 0 END),0)
        FROM source_members m LEFT JOIN source_months s
        ON m.year=s.year AND m.source_row=s.source_row
        WHERE m.year=?
        GROUP BY m.year,m.source_row""",(year,)).fetchall()
    manual = db.execute(
        "SELECT member_id,first_name,last_name,method,"+",".join(MONTH_COLUMNS)+" FROM members WHERE year=?",
        (year,)).fetchall()
    result = [(str(a),str(b),str(c),str(d)) for a,b,c,d,paid in source if paid>0]
    result += [(str(row[0]),str(row[1]),str(row[2]),str(row[3])) for row in manual
               if sum(euros(v) for v in row[4:])>0]
    return result

def carry_forward(db, from_year, to_year):
    if to_year != from_year+1:
        raise ValueError("Carry-forward is permitted only to the following year")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_members_year_identity ON members(year,member_id,first_name,last_name)")
    existing = set((str(a),str(b).casefold(),str(c).casefold()) for a,b,c in
        db.execute("SELECT member_id,first_name,last_name FROM members WHERE year=?",(to_year,)))
    existing.update((str(a),str(b).casefold(),str(c).casefold()) for a,b,c in
        db.execute("SELECT member_id,first_name,last_name FROM source_members WHERE year=?",(to_year,)))
    added=0
    for member_id,first,last,method in paid_members(db,from_year):
        key=(member_id,first.casefold(),last.casefold())
        if key in existing:continue
        db.execute("INSERT INTO members(year,member_id,first_name,last_name,method) VALUES(?,?,?,?,?)",
                   (to_year,member_id,first,last,method))
        existing.add(key)
        added+=1
    db.commit()
    return added
