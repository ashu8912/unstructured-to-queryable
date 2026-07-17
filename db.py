import sqlite3, json

DB = "receipts.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT, date TEXT, total REAL,
            currency TEXT, items_json TEXT
        )""")
    con.commit(); con.close()

def insert_receipt(r):
    con = sqlite3.connect(DB)
    con.execute(
        "INSERT INTO receipts (store, date, total, currency, items_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (r.store, r.date, r.total, r.currency,
         json.dumps([i.model_dump() for i in r.items])),
    )
    con.commit(); con.close()

def run_query(sql):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql).fetchall()
    con.close()
    return [dict(x) for x in rows]