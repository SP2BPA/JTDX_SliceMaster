#!/usr/bin/env python3
"""Read-only structural check for a Log4OM 2 SQLite database."""
from pathlib import Path
import sqlite3
import sys

def fail(msg):
    print("[FAIL] " + msg)
    raise SystemExit(2)

def main():
    if len(sys.argv) != 2:
        fail("usage: VERIFY_LOG4OM_DB.py <path-to-Log4OM.SQLite>")
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.is_file():
        fail("file not found: " + str(path))
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "Log" not in tables:
            fail("table Log not found")
        columns = [r[1] for r in cur.execute("PRAGMA table_info('Log')")]
        lower = {c.lower() for c in columns}
        required = {"callsign", "band", "mode", "qsodate"}
        missing = sorted(required - lower)
        if missing:
            fail("missing required columns: " + ", ".join(missing))
        count = cur.execute("SELECT COUNT(*) FROM Log").fetchone()[0]
        dxcc = cur.execute("SELECT COUNT(DISTINCT dxcc) FROM Log WHERE dxcc IS NOT NULL").fetchone()[0] if "dxcc" in lower else "n/a"
        dates = cur.execute("SELECT MIN(qsodate), MAX(qsodate) FROM Log").fetchone()
        print("[PASS] Log4OM SQLite structure compatible")
        print("[INFO] columns:", len(columns))
        print("[INFO] QSO rows:", count)
        print("[INFO] distinct DXCC:", dxcc)
        print("[INFO] date range:", dates[0], "..", dates[1])
    finally:
        con.close()

if __name__ == "__main__":
    main()
